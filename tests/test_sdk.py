"""The Python SDK: queries, results, point-in-time logic, push, errors."""

import json

import pandas as pd
import pyarrow as pa
import pytest

from fakes import KEY

import isodrome as iso
from isodrome.query import Query, _Read
from isodrome.v1 import isodrome_pb2 as pb

T = pd.Timestamp


@pytest.fixture
def client(fake):
    with iso.connect(endpoint=fake.endpoint, api_key=KEY) as c:
        yield c


def _ns(text):
    return T(text, tz="UTC").value


# ---------- Building requests ----------


def test_query_maps_onto_the_read_request(client, fake):
    client.create_feed("t", key="symbol", time_field="event_time")
    feed = client.feed("t")
    q = feed.query(
        start="2026-10-01", end=T("2026-10-02", tz="UTC"), where={"_key": ["a", "b"], "kind": "x", "n": None},
        columns=["price"], limit=5, as_of="2026-10-01T12:00Z", basis="published",
        dedupe=["_key"], keep="first", order="publication",
    ).where(iso.col("price") >= 1.5)
    q.fetch()
    r = fake.last_read
    assert (r.feed.namespace, r.feed.name) == ("", "t")
    assert (r.start_event_time_ns, r.end_event_time_ns) == (_ns("2026-10-01"), _ns("2026-10-02"))
    assert (r.as_of_ns, r.as_of_basis) == (_ns("2026-10-01T12:00"), pb.AS_OF_BASIS_PUBLISHED)
    assert [(f.column, f.op) for f in r.filters] == [
        ("_key", pb.FILTER_OP_IN), ("kind", pb.FILTER_OP_EQ), ("n", pb.FILTER_OP_IS_NULL), ("price", pb.FILTER_OP_GTE),
    ]
    assert r.filters[3].values[0].float_value == 1.5
    assert (list(r.columns), r.limit) == (["price"], 5)
    assert (list(r.dedupe.columns), r.dedupe.keep, r.dedupe.order) == (["_key"], pb.DEDUPE_KEEP_FIRST,
                                                                      pb.DEDUPE_ORDER_PUBLICATION)


def test_since_is_relative_to_when_the_query_runs(client, fake):
    client.create_feed("t")
    q = client.feed("t").query(since="1h")
    before = pd.Timestamp.now(tz="UTC").value
    q.fetch()
    assert abs(fake.last_read.start_event_time_ns - (before - 3600 * 10**9)) < 5 * 10**9


def test_queries_are_immutable_and_describe_themselves(client):
    client.create_feed("t")
    base = client.feed("t").query(since="7d")
    narrowed = base.where(symbol="AAPL").select("price")
    assert base.filters == () and base.columns is None
    assert "where col('symbol') == 'AAPL'" in repr(narrowed) and "since 7d ago" in repr(narrowed)
    assert narrowed.to_dict() == {
        "feed": "acme/default/t", "since": 7 * 86400 * 10**9,
        "filters": [{"column": "symbol", "op": "==", "values": ["AAPL"]}], "columns": ["price"],
    }


def test_bad_query_options():
    feed_q = Query(feed="a/b/c")
    with pytest.raises(ValueError):
        feed_q.replace(basis="sometime")
    with pytest.raises(TypeError):
        feed_q.replace(nonsense=1)
    with pytest.raises(ValueError):
        feed_q.replace(since="1h", start="2026-01-01")
    with pytest.raises(TypeError):
        (iso.col("a") == 1) | (iso.col("b") == 2)
    with pytest.raises(TypeError):
        feed_q.where(iso.col("a"))


# ---------- Results ----------


def test_results_convert_and_record_their_position(client, fake):
    client.create_feed("t")
    feed = client.feed("t")
    feed.push([{"price": 1.0}, {"price": 2.5}])
    result = feed.query().fetch()
    df = result.to_df()
    assert isinstance(df, pd.DataFrame) and list(df["price"]) == [1.0, 2.5]
    assert str(df["_event_time"].dtype) == "datetime64[ns, UTC]"
    assert result.position == (2,) and len(result) == 2
    assert feed.query().to_df().equals(df)
    feed.query().at(result.position).fetch()
    assert list(fake.last_read.at_position.next_offsets) == [2]
    assert feed.query().count() == 2


