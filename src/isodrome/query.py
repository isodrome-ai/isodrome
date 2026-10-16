"""Queries: immutable descriptions of a read, run only when a result is asked for."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

import pyarrow as pa

from isodrome import errors
from isodrome.output import decode
from isodrome.parse import format_ns, format_position, parse_position, to_duration_ns, to_ns
from isodrome.result import Result
from isodrome.v1 import isodrome_pb2 as pb

if TYPE_CHECKING:
    import pandas as pd

    from isodrome._feed import Feed

TIME_COLUMNS = ("_event_time", "_published_time", "_receive_time")
BASES = {"received": pb.AS_OF_BASIS_RECEIVED, "published": pb.AS_OF_BASIS_PUBLISHED}
KEEP = {"first": pb.DEDUPE_KEEP_FIRST, "last": pb.DEDUPE_KEEP_LAST}
ORDERS = {"arrival": pb.DEDUPE_ORDER_ARRIVAL, "publication": pb.DEDUPE_ORDER_PUBLICATION}


# ---------- Filter expressions ----------

_OPS = {
    "==": pb.FILTER_OP_EQ,
    "!=": pb.FILTER_OP_NE,
    "<": pb.FILTER_OP_LT,
    "<=": pb.FILTER_OP_LTE,
    ">": pb.FILTER_OP_GT,
    ">=": pb.FILTER_OP_GTE,
    "in": pb.FILTER_OP_IN,
    "is_null": pb.FILTER_OP_IS_NULL,
    "is_not_null": pb.FILTER_OP_IS_NOT_NULL,
}


def _plain(value):
    """A filter value as the server takes it: bool, int, float or str (times as integer ns)."""
    if isinstance(value, (bool, int, float, str)):
        return value
    try:
        return to_ns(value)
    except TypeError:
        raise TypeError(f"cannot filter on {value!r}: use a bool, number, string or time") from None


@dataclass(frozen=True)
class Condition:
    """`column op values`, e.g. col("price") > 100. Several conditions are ANDed."""

    column: str
    op: str
    values: tuple = ()

    def to_pb(self) -> pb.Filter:
        def value(v) -> pb.Value:
            if isinstance(v, bool):
                return pb.Value(bool_value=v)
            if isinstance(v, int):
                return pb.Value(int_value=v)
            if isinstance(v, float):
                return pb.Value(float_value=v)
            return pb.Value(string_value=v)

        return pb.Filter(column=self.column, op=_OPS[self.op], values=[value(v) for v in self.values])

    def mask(self, df: pd.DataFrame):
        """The same condition, evaluated on a DataFrame (for filters applied after local work)."""
        import pandas as pd

        series = df[self.column]
        values = list(self.values)
        if pd.api.types.is_datetime64_any_dtype(series):
            values = [pd.Timestamp(v, unit="ns", tz="UTC") if isinstance(v, int) else pd.Timestamp(v) for v in values]
        if self.op == "is_null":
            return series.isna()
        if self.op == "is_not_null":
            return series.notna()
        if self.op == "in":
            return series.isin(values)
        v = values[0]
        return {
            "==": series == v, "!=": series != v, "<": series < v, "<=": series <= v, ">": series > v, ">=": series >= v,
        }[self.op].fillna(False)

    def __and__(self, other):
        raise TypeError("conditions are ANDed by passing several: where(a, b)")

    def __or__(self, other):
        raise TypeError("the server takes only ANDed conditions; fetch, then filter the DataFrame for OR")

    def __bool__(self):
        raise TypeError("use conditions in where(...), not in `if` or `and`/`or`")

    def __repr__(self) -> str:
        if self.op in ("is_null", "is_not_null"):
            return f"col({self.column!r}).{self.op}()"
        if self.op == "in":
            return f"col({self.column!r}).isin({list(self.values)!r})"
        return f"col({self.column!r}) {self.op} {self.values[0]!r}"


class Col:
    """A column in a filter: `col("price") > 100`, `col("side").isin(["buy", "sell"])`."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def _cmp(self, op, value) -> Condition:
        if value is None:
            raise TypeError("compare with None using .is_null() or .is_not_null()")
        return Condition(self.name, op, (_plain(value),))

    def __eq__(self, value):  # type: ignore[override]
        return self._cmp("==", value)

    def __ne__(self, value):  # type: ignore[override]
        return self._cmp("!=", value)

    def __lt__(self, value):
        return self._cmp("<", value)

    def __le__(self, value):
        return self._cmp("<=", value)

    def __gt__(self, value):
        return self._cmp(">", value)

    def __ge__(self, value):
        return self._cmp(">=", value)

    __hash__ = object.__hash__

    def isin(self, values: Iterable) -> Condition:
        values = tuple(_plain(v) for v in values)
        if not values:
            raise ValueError("isin needs at least one value")
        return Condition(self.name, "in", values)

    def is_null(self) -> Condition:
        return Condition(self.name, "is_null")

    def is_not_null(self) -> Condition:
        return Condition(self.name, "is_not_null")

    def __repr__(self) -> str:
        return f"col({self.name!r})"


