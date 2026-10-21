"""Declaring transformers: `@iso.transformer`, `iso.feed`, `iso.output`, and reads that work both
inside Isodrome (as known by the trigger) and in a notebook.

The contract with Isodrome's harness (schema version 1): `iso.transformer(**manifest)` sets
`fn.__isodrome_transformer__` to the manifest and returns `fn` unchanged; `iso.feed(...)` and
`iso.output(...)` are plain dicts. Inside Isodrome the module `isodrome_runtime` is importable and
`iso.get` / `iso.read` go through it (there is no network).
"""

from __future__ import annotations

import importlib.util
import re

MANIFEST_VERSION = 1
AS_OF = ("received", "published")
ON_RESTART = ("resume", "latest")
STATE_MAX_BYTES = 2 * 1024 * 1024  # ctx.state, serialised

_DURATION = re.compile(r"^\d+(\.\d+)?\s*(ns|us|ms|s|m|h|d|w)$")
_HORIZON_MAX_NS = 400 * 86_400 * 10**9


def inside_isodrome() -> bool:
    """True when running as a transformer in Isodrome (the harness provides `isodrome_runtime`)."""
    import sys

    return "isodrome_runtime" in sys.modules or importlib.util.find_spec("isodrome_runtime") is not None


# ---------- The manifest ----------


def transformer(name: str | None = None, **manifest):
    """Declares a transformer: Python that Isodrome runs on feeds' events to write a feed.

        @iso.transformer(
            name="forecast-errors",
            triggers={"obs": iso.feed("isodrome/public/met_eireann_observations", window="24h")},
            dependencies={"forecast": iso.feed("isodrome/public/met_eireann_point_forecast",
                                               horizon="24h")},
            output=iso.output("forecast_errors", key="station", time="observed_at"),
            as_of="published",
        )
        def errors(window, ctx):
            ...

    Fields: `triggers` and `dependencies` ({name: "feed" | iso.feed(...)}), `output` ("feed" |
    iso.output(...)), `as_of` ("received", the default, or "published"), `on_restart` ("resume"
    or "latest"), `state` (True: the code keeps `ctx.state`, see below).

    **`ctx.state`** (with `state=True`) is a dict the code keeps from one event to the next:
    running totals, ratings, standings. It holds JSON types only (str keys, lists not tuples),
    at most 2 MB serialised, and it is **only ever what replaying the triggers gives**: each new
    version replays every trigger event before going live, a backtest warms it up from the first
    trigger event, and it is never carried from one version to the next. So
    `on_restart="latest"` (which skips events) is refused with state.

    With `as_of="published"`, triggers are replayed in publication order (publication time,
    else event time), and each sees what had been published by then.

    Returns the function unchanged (so it can be called and tested directly).
    """
    _check(manifest)

    def decorate(fn):
        entry = dict(manifest)
        entry["manifest_version"] = MANIFEST_VERSION
        entry["name"] = name or fn.__name__.replace("_", "-")
        entry["entrypoint"] = f"{fn.__module__}:{fn.__qualname__}"
        fn.__isodrome_transformer__ = entry
        return fn

    return decorate


def _check(manifest: dict) -> None:
    """Mistakes worth knowing about before a deploy (the server checks everything again)."""
    state = manifest.get("state", False)
    if not isinstance(state, bool):
        raise TypeError("state= must be True or False")
    as_of = manifest.get("as_of")
    if as_of is not None and as_of not in AS_OF:
        raise ValueError(f"as_of= must be one of {', '.join(AS_OF)}, not {as_of!r}")
    on_restart = manifest.get("on_restart")
    if on_restart is not None and on_restart not in ON_RESTART:
        raise ValueError(f"on_restart= must be one of {', '.join(ON_RESTART)}, not {on_restart!r}")
    if state and on_restart == "latest":
        raise ValueError(
            'on_restart="latest" cannot be used with state=True: skipping events would make the '
            "state something no replay gives"
        )
    for kind in ("triggers", "dependencies"):
        inputs = manifest.get(kind, {})
        if not isinstance(inputs, dict):
            raise TypeError(f"{kind}= must be a dict of name: feed")
        for input_name, spec in inputs.items():
            if not isinstance(spec, (str, dict)):
                raise TypeError(f"{kind}[{input_name!r}] must be a feed reference or iso.feed(...)")
    if not manifest.get("triggers"):
        raise ValueError("a transformer needs at least one trigger: triggers={'name': 'feed'}")
    if "output" in manifest and not isinstance(manifest["output"], (str, dict)):
        raise TypeError("output= must be a feed name or iso.output(...)")


def _duration(value, what: str):
    if value is None or isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and _DURATION.match(value.strip()):
        return value
    raise ValueError(f"{what} {value!r}: use e.g. '90s', '10m', '24h', '7d' or nanoseconds")


def output(feed: str, key: str | None = None, time: str | None = None, publication_time: str | None = None,
           description: str = "") -> dict:
    """A transformer's output feed (in its namespace): its key field, the field holding each
    row's time (a row without it takes its trigger event's time), and its publication time."""
    return {"feed": feed, "key": key, "time": time, "publication_time": publication_time,
            "description": description}