def test_results_and_feeds_display_in_jupyter(client, fake):
    fake.add_public_feed()
    forecasts = client.feed("isodrome/public/forecasts")
    page = forecasts._repr_html_()
    assert "Copyright Met Éireann" in page and "CC BY 4.0" in page
    result = forecasts.query().fetch()
    assert "Data: Copyright Met Éireann" in result._repr_html_() and "Data: Copyright" in repr(result)
    listed = client.feeds()
    assert "isodrome/public/forecasts" in listed.to_df()["feed"].tolist()
    assert "<table" in listed._repr_html_()


# ---------- Point in time, computed locally ----------


def _versions(rows):
    """A versions table: (key, event, published or None, received, value)."""
    col = lambda i: [r[i] for r in rows]  # noqa: E731
    ts = lambda values: pa.array([None if v is None else _ns(v) for v in values], pa.timestamp("ns", tz="UTC"))  # noqa: E731
    return pa.table({
        "_key": col(0), "_event_time": ts(col(1)), "_published_time": ts(col(2)), "_receive_time": ts(col(3)),
        "value": pa.array(col(4), pa.float64()),
    })


@pytest.fixture
def versions(monkeypatch):
    """Makes every query read the given versions instead of asking the server."""
    holder = {}

    def fake_read(self, request):
        holder["request"] = request
        return _Read(table=holder["table"], position=(len(holder["table"]),))

    monkeypatch.setattr(Query, "_read", fake_read)

    def set_table(rows):
        holder["table"] = _versions(rows)
        return holder

    return set_table


FORECASTS = [
    # key, event time,        published,            received,            value
    ("A", "2026-10-16T12:00", "2026-10-16T06:00", "2026-10-16T06:01", 1.0),  # run at 06
    ("A", "2026-10-16T12:00", "2026-10-16T09:00", "2026-10-16T09:01", 2.0),  # run at 09
    ("A", "2026-10-16T12:00", "2026-10-16T11:30", "2026-10-16T11:31", 3.0),  # run at 11:30
    ("A", "2026-10-16T13:00", "2026-10-16T06:00", "2026-10-16T06:01", 4.0),
    ("B", "2026-10-16T12:00", "2026-10-16T09:00", "2026-10-16T09:01", 9.0),
]


def test_as_of_lag_keeps_each_event_as_known_before_it(client, fake, versions):
    client.create_feed("t")
    held = versions(FORECASTS)
    q = client.feed("t").query(as_of_lag="2h", basis="published", dedupe=["_key", "_event_time"], order="publication")
    df = q.to_df()
    # 12:00 known by 10:00: the 09:00 run; 13:00 known by 11:00: the 06:00 run.
    assert list(zip(df["_key"], df["value"])) == [("A", 2.0), ("B", 9.0), ("A", 4.0)]
    # The server was asked for every version (no dedupe, no limit) with the times needed.
    assert not held["request"].HasField("dedupe")
    q3 = client.feed("t").query(as_of_lag="3h", dedupe=["_key", "_event_time"], basis="received")
    assert list(q3.to_df()["value"]) == [1.0, 4.0]  # 12:00 known by 09:00 received: the 06:00 run


def test_filters_never_bring_back_a_superseded_version(client, fake, versions):
    client.create_feed("t")
    held = versions(FORECASTS)
    q = client.feed("t").query(as_of_lag="0s", basis="published", dedupe=["_key", "_event_time"],
                               where=[iso.col("value") == 1.0, iso.col("_key") == "A"])
    # The newest version of A/12:00 is 3.0, so asking for value == 1.0 finds nothing, as on the server.
    assert len(q.to_df()) == 0
    # Only the filter on a de-duplication column went to the server; the other waited.
    assert [f.column for f in held["request"].filters] == ["_key"]


