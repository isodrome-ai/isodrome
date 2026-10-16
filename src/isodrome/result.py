"""Results: what a query returned, as pandas (`.to_df()`), Arrow or Polars, with where it was read."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

import pyarrow as pa

if TYPE_CHECKING:
    import pandas as pd

    from isodrome._feed import Feed
    from isodrome.query import Query


class Result:
    """The events a query returned.

    `.to_df()` gives a pandas DataFrame (timestamps are UTC, to the nanosecond). `.position` is
    where in the feed's log the read ended: `query.at(result.position)` reads exactly the same
    events again. `.attribution` is the credit the data's source asks for.
    """

    def __init__(
        self,
        table: pa.Table | None = None,
        df: pd.DataFrame | None = None,
        position: tuple[int, ...] | None = None,
        server_ns: int = 0,
        feed: Feed | None = None,
        query: Query | None = None,
        estimate: dict | None = None,
    ):
        self._table = table
        self._df = df
        self.position = position
        self.server_ms = server_ns / 1e6
        self.feed = feed
        self.query = query
        self.estimate = estimate  # the server's size estimate before reading: {"rows", "bytes"}

    @property
    def attribution(self) -> str:
        return self.feed.attribution if self.feed is not None else ""

    def to_df(self) -> pd.DataFrame:
        """The events as a pandas DataFrame."""
        if self._df is None:
            self._df = self._table.to_pandas()
        return self._df

    def to_arrow(self) -> pa.Table:
        if self._table is None:
            self._table = pa.Table.from_pandas(self._df, preserve_index=False)
        return self._table

    def to_polars(self):
        try:
            import polars as pl
        except ImportError:
            raise ImportError("to_polars() needs polars: pip install 'isodrome[polars]'") from None
        return pl.from_arrow(self.to_arrow())

    @property
    def columns(self) -> list[str]:
        return list(self._df.columns) if self._df is not None else self._table.column_names

    def __len__(self) -> int:
        return len(self._df) if self._df is not None else self._table.num_rows

    def _summary(self) -> str:
        parts = [f"{len(self):,} events"]
        df = self.to_df()
        if "_event_time" in df and len(df):
            parts.append(f"event time {df['_event_time'].min()} to {df['_event_time'].max()}")
        if self.position is not None:
            parts.append("position " + ",".join(map(str, self.position)))
        return " · ".join(parts)

    def __repr__(self) -> str:
        text = f"<Result {self._summary()}>"
        if self.attribution:
            text += f"\nData: {self.attribution}"
        return text

    def _repr_html_(self) -> str:
        table = self.to_df().head(20)._repr_html_()
        footer = f"<p style='color:#666;font-size:85%'>{html.escape(self._summary())}"
        if len(self) > 20:
            footer += " (first 20 shown; .to_df() for all)"
        footer += "</p>"
        if self.attribution:
            footer += f"<p style='color:#666;font-size:85%'>Data: {html.escape(self.attribution)}</p>"
        return table + footer
