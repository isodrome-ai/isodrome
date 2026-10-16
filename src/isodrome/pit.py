"""Point-in-time joins: for each row of your data, what a feed said at that row's time."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from isodrome.query import TIME_COLUMNS, Col, Query

if TYPE_CHECKING:
    from isodrome._feed import Feed


def as_of_join(
    left: pd.DataFrame,
    right: Feed | Query,
    *,
    at: str,
    key: str | None = None,
    basis: str = "published",
    columns=None,
    suffix: str = "_right",
) -> pd.DataFrame:
    """For each row of `left`, the latest event of `right` that had happened **and** was known
    by the row's time `at`: no look-ahead.

    - `at`: the column of `left` holding each row's time.
    - `key`: the column of `left` matched against `right`'s key (`_key`); None for an unkeyed feed.
    - `basis`: "published" (known = the source's publication time, else receive time) or
      "received" (known = when Isodrome received it).
    - `columns`: `right`'s columns to bring over (default: all of them). The matched event's
      `_event_time`, `_published_time` and `_receive_time` always come too.

    "Latest" means the newest event time among those known; between versions of one event, the
    one known last. Rows with nothing known yet get missing values. `right` may be a feed or a
    query of one (its `where`, `start`/`since` and `as_of` still apply); its versions are read
    up to the latest `at`, for the keys present in `left`.

    Example: each trade with the forecast temperature that was public when it was made:

        iso.as_of_join(trades, forecast, at="time", key="location", columns=["t2m_k"])
    """
    if basis not in ("published", "received"):
        raise ValueError("basis= must be 'published' or 'received'")
    query = right if isinstance(right, Query) else right.query()
    if query.dedupe or query.as_of_lag is not None:
        raise ValueError("pass a query without dedupe= or as_of_lag=: the join chooses the version itself")
    times = pd.to_datetime(left[at], utc=True).astype("datetime64[ns, UTC]")  # Isodrome's resolution
    if times.isna().any():
        raise ValueError(f"left[{at!r}] has missing times")
    wanted = list(columns) if columns is not None else (list(query.columns) if query.columns else None)

    versions = query._with(end=times.max() + pd.Timedelta(1, "ns"))
    if key is not None:
        keys = [k for k in pd.unique(left[key]) if k == k]
        versions = versions.where(Col("_key").isin(keys))
    if wanted is not None:
        versions = versions.select(*dict.fromkeys(list(TIME_COLUMNS) + ["_key"] + wanted))
    r = versions.fetch().to_df()

    out = left.copy()
    if not len(r):
        for column in wanted or []:
            out[column if column not in out else column + suffix] = np.nan
        return out
    if "_published_time" not in r:
        r["_published_time"] = pd.NaT
    for column in TIME_COLUMNS:
        r[column] = pd.to_datetime(r[column], utc=True).astype("datetime64[ns, UTC]")
    known = r["_published_time"].fillna(r["_receive_time"]) if basis == "published" else r["_receive_time"]
    # A version is usable from the moment it had both happened and been known.
    r = r.assign(_known=known, _usable=r["_event_time"].where(r["_event_time"] >= known, known))
    # Rank versions by (event time, known time): the answer at any moment is the highest-ranked
    # usable version, i.e. the running maximum of the rank in order of becoming usable.
    r = r.sort_values(["_event_time", "_known"], kind="stable").reset_index(drop=True)
    r["_rank"] = np.arange(len(r))
    by_usable = r.sort_values("_usable", kind="stable")
    group = by_usable["_key"] if key is not None else pd.Series(0, index=by_usable.index)
    by_usable = by_usable.assign(_best=by_usable.groupby(group, dropna=False)["_rank"].cummax())

    lookup = by_usable[["_usable", "_best"] + (["_key"] if key is not None else [])]
    probe = pd.DataFrame({"_at": times.reset_index(drop=True), "_row": np.arange(len(left))})
    if key is not None:
        probe["_key"] = left[key].reset_index(drop=True)
    matched = pd.merge_asof(
        probe.sort_values("_at", kind="stable"),
        lookup.sort_values("_usable", kind="stable"),
        left_on="_at",
        right_on="_usable",
        by="_key" if key is not None else None,
        direction="backward",
        allow_exact_matches=True,
    ).sort_values("_row")

    # The matched event's three times always come along, so the absence of look-ahead can be checked.
    bring = list(TIME_COLUMNS) + (
        [c for c in wanted if c not in TIME_COLUMNS] if wanted is not None
        else [c for c in r.columns if not c.startswith("_")]
    )
    best = matched["_best"].to_numpy(dtype=float)
    rows = np.where(np.isnan(best), -1, best).astype(int)  # -1: nothing known yet (a missing row)
    picked = r[bring].reindex(rows)
    picked.index = out.index
    for column in bring:
        out[column if column not in out else column + suffix] = picked[column]
    return out
