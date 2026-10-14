"""Configuration, endpoints, output formatting and event parsing, without a server."""

import io
import json
import stat

import pyarrow as pa
import pytest

from fakes import ipc

from isodrome import output, push
from isodrome.client import DEFAULT_ENDPOINT, Endpoint, key_id
from isodrome.config import Config, Profile, config_path


def test_config_round_trip_is_private(config_dir):
    config = Config(current="local")
    config.profiles["local"] = Profile(endpoint="http://localhost:7470", api_key='iso_a_b"c', namespace="ns")
    config.profile("cloud")
    path = config.save()
    assert path == config_path() and path.parent == config_dir
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    loaded = Config.load()
    assert loaded.current == "local"
    assert loaded.profiles["local"] == config.profiles["local"]
    assert loaded.profiles["cloud"] == Profile(endpoint=DEFAULT_ENDPOINT)


def test_missing_config_is_empty():
    assert Config.load().profile().endpoint == DEFAULT_ENDPOINT


def test_endpoints():
    e = Endpoint.parse("https://stg.api.isodrome.ai/")
    assert (e.target, e.tls, e.http_base()) == ("stg.api.isodrome.ai:443", True, "https://stg.api.isodrome.ai")
    e = Endpoint.parse("http://localhost:7470")
    assert (e.target, e.tls, e.http_base()) == ("localhost:7470", False, "http://localhost:7471")
    assert Endpoint.parse("example.com").tls
    with pytest.raises(ValueError):
        Endpoint.parse("ftp://x")


def test_key_id():
    assert key_id("iso_abc123_SECRET") == "abc123"
    with pytest.raises(ValueError):
        key_id("sk-whatever")


def test_parse_events():
    assert [p for _, p in push.parse_events('{"a": 1}')] == [b'{"a":1}']
    assert [p for _, p in push.parse_events('[{"a": 1}, {"a": 2}]')] == [b'{"a":1}', b'{"a":2}']
    jsonl = '{"a": 1}\n\nnot json\n{"a": 3}\n'
    events = list(push.parse_events(jsonl, "f.jsonl"))
    # Invalid lines are sent anyway, so that the server's rejection is reported.
    assert events == [("f.jsonl:1", b'{"a": 1}'), ("f.jsonl:3", b"not json"), ("f.jsonl:4", b'{"a": 3}')]
    assert list(push.parse_events("  ")) == []
    with pytest.raises(ValueError):
        list(push.parse_events("[1, 2"))


def test_batches_by_count_and_bytes():
    items = [push.Item("x", b"x" * 100) for _ in range(10)]
    assert [len(b) for b in push.batches(items, size=4)] == [4, 4, 2]
    assert [len(b) for b in push.batches(items, size=100, max_bytes=600)] == [3, 3, 3, 1]
    assert len({i.message_id for i in items}) == 10


def _table():
    return pa.table({
        "_event_time": pa.array([1_704_067_200_000_000_001, None], pa.timestamp("ns", tz="UTC")),
        "price": [1.5, None],
        "_payload": ['{"price": 1.5}', None],
    })


def test_decode_and_rows():
    table = output.decode(ipc(_table()))
    assert output.decode(b"") is None
    assert output.rows(table) == [
        {"_event_time": "2024-01-01T00:00:00.000000001Z", "price": 1.5, "_payload": {"price": 1.5}},
        {"_event_time": None, "price": None, "_payload": None},
    ]


@pytest.mark.parametrize("fmt", output.FORMATS)
def test_printer_formats(fmt):
    out = io.StringIO()
    printer = output.Printer(fmt, out)
    printer.table(_table())
    printer.table(_table().slice(0, 1))
    text = out.getvalue().splitlines()
    if fmt == "json":
        assert json.loads(text[0])["_payload"] == {"price": 1.5} and len(text) == 3
    elif fmt == "csv":
        assert text[0] == "_event_time,price,_payload" and len(text) == 4  # header once
        assert text[1] == '2024-01-01T00:00:00.000000001Z,1.5,"{""price"":1.5}"'
    else:
        assert text[0].split() == ["_event_time", "price", "_payload"] and len(text) == 4
    assert printer.count == 3