class FeedSpec(dict):
    """`iso.feed(ref, window=..., horizon=...)`.

    In a transformer's declaration it is the plain dict Isodrome expects (`{"feed", "window",
    "horizon"}`). In a notebook it is also the feed itself: `iso.feed(ref).query(...)`,
    `.latest()`, `.tail()` and the rest connect (with `iso login`'s credentials) on first use.
    """

    __slots__ = ("_resolved",)

    def __init__(self, ref: str, window=None, horizon=None):
        super().__init__(feed=ref, window=window, horizon=horizon)
        self._resolved = None

    @property
    def ref(self) -> str:
        return self["feed"]

    def _feed(self):
        if self._resolved is None:
            if inside_isodrome():
                raise RuntimeError(
                    "inside a transformer, read feeds through ctx.<dependency>, iso.get or iso.read"
                )
            from isodrome import _client

            self._resolved = _client().feed(self["feed"])
        return self._resolved

    def __getattr__(self, name):
        # Python and tools probe objects for dunders (the harness looks for
        # __isodrome_transformer__ on everything a module defines): never connect for those.
        if name.startswith("__") or (name.startswith("_") and name != "_repr_html_"):
            raise AttributeError(name)
        if name == "_repr_html_" and inside_isodrome():
            raise AttributeError(name)
        return getattr(self._feed(), name)

    def __repr__(self) -> str:
        options = "".join(f", {k}={self[k]!r}" for k in ("window", "horizon") if self[k] is not None)
        return f"iso.feed({self['feed']!r}{options})"


def feed(ref: str, window=None, horizon=None) -> FeedSpec:
    """A feed: `"FEED"`, `"NAMESPACE/FEED"` or `"ORG/NAMESPACE/FEED"`, optionally `@version` or
    `:tag`.

    In a transformer's declaration: a trigger's `window` (`10` events, `"10m"` of event time, or
    `{"count"|"duration": …, "tumbling": bool, "all_keys": bool}`), or a dependency's `horizon`
    (how much event time it keeps in memory; default 24 h, at most 400 days).
    In a notebook: the feed itself (`iso.feed(ref).query(...).to_df()`).
    """
    if isinstance(window, (str, int)) and not isinstance(window, bool):
        _duration(window if isinstance(window, str) else None, "window")
    if horizon is not None:
        _duration(horizon, "horizon")
        if isinstance(horizon, str):
            from isodrome.parse import parse_duration

            ns = parse_duration(horizon)
        else:
            ns = horizon
        if ns > _HORIZON_MAX_NS:
            raise ValueError(f"horizon {horizon!r} is over the maximum of 400 days")
    return FeedSpec(ref, window=window, horizon=horizon)


# ---------- Reads that work inside Isodrome and out ----------


def _runtime():
    import importlib

    return importlib.import_module("isodrome_runtime") if inside_isodrome() else None


def get(feed_ref, key=None):
    """The latest event of `key` (or every key's latest, a list).

    Inside a transformer: as known by the trigger (so a backtest computes what live did), as
    events. In a notebook: a dict (or a list of dicts), from the server now."""
    runtime = _runtime()
    if runtime is not None:
        return runtime.get(_ref_text(feed_ref), key)
    from isodrome import _client

    rows = _client().feed(_ref_text(feed_ref)).latest(keys=None if key is None else [key]).to_df()
    records = rows.to_dict(orient="records")
    return records if key is None else (records[0] if records else None)


def read(feed_ref, start=None, end=None, limit=None, **options):
    """Events of a feed in an event-time range.

    Inside a transformer: `iso.read(feed, start=None, end=None, limit=1000)`, as known by the
    trigger, as events. In a notebook: a Result (`.to_df()`), with every query option:
    `since`, `where`, `columns`, `as_of` and `as_of_basis` ("received"/"published"),
    `as_of_lag`, `dedupe` with `keep` and `dedupe_order` ("arrival"/"publication"), `at`."""
    runtime = _runtime()
    if runtime is not None:
        if options:
            raise TypeError(f"inside a transformer iso.read takes feed, start, end, limit; not {sorted(options)}")
        return runtime.read(_ref_text(feed_ref), start=start, end=end, limit=1000 if limit is None else limit)
    query = _query(feed_ref, start=start, end=end, limit=limit, **options)
    return query.fetch()


def latest(feed_ref, keys=None, columns=None):
    """The newest event per key (or for `keys`), as a Result (`.to_df()`)."""
    from isodrome import _client

    return _client().feed(_ref_text(feed_ref)).latest(keys=keys, columns=columns)


def subscribe(feed_ref, start="now", **options):
    """History from `start` ("now", "beginning", a time) or the `last` N events, then live, as
    Results (one per batch). Options: `last`, `speed`, `where`, `columns`, `dedupe`, `follow`."""
    from isodrome import _client

    return _client().feed(_ref_text(feed_ref)).subscribe(start, **options)


def _query(feed_ref, **options):
    from isodrome import _client

    aliases = {"as_of_basis": "basis", "dedupe_order": "order"}
    options = {aliases.get(k, k): v for k, v in options.items() if v is not None}
    return _client().feed(_ref_text(feed_ref)).query(**options)


def _ref_text(feed_ref) -> str:
    if isinstance(feed_ref, dict):
        return feed_ref["feed"]
    if hasattr(feed_ref, "ref"):
        return feed_ref.ref
    return feed_ref