OBSERVATIONS = [
    ("dub", "2026-10-16T09:00", "2026-10-16T09:20", "2026-10-16T09:25", 10.0),
    ("dub", "2026-10-16T09:00", "2026-10-16T10:15", "2026-10-16T10:16", 10.5),  # a correction
    ("dub", "2026-10-16T10:00", "2026-10-16T10:20", "2026-10-16T10:21", 11.0),
    ("dub", "2026-10-16T08:00", "2026-10-16T10:40", "2026-10-16T10:41", 99.0),  # late, older event
    ("cork", "2026-10-16T09:00", None, "2026-10-16T09:10", 7.0),
]


def test_as_of_join_has_no_look_ahead(client, fake, versions):
    client.create_feed("t")
    versions(OBSERVATIONS)
    left = pd.DataFrame({
        "at": pd.to_datetime(["2026-10-16T09:10Z", "2026-10-16T09:30Z", "2026-10-16T10:17Z",
                              "2026-10-16T10:30Z", "2026-10-16T10:50Z", "2026-10-16T09:15Z"]),
        "station": ["dub", "dub", "dub", "dub", "dub", "cork"],
    })
    out = iso.as_of_join(left, client.feed("t"), at="at", key="station", columns=["value"])
    # 09:10 nothing published yet; 09:30 the first reading; 10:17 its correction (10:00 not yet
    # published); 10:30 the 10:00 reading; 10:50 still 10:00 (the late 08:00 event is older);
    # cork has no publication time, so its receive time counts.
    assert out["value"].tolist()[1:] == [10.0, 10.5, 11.0, 11.0, 7.0]
    assert pd.isna(out["value"].iloc[0])
    assert out["_event_time"].iloc[2] == T("2026-10-16T09:00", tz="UTC")
    assert list(out.columns[:2]) == ["at", "station"]


# ---------- Writing ----------


def test_push_from_a_dataframe_is_idempotent(client, fake):
    feed = client.create_feed("prices")
    df = pd.DataFrame({
        "symbol": ["a", "b"], "price": [1.5, float("nan")],
        "at": pd.to_datetime(["2026-10-16T09:00:00.000000001Z", None]),
    })
    first = feed.push(df)
    assert (first.accepted, first.duplicates) == (2, 0)
    again = feed.push(df)
    assert (again.accepted, again.duplicates) == (2, 2)
    stored = [body for _, body in fake.events[("default", "prices")]]
    assert stored[0] == {"symbol": "a", "price": 1.5, "at": "2026-10-16T09:00:00.000000001Z"}
    assert stored[1] == {"symbol": "b", "price": None, "at": None}


def test_rejections_raise_unless_asked_not_to(client, fake):
    feed = client.create_feed("prices")
    with pytest.raises(iso.Rejected) as caught:
        feed.push([{"price": 1}, {"nope": 2}])
    assert caught.value.rejected[0]["row"] == 1 and caught.value.rejected[0]["reason"] == "missing_key"
    result = feed.push([{"nope": 3}], raise_on_reject=False)
    assert len(result.rejected) == 1 and json.loads(result.rejected[0]["event"]) == {"nope": 3}


def test_another_organizations_feeds_cannot_be_pushed_to(client, fake):
    fake.add_public_feed()
    with pytest.raises(iso.PermissionDenied):
        client.feed("isodrome/public/forecasts").push({"price": 1})


# ---------- Connecting and errors ----------


def test_errors_are_typed(client, fake):
    with pytest.raises(iso.NotFound):
        client.feed("missing")
    with pytest.raises(iso.Unauthenticated):
        iso.connect(endpoint=fake.endpoint, api_key="iso_x_wrong").whoami()


def test_connect_uses_the_saved_login(iso_cli_login, fake):
    client = iso.connect()
    assert client.whoami().email == "a@acme.io"
    assert "a@acme.io" in client._repr_html_()


def test_connect_without_a_login():
    with pytest.raises(iso.Unauthenticated, match="iso login"):
        iso.connect()


