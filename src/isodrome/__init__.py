"""Isodrome: time-aware event feeds, from Python.

    import isodrome as iso

    client = iso.connect()                    # uses what `iso login` saved
    client.feeds()                            # yours, then other organizations' public ones
    forecast = client.feed("isodrome/public/ecmwf_open_data_forecast")
    df = forecast.query(since="3d", where={"_key": "dublin-airport"}).to_df()

`iso.feed(...)` and `iso.feeds()` use a default connection, made on first use.
"""

from __future__ import annotations

from isodrome._version import __version__
from isodrome.errors import (
    AlreadyExists,
    FailedPrecondition,
    InvalidArgument,
    IsodromeError,
    NotFound,
    PermissionDenied,
    Rejected,
    Unauthenticated,
    Unavailable,
)

__all__ = [
    "__version__",
    "connect",
    "feed",
    "feeds",
    "namespaces",
    "col",
    "as_of_join",
    "Client",
    "Feed",
    "Query",
    "Result",
    "IsodromeError",
    "Unauthenticated",
    "PermissionDenied",
    "NotFound",
    "AlreadyExists",
    "InvalidArgument",
    "FailedPrecondition",
    "Unavailable",
    "Rejected",
]

_default = None


def __getattr__(name):
    # The SDK's modules import pandas; loaded on first use so `iso` (the CLI) starts quickly.
    if name in ("connect", "Client"):
        from isodrome import client

        return getattr(client, name)
    if name == "Feed":
        from isodrome._feed import Feed

        return Feed
    if name in ("Query", "col"):
        from isodrome import query

        return getattr(query, name)
    if name == "Result":
        from isodrome.result import Result

        return Result
    if name == "as_of_join":
        from isodrome.pit import as_of_join

        return as_of_join
    raise AttributeError(f"module 'isodrome' has no attribute {name!r}")


def _client():
    global _default
    if _default is None:
        from isodrome.client import connect

        _default = connect()
    return _default


def feed(ref: str):
    """A feed, using the default connection: `iso.feed("isodrome/public/met_eireann_observations")`."""
    return _client().feed(ref)


def feeds(**options):
    """The feeds you can read, using the default connection (see Client.feeds)."""
    return _client().feeds(**options)


def namespaces(**options):
    """Namespaces, using the default connection (see Client.namespaces)."""
    return _client().namespaces(**options)