def col(name: str) -> Col:
    """A column for filters: `feed.query(where=col("price") > 100)`."""
    return Col(name)


def conditions(where) -> tuple[Condition, ...]:
    """`where=` as given (a condition, a list of them, or {column: value}) → conditions.
    In a dict, a list means "one of" and None means "is null"."""
    if where is None:
        return ()
    if isinstance(where, Condition):
        return (where,)
    if isinstance(where, dict):
        out = []
        for column, value in where.items():
            if value is None:
                out.append(Condition(column, "is_null"))
            elif isinstance(value, (list, tuple, set, frozenset)):
                out.append(Col(column).isin(value))
            else:
                out.append(Col(column) == value)
        return tuple(out)
    if isinstance(where, (list, tuple)):
        return tuple(c for item in where for c in conditions(item))
    if isinstance(where, Col):
        raise TypeError(f"{where!r} is a column, not a condition: compare it, e.g. {where!r} == 'x'")
    raise TypeError(f"where= takes a condition, a list of them, or a dict, not {type(where).__name__}")


# ---------- Queries ----------


@dataclass(frozen=True)
class Query:
    """A read of one feed. Immutable: every method returns a new query. Nothing runs until
    `.to_df()`, `.fetch()`, `.to_arrow()`, `.to_polars()` or `.count()`.

    Times: `start`/`end` bound event time (end exclusive); `since` is "this long ago" (resolved
    when the query runs). `as_of` keeps what was known at that moment, by `basis` "received"
    (what Isodrome had; the default) or "published" (what the source had published).
    `as_of_lag` keeps each event as known that long before its own event time (e.g. "24h": each
    forecast hour as it stood a day ahead). `dedupe` keeps one version per value of its columns,
    the `keep` "last" or "first" by `order` "arrival" or "publication".
    """

    feed: str
    start: int | None = None
    end: int | None = None
    since: int | None = None
    as_of: int | None = None
    basis: str = "received"
    as_of_lag: int | None = None
    filters: tuple[Condition, ...] = ()
    columns: tuple[str, ...] | None = None
    limit: int | None = None
    payload: bool = False
    dedupe: tuple[str, ...] | None = None
    keep: str = "last"
    order: str = "arrival"
    at_position: tuple[int, ...] | None = None
    _feed: Feed | None = field(default=None, compare=False, repr=False)

    @classmethod
    def build(cls, feed: Feed, **options) -> Query:
        return cls(feed=feed.ref, _feed=feed)._with(**options)

    def _with(self, **options) -> Query:
        changes: dict[str, Any] = {}
        for name, value in options.items():
            if name in ("start", "end", "as_of"):
                changes[name] = None if value is None else to_ns(value)
            elif name == "since":
                changes[name] = None if value is None else (
                    to_duration_ns(value) if not isinstance(value, int) else value
                )
            elif name == "as_of_lag":
                changes[name] = None if value is None else to_duration_ns(value)
            elif name == "where":
                changes["filters"] = conditions(value)
            elif name in ("columns", "dedupe"):
                if isinstance(value, str):
                    value = [value]
                changes[name] = None if value is None else tuple(value)
            elif name == "at":
                changes["at_position"] = None if value is None else _position(value)
            elif name in ("basis", "keep", "order"):
                allowed = {"basis": BASES, "keep": KEEP, "order": ORDERS}[name]
                if value not in allowed:
                    raise ValueError(f"{name}= must be one of {', '.join(allowed)}, not {value!r}")
                changes[name] = value
            elif name in ("limit", "payload"):
                changes[name] = value
            else:
                raise TypeError(f"unknown query option {name!r}")
        query = dataclasses.replace(self, **changes)
        if query.since is not None and query.start is not None:
            raise ValueError("give since= or start=, not both")
        if query.as_of_lag is not None and query.at_position is not None:
            raise ValueError("as_of_lag= is computed from versions, so it cannot be pinned with at=")
        return query

    # ----- building -----

    def replace(self, **options) -> Query:
        """The same query with some options changed, e.g. `q.replace(since="7d")`."""
        return self._with(**options)

    def where(self, *conds, **equals) -> Query:
        """More conditions (ANDed with the existing ones): `q.where(col("x") > 1, kind="instant")`."""
        return dataclasses.replace(self, filters=self.filters + conditions(list(conds)) + conditions(equals or None))

    def select(self, *columns: str) -> Query:
        """Only these columns."""
        return dataclasses.replace(self, columns=tuple(columns))

    def at(self, position) -> Query:
        """Pinned to a position (from `Result.position`): reads exactly those events again."""
        return self._with(at=position)

    # ----- running -----

    def fetch(self) -> Result:
        """Runs the query and returns a Result (with `.to_df()`, `.position`, `.attribution`)."""
        if self.as_of_lag is not None:
            return self._fetch_with_lag()
        table, position, server_ns = self._read(self._request())
        return Result(table=table, position=position, server_ns=server_ns, feed=self._feed, query=self)

    def to_df(self) -> pd.DataFrame:
        """Runs the query; the events as a pandas DataFrame."""
        return self.fetch().to_df()

    def to_arrow(self) -> pa.Table:
        return self.fetch().to_arrow()

    def to_polars(self):
        return self.fetch().to_polars()

    def count(self) -> int:
        """The number of matching events (without fetching their data)."""
        if self.as_of_lag is not None:
            return len(self.fetch())
        request = self._request()
        if not request.columns:
            request.columns[:] = ["_offset"]
        table, _, _ = self._read(request)
        return table.num_rows

    # ----- internals -----

    def _client(self):
        if self._feed is None:
            raise RuntimeError("this query is not attached to a feed; build it with feed.query(...)")
        return self._feed._client

    def _request(self) -> pb.ReadRequest:
        request = pb.ReadRequest(
            feed=self._feed._pb_ref if self._feed is not None else _ref(self.feed),
            filters=[c.to_pb() for c in self.filters],
            columns=list(self.columns or ()),
            include_payload=self.payload or "_payload" in (self.columns or ()),
        )
        start = self.start
        if self.since is not None:
            from isodrome.parse import now_ns

            start = now_ns() - self.since
        if start is not None:
            request.start_event_time_ns = start
        if self.end is not None:
            request.end_event_time_ns = self.end
        if self.as_of is not None:
            request.as_of_ns = self.as_of
            request.as_of_basis = BASES[self.basis]
        if self.limit is not None:
            request.limit = self.limit
        if self.dedupe:
            request.dedupe.CopyFrom(pb.Dedupe(columns=list(self.dedupe), keep=KEEP[self.keep], order=ORDERS[self.order]))
        if self.at_position is not None:
            request.at_position.CopyFrom(pb.Position(next_offsets=list(self.at_position)))
        return request

    @errors.translating
    def _read(self, request: pb.ReadRequest) -> tuple[pa.Table, tuple[int, ...] | None, int]:
        tables, position, server_ns = [], None, 0
        for message in self._client().stream("Read", request, timeout=600):
            if message.HasField("position"):
                position = tuple(message.position.next_offsets)
                server_ns = message.server_ns
            table = decode(message.batch.ipc)
            if table is not None:
                tables.append(table)
        if not tables:
            return pa.table({}), position, server_ns
        return pa.concat_tables(tables, promote_options="default"), position, server_ns

    def _fetch_with_lag(self) -> Result:
        """Each event as known `as_of_lag` before its own event time: every version is read
        (with the times needed), then filtered, de-duplicated and filtered again locally, in the
        same order the server applies them (de-duplication first, so a filter never brings back
        a superseded version)."""
        import pandas as pd

        dedupe = self.dedupe or ()
        # Filters on de-duplication columns hold for every version of a row, so the server can
        # apply them first; the rest must wait until after de-duplication.
        early = tuple(c for c in self.filters if not dedupe or c.column in dedupe)
        late = tuple(c for c in self.filters if c not in early)
        wanted = list(self.columns) if self.columns else None
        needed = None
        if wanted is not None:
            needed = list(dict.fromkeys(wanted + list(TIME_COLUMNS) + list(dedupe) + [c.column for c in late]))
        versions = dataclasses.replace(
            self, as_of_lag=None, dedupe=None, limit=None, filters=early, columns=tuple(needed) if needed else None,
        )
        table, position, server_ns = versions._read(versions._request())
        df = table.to_pandas()
        if len(df):
            if "_published_time" not in df:
                df["_published_time"] = pd.NaT
            known = df["_receive_time"]
            if self.basis == "published":
                known = df["_published_time"].fillna(df["_receive_time"])
            lag = pd.Timedelta(self.as_of_lag, unit="ns")
            df = df[known <= df["_event_time"] - lag]
            if dedupe:
                arrival = df["_receive_time"]
                rank = df["_published_time"].fillna(arrival) if self.order == "publication" else arrival
                df = (
                    df.assign(_rank=rank, _arrival=arrival, _seq=range(len(df)))
                    .sort_values(["_rank", "_arrival", "_seq"])
                    .drop_duplicates(list(dedupe), keep=self.keep)
                    .drop(columns=["_rank", "_arrival", "_seq"])
                )
            for condition in late:
                df = df[condition.mask(df)]
            df = df.sort_values([c for c in ("_event_time", "_receive_time") if c in df], kind="stable")
            if self.limit is not None:
                df = df.head(self.limit)
        if wanted is not None:
            df = df[[c for c in wanted if c in df]]
        return Result(df=df.reset_index(drop=True), position=position, server_ns=server_ns, feed=self._feed, query=self)

    def describe(self) -> str:
        """The query in words."""
        parts = [f"from {self.feed}"]
        if self.since is not None:
            parts.append(f"since {_duration(self.since)} ago")
        if self.start is not None:
            parts.append(f"from {format_ns(self.start)}")
        if self.end is not None:
            parts.append(f"until {format_ns(self.end)}")
        if self.filters:
            parts.append("where " + " and ".join(map(repr, self.filters)))
        if self.as_of is not None:
            parts.append(f"as {self.basis} by {format_ns(self.as_of)}")
        if self.as_of_lag is not None:
            parts.append(f"each event as {self.basis} {_duration(self.as_of_lag)} before its event time")
        if self.dedupe:
            parts.append(f"{self.keep} version per {', '.join(self.dedupe)} by {self.order}")
        if self.columns:
            parts.append(f"columns {', '.join(self.columns)}")
        if self.limit is not None:
            parts.append(f"at most {self.limit}")
        if self.at_position is not None:
            parts.append(f"at position {format_position(pb.Position(next_offsets=self.at_position))}")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        """A plain, JSON-serialisable form (e.g. for a transformer's declared inputs)."""
        out = {}
        for f in dataclasses.fields(self):
            if f.name.startswith("_"):
                continue
            value = getattr(self, f.name)
            if f.name == "filters":
                value = [{"column": c.column, "op": c.op, "values": list(c.values)} for c in value]
            elif isinstance(value, tuple):
                value = list(value)
            if value is not None and value != [] and value != f.default:
                out[f.name] = value
        return out

    def __repr__(self) -> str:
        return f"<Query {self.describe()}>"


def _position(value) -> tuple[int, ...]:
    if isinstance(value, str):
        return tuple(parse_position(value).next_offsets)
    return tuple(int(v) for v in value)


def _ref(ref: str) -> pb.FeedRef:
    parts = ref.split("/")
    return pb.FeedRef(organization=parts[-3] if len(parts) == 3 else "", namespace=parts[-2] if len(parts) > 1 else "",
                      name=parts[-1])


def _duration(ns: int) -> str:
    for unit, size in (("d", 86_400e9), ("h", 3_600e9), ("m", 60e9), ("s", 1e9)):
        if ns >= size and ns % size == 0:
            return f"{int(ns // size)}{unit}"
    return f"{ns}ns"
