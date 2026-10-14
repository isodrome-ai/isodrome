"""Parsing command-line values into API values: times, durations, filters, positions."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from isodrome.v1 import isodrome_pb2 as pb

_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(ns|us|ms|s|m|h|d|w)")
_UNIT_NS = {
    "ns": 1,
    "us": 1_000,
    "ms": 1_000_000,
    "s": 1_000_000_000,
    "m": 60 * 1_000_000_000,
    "h": 3600 * 1_000_000_000,
    "d": 86400 * 1_000_000_000,
    "w": 7 * 86400 * 1_000_000_000,
}


def now_ns() -> int:
    return time.time_ns()


def parse_duration(text: str) -> int:
    """`90s`, `15m`, `1h30m`, `7d` → nanoseconds."""
    text = text.strip().lower()
    total, pos = 0, 0
    for match in _DURATION.finditer(text):
        if match.start() != pos:
            break
        total += int(float(match.group(1)) * _UNIT_NS[match.group(2)])
        pos = match.end()
    if pos != len(text) or not text:
        raise ValueError(f"{text!r} is not a duration; try e.g. 30s, 15m, 1h or 7d")
    return total


def parse_time(text: str) -> int:
    """RFC 3339 (`2026-10-13T16:00:00Z`, fractions to the nanosecond), a date (`2026-10-13`, UTC
    midnight), integer nanoseconds, or `now`."""
    text = text.strip()
    if text == "now":
        return now_ns()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    match = re.fullmatch(r"(.+?T\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?(Z|[+-]\d\d:?\d\d)?", text, re.IGNORECASE)
    try:
        if match:
            base, fraction, zone = match.groups()
            zone = "+00:00" if zone in (None, "Z", "z") else zone
            seconds = datetime.fromisoformat(base + zone)
            nanos = int((fraction or "").ljust(9, "0"))
            return int(seconds.timestamp()) * 1_000_000_000 + nanos
        day = datetime.fromisoformat(text)
        if day.tzinfo is None:
            day = day.replace(tzinfo=timezone.utc)
        return int(day.timestamp()) * 1_000_000_000
    except ValueError:
        pass
    raise ValueError(f"{text!r} is not a time; use RFC 3339 (2026-10-13T16:00:00Z) or integer nanoseconds")


def format_ns(ns: int) -> str:
    """Nanoseconds → RFC 3339 UTC, with as many fraction digits as needed (0, 3, 6 or 9)."""
    seconds, nanos = divmod(ns, 1_000_000_000)
    text = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    if nanos:
        digits = 3 if nanos % 1_000_000 == 0 else 6 if nanos % 1_000 == 0 else 9
        text += "." + f"{nanos:09d}"[:digits]
    return text + "Z"


def short_enum(enum_type, value: int) -> str:
    """`pb.AckMode`, 1 → `replicated`."""
    name = enum_type.Name(value)
    prefix = enum_type.DESCRIPTOR.values[0].name.rsplit("_", 1)[0] + "_"  # e.g. ACK_MODE_
    return name.removeprefix(prefix).lower()


def parse_filter(text: str) -> pb.Filter:
    """`column OP value` with `=`, `!=`, `<`, `<=`, `>`, `>=`; `column in (a, b)`;
    `column is null`; `column is not null`. Values: integers, decimals, `true`/`false`, or
    strings (optionally quoted)."""
    lower = text.lower()

    def make(column: str, op: int, values: list[pb.Value]) -> pb.Filter:
        column = column.strip()
        if not column:
            raise ValueError(f"filter {text!r} names no column")
        return pb.Filter(column=column, op=op, values=values)

    if (i := lower.find(" is not null")) >= 0:
        return make(text[:i], pb.FILTER_OP_IS_NOT_NULL, [])
    if (i := lower.find(" is null")) >= 0:
        return make(text[:i], pb.FILTER_OP_IS_NULL, [])
    if (i := lower.find(" in ")) >= 0:
        items = text[i + 4 :].strip()
        if not (items.startswith("(") and items.endswith(")")):
            raise ValueError(f"expected `{text[:i].strip()} in (a, b)`")
        values = [parse_value(v) for v in items[1:-1].split(",")]
        return make(text[:i], pb.FILTER_OP_IN, values)
    for symbol, op in (
        ("<=", pb.FILTER_OP_LTE),
        (">=", pb.FILTER_OP_GTE),
        ("!=", pb.FILTER_OP_NE),
        ("==", pb.FILTER_OP_EQ),
        ("=", pb.FILTER_OP_EQ),
        ("<", pb.FILTER_OP_LT),
        (">", pb.FILTER_OP_GT),
    ):
        if (i := text.find(symbol)) >= 0:
            return make(text[:i], op, [parse_value(text[i + len(symbol) :])])
    raise ValueError(f"cannot parse filter {text!r}; try e.g. 'pitch.velocity>98' or 'result in (ball, foul)'")


def parse_value(text: str) -> pb.Value:
    text = text.strip()
    if re.fullmatch(r"-?\d+", text):
        return pb.Value(int_value=int(text))
    try:
        return pb.Value(float_value=float(text))
    except ValueError:
        pass
    if text in ("true", "false"):
        return pb.Value(bool_value=text == "true")
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    return pb.Value(string_value=text)


def parse_position(text: str) -> pb.Position:
    """`12,0,7` → a position (the next offset of each partition)."""
    try:
        return pb.Position(next_offsets=[int(o) for o in text.split(",")])
    except ValueError:
        raise ValueError(f"{text!r} is not a comma-separated list of offsets") from None


def format_position(position: pb.Position) -> str:
    return ",".join(str(o) for o in position.next_offsets)
