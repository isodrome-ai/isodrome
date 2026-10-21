import pytest

from isodrome.parse import (
    format_ns,
    parse_duration,
    parse_filter,
    parse_position,
    parse_time,
    short_enum,
)
from isodrome.v1 import isodrome_pb2 as pb


def test_times():
    assert parse_time("1700000000000000000") == 1_700_000_000_000_000_000
    assert parse_time("2024-01-01T00:00:00Z") == 1_704_067_200_000_000_000
    assert parse_time("2024-01-01T00:00:00.000000001Z") == 1_704_067_200_000_000_001
    assert parse_time("2024-01-01T01:00:00+01:00") == 1_704_067_200_000_000_000
    assert parse_time("2024-01-01") == 1_704_067_200_000_000_000
    # Without seconds, with a space, or a zone without a colon (Python 3.10's fromisoformat refuses these).
    assert parse_time("2024-01-01T00:00Z") == parse_time("2024-01-01 00:00") == 1_704_067_200_000_000_000
    assert parse_time("2024-01-01T01:00+0100") == 1_704_067_200_000_000_000
    with pytest.raises(ValueError):
        parse_time("yesterday")


def test_format_ns_round_trips():
    for text in ("2024-01-01T00:00:00Z", "2024-01-01T00:00:00.5Z".replace(".5", ".500"),
                 "2024-01-01T00:00:00.000001Z", "2024-01-01T00:00:00.000000001Z"):
        assert format_ns(parse_time(text)) == text


def test_durations():
    assert parse_duration("90s") == 90 * 10**9
    assert parse_duration("1h30m") == 5400 * 10**9
    assert parse_duration("7d") == 7 * 86400 * 10**9
    assert parse_duration("250ms") == 250 * 10**6
    for bad in ("", "1x", "h", "1h 2"):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_filters():
    f = parse_filter("pitch.velocity>98")
    assert (f.column, f.op, f.values[0].int_value) == ("pitch.velocity", pb.FILTER_OP_GT, 98)
    f = parse_filter("pitch.velocity >= 98.5")
    assert (f.op, f.values[0].float_value) == (pb.FILTER_OP_GTE, 98.5)
    assert parse_filter("result = 'ball'").values[0].string_value == "ball"
    f = parse_filter("result in (ball, foul)")
    assert (f.op, [v.string_value for v in f.values]) == (pb.FILTER_OP_IN, ["ball", "foul"])
    assert parse_filter("spin is not null").op == pb.FILTER_OP_IS_NOT_NULL
    assert parse_filter("spin IS NULL").op == pb.FILTER_OP_IS_NULL
    assert parse_filter("live!=true").values[0].bool_value is True
    assert parse_filter("live!=true").values[0].WhichOneof("kind") == "bool_value"
    for bad in ("nonsense", ">5", "x in ball"):
        with pytest.raises(ValueError):
            parse_filter(bad)


def test_positions():
    assert list(parse_position("12, 0,7").next_offsets) == [12, 0, 7]
    with pytest.raises(ValueError):
        parse_position("12,x")


def test_short_enum():
    assert short_enum(pb.AckMode, pb.ACK_MODE_REPLICATED) == "replicated"
    assert short_enum(pb.Role, pb.ROLE_ADMIN) == "admin"
    assert short_enum(pb.Role, pb.ROLE_OWNER) == "owner"
    assert short_enum(pb.Role, 99) == "unknown (99)"   # a newer server's value
    assert short_enum(pb.ColumnType, pb.COLUMN_TYPE_FLOAT64) == "float64"
    assert short_enum(pb.RejectionReason, pb.REJECTION_REASON_MISSING_EVENT_TIME) == "missing_event_time"
