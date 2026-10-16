"""A feed: its description, and everything you can do with it."""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator

import pyarrow as pa

from isodrome import errors
from isodrome import push as pusher
from isodrome.output import decode
from isodrome.parse import format_ns, short_enum, to_ns
from isodrome.query import TIME_COLUMNS, Query, conditions
from isodrome.result import Result
from isodrome.v1 import isodrome_pb2 as pb

if TYPE_CHECKING:
    import pandas as pd

    from isodrome.client import Client

_COLUMN_TYPES = {
    pb.COLUMN_TYPE_BOOL: "bool",
    pb.COLUMN_TYPE_INT64: "int64",
    pb.COLUMN_TYPE_FLOAT64: "float64",
    pb.COLUMN_TYPE_STRING: "string",
    pb.COLUMN_TYPE_JSON: "json",
}


@dataclass
class PushResult:
    accepted: int = 0
    duplicates: int = 0
    rejected: list[dict] = field(default_factory=list)  # {"row", "reason", "detail", "event"}

    def __repr__(self) -> str:
        text = f"<PushResult {self.accepted} accepted"
        if self.duplicates:
            text += f" ({self.duplicates} already sent)"
        if self.rejected:
            text += f", {len(self.rejected)} rejected"
        return text + ">"


class Feed:
    """A feed you can read (and, if it is your organization's, write).

    Get one with `client.feed("NAMESPACE/FEED")` or `iso.feed("ORG/NAMESPACE/FEED")`.
    """

    def __init__(self, client: Client, meta: pb.Feed, ref: pb.FeedRef, complete: bool = True):
        self._client_obj = client
        self._meta = meta
        self._pb_ref = ref
        self._complete = complete  # False when from a list, which has no columns or counts

    def _full(self) -> pb.Feed:
        if not self._complete:
            self.refresh()
        return self._meta

    @property
    def _client(self):
        return self._client_obj._transport

    # ----- description -----

    @property
    def ref(self) -> str:
        """ORGANIZATION/NAMESPACE/NAME: how to refer to this feed from anywhere."""
        return f"{self._meta.organization}/{self._meta.namespace}/{self._meta.name}"

    name = property(lambda self: self._meta.name)
    namespace = property(lambda self: self._meta.namespace)
    organization = property(lambda self: self._meta.organization)
    description = property(lambda self: self._meta.description)
    licence = property(lambda self: self._meta.licence)
    attribution = property(lambda self: self._meta.attribution)
    source_url = property(lambda self: self._meta.source_url)
    public = property(lambda self: self._meta.public)
    publication_time_field = property(lambda self: self._meta.publication_time_field or None)

    @property
    def key_field(self) -> str | None:
        return self._meta.key_field if self._meta.HasField("key_field") and self._meta.key_field else None

    @property
    def time_field(self) -> str | None:
        """The field events carry their time in; None if they are timed on arrival."""
        return None if self._meta.arrival_time else self._meta.time_field

    @property
    def columns(self) -> dict[str, str]:
        """The fields inferred from the events, with their types (besides the system columns
        `_event_time`, `_published_time`, `_receive_time`, `_key`, ...)."""
        return {c.name: _COLUMN_TYPES.get(c.type, "?") for c in self._full().columns}

    @property
    def events(self) -> int:
        """Events stored (flushed and pending)."""
        s = self._full().stats
        return s.events_flushed + s.events_pending_flush

    def refresh(self) -> Feed:
        """Fetch the description again (columns and counts change as events arrive)."""
        self._meta = errors.call(self._client.call, "GetFeed", pb.GetFeedRequest(feed=self._pb_ref))
        self._complete = True
        return self

    # ----- reading -----

    def query(self, **options) -> Query:
        """A query of this feed (lazy: `.to_df()` runs it).

        Options: `since` ("1h", "7d"), `start`/`end` (event time; end exclusive), `where`
        (`{"column": value}`, or `col(...)` conditions), `columns`, `limit`, `as_of` with
        `basis` ("received" or "published"), `as_of_lag` ("24h": each event as known that long
        before its own time), `dedupe` (columns) with `keep` ("last"/"first") and `order`
        ("arrival"/"publication"), `payload` (the original JSON), `at` (a position).
        """
        return Query.build(self, **options)

    def versions(self, **options) -> Query:
        """Every version of every event, with all three times: the raw material for asking what
        was known when. (A query without de-duplication, always including the time columns.)"""
        query = Query.build(self, **options)
        if query.dedupe:
            raise ValueError("versions() keeps every version; use query(dedupe=...) to keep one")
        if query.columns is not None:
            query = query.select(*dict.fromkeys(list(TIME_COLUMNS) + ["_key"] + list(query.columns)))
        return query

    @errors.translating
    def latest(self, keys=None, columns=None) -> Result:
        """The newest event (by event time) for each key, or for `keys` only."""
        if isinstance(keys, str):
            keys = [keys]
        if isinstance(columns, str):
            columns = [columns]
        response = errors.call(
            self._client.call,
            "Latest",
            pb.LatestRequest(feed=self._pb_ref, keys=list(keys or ()), columns=list(columns or ())),
        )
        table = decode(response.batch.ipc) or pa.table({})
        return Result(table=table, server_ns=response.server_ns, feed=self)

    def tail(self, last: int = 10, **options) -> Iterator[Result]:
        """The last `last` events, then new ones as they arrive, as Results (one per batch).
        Stop with `break`, or interrupt. `follow=False` stops after the history."""
        return self.subscribe(last=last, **options)

    def subscribe(
        self,
        start: Any = "now",
        *,
        last: int | None = None,
        speed: float | None = None,
        where=None,
        columns=None,
        dedupe=None,
        keep: str = "last",
        follow: bool = True,
    ) -> Iterator[Result]:
        """History from `start` ("now", "beginning", or a time), or the `last` N events, then
        live events, as Results (one per batch). `speed` paces the history by event time (1 =
        real time). `follow=False` stops once the history has been delivered."""
        request = pb.SubscribeRequest(
            feed=self._pb_ref,
            filters=[c.to_pb() for c in conditions(where)],
            columns=[columns] if isinstance(columns, str) else list(columns or ()),
            delivery=pb.DELIVERY_CONFIRMED,
        )
        request.include_payload = "_payload" in request.columns
        if last is not None:
            request.from_last = last
        elif start == "now":
            request.from_now = True
        elif start == "beginning":
            request.from_beginning = True
        else:
            request.from_event_time_ns = to_ns(start)
        if speed is not None:
            request.speed = speed
        if dedupe:
            request.dedupe.CopyFrom(pb.Dedupe(columns=[dedupe] if isinstance(dedupe, str) else list(dedupe),
                                              keep=pb.DEDUPE_KEEP_LAST if keep == "last" else pb.DEDUPE_KEEP_FIRST))
        return self._subscribe(request, follow)

    def _subscribe(self, request: pb.SubscribeRequest, follow: bool) -> Iterator[Result]:
        stream = self._client.stream("Subscribe", request)
        try:
            for message in stream:
                kind = message.WhichOneof("message")
                if kind == "batch":
                    table = decode(message.batch.ipc)
                    if table is not None and table.num_rows:
                        yield Result(table=table, feed=self)
                elif kind == "caught_up" and not follow:
                    return
        except Exception as e:
            import grpc

            if isinstance(e, grpc.RpcError) and e.code() != grpc.StatusCode.CANCELLED:
                raise errors.translate(e) from None
            if not isinstance(e, grpc.RpcError):
                raise
        finally:
            stream.cancel()

    async def subscribe_async(self, start: Any = "now", **options) -> AsyncIterator[Result]:
        """`subscribe`, as an async iterator (each batch is waited for in a worker thread)."""
        iterator = self.subscribe(start, **options)
        done = object()
        try:
            while True:
                result = await asyncio.to_thread(next, iterator, done)
                if result is done:
                    return
                yield result
        finally:
            iterator.close()

    def watch(self, last: int = 20, columns=None, where=None) -> None:
        """In Jupyter: a table of the latest `last` events that updates in place as events
        arrive. Interrupt the kernel (■) to stop."""
        import pandas as pd
        from IPython.display import display

        frames: list[pd.DataFrame] = []
        handle = display(pd.DataFrame(), display_id=True)
        try:
            for result in self.tail(last=last, columns=columns, where=where):
                frames.append(result.to_df())
                shown = pd.concat(frames, ignore_index=True).tail(last)
                frames = [shown]
                handle.update(shown)
        except KeyboardInterrupt:
            pass

    # ----- writing -----

    def push(self, data, *, raise_on_reject: bool = True, batch_size: int = pusher.DEFAULT_BATCH_SIZE) -> PushResult:
        """Send events: a pandas DataFrame, a pyarrow Table, a dict, or a list of dicts.

        Each event's message id is derived from the feed, its row number and its content, so
        pushing the same data again (re-running a cell) is answered "already sent" instead of
        writing twice. Rejected events raise `iso.Rejected` (with `.rejected`), unless
        `raise_on_reject=False`, when they are returned in the PushResult.
        """
        if self.organization and self.organization != self._client_obj.organization:
            raise errors.PermissionDenied(
                f"{self.ref} belongs to another organization: its public feeds can be read, but not changed"
            )
        rows = _rows(data)
        items = []
        for i, row in enumerate(rows):
            payload = json.dumps(_clean(row), separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            digest = hashlib.sha256(f"{self.ref}\0{i}\0".encode() + payload).digest()
            items.append(pusher.Item(source=str(i), payload=payload, message_id=digest[:16].hex()))
        try:
            sent = pusher.send(self._client, self._pb_ref, items, batch_size=batch_size)
        except Exception as e:
            import grpc

            if isinstance(e, grpc.RpcError):
                raise errors.translate(e) from None
            raise
        result = PushResult(accepted=sent.accepted, duplicates=sent.duplicates)
        for item, rejection in sent.rejected:
            result.rejected.append({
                "row": int(item.source) if item.source.isdigit() else None,
                "reason": short_enum(pb.RejectionReason, rejection.reason),
                "detail": rejection.detail,
                "event": item.payload.decode("utf-8", "replace"),
            })
        if result.rejected and raise_on_reject:
            first = result.rejected[0]
            raise errors.Rejected(
                f"{len(result.rejected)} of {len(items)} events rejected; first (row {first['row']}): "
                f"{first['reason']}: {first['detail']}",
                result,
            )
        return result

    # ----- display -----

    def __repr__(self) -> str:
        return f"<Feed {self.ref}: {self.events:,} events{', public' if self.public else ''}>"

    def _repr_html_(self) -> str:
        rows = [("feed", self.ref)]
        rows += [(k, v) for k, v in (
            ("description", self.description),
            ("source", self.source_url),
            ("licence", self.licence),
            ("attribution", self.attribution),
        ) if v]
        rows += [
            ("access", "public" if self.public else "your organization"),
            ("events", f"{self.events:,}"),
            ("key", self.key_field or "(none: one stream)"),
            ("event time", self.time_field or "(arrival)"),
        ]
        if self.publication_time_field:
            rows.append(("published time", self.publication_time_field))
        rows.append(("created", format_ns(self._meta.created_at_ns)))
        cols = ", ".join(f"{html.escape(n)} <span style='color:#888'>{t}</span>" for n, t in self.columns.items())
        rows.append(("columns", cols or "(none yet)"))
        body = "".join(
            f"<tr><th style='text-align:left;vertical-align:top;padding-right:1em'>{html.escape(k)}</th>"
            f"<td style='text-align:left'>{v if k == 'columns' else html.escape(str(v))}</td></tr>"
            for k, v in rows
        )
        return f"<table>{body}</table>"


def _rows(data) -> list[dict]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, pa.Table):
        return data.to_pylist()
    if hasattr(data, "to_dict") and hasattr(data, "columns"):  # pandas
        return data.to_dict(orient="records")
    if hasattr(data, "to_dicts"):  # polars
        return data.to_dicts()
    return list(data)


def _clean(value):
    """A value as JSON can hold it: missing values (None, NaN, NaT) become null, times RFC 3339
    strings, numpy numbers plain numbers; dicts and lists are cleaned throughout."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return None if value != value or value in (float("inf"), float("-inf")) else value
    if type(value).__name__ in ("NaTType", "NAType"):
        return None
    if hasattr(value, "isoformat") or type(value).__name__ == "datetime64":
        return format_ns(to_ns(value))
    if hasattr(value, "tolist"):  # numpy scalars and arrays
        return _clean(value.tolist())
    raise TypeError(f"cannot send {value!r} ({type(value).__name__}) as JSON")


class FeedList(list):
    """Feeds, displayed as a table. `.to_df()` for a DataFrame."""

    def to_df(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame([{
            "feed": f.ref,
            "public": f.public,
            "key": f.key_field,
            "event time": f.time_field or "(arrival)",
            "description": f.description,
        } for f in self])

    def _repr_html_(self) -> str:
        return self.to_df()._repr_html_()

    def __repr__(self) -> str:
        return self.to_df().to_string(index=False) if self else "FeedList([])"