@pytest.fixture
def iso_cli_login(iso):
    assert iso("login", "--api-key", KEY, key=False).exit_code == 0


# ---------- Where the server can do it ----------


def test_as_of_lag_goes_to_the_server_where_it_can(client, fake):
    fake.capabilities = ["read.as_of_lag"]
    client.create_feed("t")
    feed = client.feed("t")
    feed.query(as_of_lag="24h", basis="published", dedupe=["_key", "_event_time"], order="publication",
               where=iso.col("price") > 1, limit=3).fetch()
    r = fake.last_read
    assert (r.as_of_lag_ns, r.as_of_basis) == (24 * 3600 * 10**9, pb.AS_OF_BASIS_PUBLISHED)
    assert list(r.dedupe.columns) == ["_key", "_event_time"] and r.limit == 3 and r.filters[0].column == "price"
    feed.query(as_of_lag="1h").at((5,)).fetch()   # pinning works on the server
    assert list(fake.last_read.at_position.next_offsets) == [5]


def test_as_of_join_uses_the_servers_lookup(client, fake):
    fake.capabilities = ["lookup"]
    client.create_feed("t")
    left = pd.DataFrame({
        "at": pd.to_datetime(["2026-10-16T09:00Z", "2026-10-16T10:00Z", "2026-10-16T11:00Z"]),
        "station": ["dub", "cork", "dub"],
    })
    out = iso.as_of_join(left, client.feed("t").query(where={"kind": "x"}), at="at", key="station",
                         basis="received", columns=["value"])
    lookup = fake.last_lookup
    probes = pa.ipc.open_stream(lookup.probe_batch.ipc).read_all()
    assert probes.column("_key").to_pylist() == ["dub", "cork", "dub"]
    assert probes.column("_at").to_pylist()[0] == T("2026-10-16T09:00", tz="UTC")
    assert lookup.as_of_basis == pb.AS_OF_BASIS_RECEIVED and lookup.filters[0].column == "kind"
    assert list(lookup.columns) == ["_event_time", "_published_time", "_receive_time", "value"]
    # Rows back in the left's order, whatever order they came in; no answer means missing.
    assert out["value"].tolist()[:2] == [0.0, 1.0] and pd.isna(out["value"].iloc[2])
    assert out["_event_time"].iloc[1] == T("2026-10-16T10:00", tz="UTC")


def test_as_of_join_runs_locally_when_lookup_cannot_express_the_query(client, fake, versions):
    fake.capabilities = ["lookup"]
    client.create_feed("t")
    versions(OBSERVATIONS)
    left = pd.DataFrame({"at": pd.to_datetime(["2026-10-16T10:30Z"]), "station": ["dub"]})
    out = iso.as_of_join(left, client.feed("t").query(since="30d"), at="at", key="station", columns=["value"])
    assert out["value"].tolist() == [11.0] and not hasattr(fake, "last_lookup")


def test_read_estimates_and_large_read_warnings(client, fake):
    fake.capabilities = ["read.estimate"]
    fake.estimate = (700_000, 237_000_000)
    client.create_feed("t")
    feed = client.feed("t")
    assert feed.query().estimate() == {"rows": 700_000, "bytes": 237_000_000}
    assert fake.last_read.estimate_only
    with pytest.warns(iso.LargeReadWarning, match="237 MB"):
        result = feed.query().fetch()
    assert result.estimate["rows"] == 700_000
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        feed.query(columns=["price"]).fetch()   # columns chosen: no warning


def test_feeds_say_how_fresh_they_are(client, fake):
    fake.capabilities = ["feeds.freshness"]
    fake.add_public_feed()
    stats = fake.feeds[("isodrome/public", "forecasts")].stats
    stats.last_receive_time_ns = _ns("2026-10-16T09:00")
    stats.events_flushed = 42
    listed = client.feeds(public=True).to_df()
    row = listed[listed["feed"] == "isodrome/public/forecasts"].iloc[0]
    assert row["events"] == 42 and row["last received"] == T("2026-10-16T09:00", tz="UTC")
