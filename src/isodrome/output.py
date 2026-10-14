"""Query results: the server's Arrow IPC streams, printed as a table, JSON Lines or CSV."""

from __future__ import annotations

import csv
import json
import sys
from typing import IO, Iterable

import pyarrow as pa

from isodrome.parse import format_ns

FORMATS = ("table", "json", "csv")


def decode(ipc: bytes) -> pa.Table | None:
    """One self-contained Arrow IPC stream (schema + batches) → a table; None if empty."""
    if not ipc:
        return None
    with pa.ipc.open_stream(ipc) as reader:
        return reader.read_all()


def rows(table: pa.Table) -> list[dict]:
    """The table's rows as plain values: timestamps as RFC 3339 strings at full (ns) precision,
    and `_payload` (the original JSON event) parsed back into an object."""
    columns = {}
    for name, column in zip(table.column_names, table.columns):
        if pa.types.is_timestamp(column.type):
            ints = column.cast(pa.timestamp("ns", tz=column.type.tz)).cast(pa.int64()).to_pylist()
            columns[name] = [None if v is None else format_ns(v) for v in ints]
        elif name == "_payload" and pa.types.is_string(column.type):
            columns[name] = [None if v is None else json.loads(v) for v in column.to_pylist()]
        else:
            columns[name] = column.to_pylist()
    return [dict(zip(columns, values)) for values in zip(*columns.values())] if columns else []


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class Printer:
    """Prints rows as they arrive. A table is aligned per call (one call per batch), so a
    streaming `tail` prints its header once and then a line per event."""

    def __init__(self, fmt: str = "table", out: IO[str] | None = None, max_width: int = 60):
        if fmt not in FORMATS:
            raise ValueError(f"unknown format {fmt!r}; one of {', '.join(FORMATS)}")
        self.fmt = fmt
        self.out = out or sys.stdout
        self.max_width = max_width
        self.count = 0
        self._header: list[str] | None = None
        self._widths: list[int] | None = None
        self._csv = csv.writer(self.out) if fmt == "csv" else None

    def table(self, table: pa.Table | None) -> None:
        if table is not None and table.num_rows:
            self.rows(rows(table), table.column_names)

    def rows(self, items: Iterable[dict], columns: list[str]) -> None:
        items = list(items)
        self.count += len(items)
        if self.fmt == "json":
            for row in items:
                print(json.dumps(row, separators=(",", ":"), ensure_ascii=False), file=self.out)
        elif self.fmt == "csv":
            if self._header is None:
                self._header = columns
                self._csv.writerow(columns)
            for row in items:
                self._csv.writerow([_cell(row.get(c)) for c in self._header])
        else:
            self._print_table(items, columns)
        self.out.flush()

    def _print_table(self, items: list[dict], columns: list[str]) -> None:
        cells = [[_truncate(_cell(row.get(c)), self.max_width) for c in columns] for row in items]
        if self._header != columns:
            self._header = columns
            self._widths = [max([len(c)] + [len(r[i]) for r in cells]) for i, c in enumerate(columns)]
            print("  ".join(c.ljust(w) for c, w in zip(columns, self._widths)).rstrip(), file=self.out)
        for r in cells:
            print("  ".join(v.ljust(w) for v, w in zip(r, self._widths)).rstrip(), file=self.out)

    def finish(self, empty_message: str = "(no rows)") -> None:
        if self.count == 0 and self.fmt == "table":
            print(empty_message, file=self.out)


def _truncate(text: str, width: int) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + "…"
