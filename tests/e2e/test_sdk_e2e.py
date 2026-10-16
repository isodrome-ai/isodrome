"""The Python SDK against a real server (see docker-compose.yml here). Skipped unless
ISODROME_E2E_ENDPOINT is set."""

import os
import time
import uuid

import pandas as pd
import pytest

import isodrome as iso

ENDPOINT = os.environ.get("ISODROME_E2E_ENDPOINT")
KEY = os.environ.get("ISODROME_E2E_API_KEY", "iso_devlocal_DEVONLYlocalAdminKeyNeverUseInProduction0")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not ENDPOINT, reason="set ISODROME_E2E_ENDPOINT to run against a server"),
]


def eventually(check, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return check()
        except AssertionError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def client():
    with iso.connect(endpoint=ENDPOINT, api_key=KEY) as c:
        yield c


def ts(text):
    return pd.Timestamp(text, tz="UTC")


def test_forecast_versions_end_to_end(client):
    name = f"sdk_{uuid.uuid4().hex[:8]}"
    feed = client.create_feed(name, key="location", time_field="valid_time", publication_time_field="published",
                              licence="test licence", attribution="Test Weather Service")
    # Three runs forecasting 12:00 and 13:00, published at 06:00, 09:00 and 11:30.
    runs = pd.DataFrame([
        {"location": "dub", "valid_time": ts(f"2026-10-16T{h}:00"), "published": ts(p), "temp": t}
        for p, temps in [("2026-10-16T06:00", (10.0, 11.0)), ("2026-10-16T09:00", (12.0, 13.0)),
                         ("2026-10-16T11:30", (14.0, 15.0))]
        for h, t in zip(("12", "13"), temps)
    ])
    assert feed.push(runs).accepted == 6
    assert feed.push(runs).duplicates == 6          # re-running the cell writes nothing twice
    with pytest.raises(iso.Rejected):
        feed.push({"location": "dub", "valid_time": "not a time", "temp": 1})

    everything = eventually(lambda: _rows(feed.versions(), 6))
    assert {c in everything for c in ("_event_time", "_published_time", "_receive_time")} == {True}

    # As published by 10:00, the latest version of each hour: the 09:00 run.
    as_of = feed.query(as_of="2026-10-16T10:00Z", basis="published", dedupe=["_key", "_event_time"],
                       order="publication", columns=["_event_time", "temp"]).to_df()
    assert as_of["temp"].tolist() == [12.0, 13.0]

    # Each hour as published 2 hours before it: 12:00 → the 09:00 run; 13:00 → the 09:00 run too
    # (11:30 is only 1.5 h before 13:00).
    lagged = feed.query(as_of_lag="2h", basis="published", dedupe=["_key", "_event_time"], order="publication",
                        columns=["_event_time", "temp"]).to_df()
    assert lagged["temp"].tolist() == [12.0, 13.0]

    # Exact repeat after more data arrives.
    first = feed.query(columns=["temp"]).fetch()
    feed.push({"location": "cork", "valid_time": ts("2026-10-16T12:00"), "published": ts("2026-10-16T11:00"),
               "temp": 9.0})
    eventually(lambda: _rows(feed.query(), 7))
    assert feed.query(columns=["temp"]).at(first.position).to_df().equals(first.to_df())

    # Latest per key, with the attribution carried along.
    latest = feed.latest(keys="dub", columns=["temp"])
    assert latest.to_df()["temp"].tolist() == [15.0] and latest.attribution == "Test Weather Service"

    # History then stop.
    tailed = pd.concat(r.to_df() for r in feed.tail(last=2, columns=["temp"], follow=False))
    assert len(tailed) == 2

    # Point in time: what was known at each moment.
    moments = pd.DataFrame({"at": [ts("2026-10-16T12:30"), ts("2026-10-16T13:30")], "where": ["dub", "dub"]})
    joined = iso.as_of_join(moments, feed, at="at", key="where", columns=["temp"])
    assert joined["temp"].tolist() == [14.0, 15.0]   # by 12:30, 12:00 had happened (run at 11:30)

    assert name in [f.name for f in client.feeds(mine=True)]
    with pytest.raises(iso.NotFound):
        client.feed(f"{name}_missing")


def _rows(query, n):
    df = query.to_df()
    assert len(df) == n
    return df


def test_server_and_local_point_in_time_agree(client):
    """as_of_lag and as_of_join give the same answers whether the server computes them
    (read.as_of_lag, lookup) or the SDK does from versions."""
    if not {"read.as_of_lag", "lookup"} <= client.capabilities:
        pytest.skip("this server has no read.as_of_lag/lookup to compare with")
    name = f"pit_{uuid.uuid4().hex[:8]}"
    feed = client.create_feed(name, key="location", time_field="valid_time", publication_time_field="published")
    rows = []
    for loc in ("dub", "cork"):
        for run in range(4):                                    # runs published 3 h apart
            published = ts("2026-10-16T00:00") + pd.Timedelta(hours=3 * run)
            for step in range(1, 7):                            # each forecasting 6 hours
                valid = ts("2026-10-16T00:00") + pd.Timedelta(hours=3 * run + step)
                rows.append({"location": loc, "valid_time": valid, "published": published,
                             "temp": float(run * 10 + step + (100 if loc == "cork" else 0))})
    feed.push(pd.DataFrame(rows))
    eventually(lambda: _rows(feed.versions(), len(rows)))

    lagged = dict(as_of_lag="4h", basis="published", dedupe=["_key", "_event_time"], order="publication",
                  columns=["_key", "_event_time", "temp"])
    probes = pd.DataFrame({"at": pd.date_range("2026-10-16T00:30Z", periods=12, freq="2h").tolist() * 2,
                           "location": ["dub"] * 12 + ["cork"] * 12})

    def compute():
        return (feed.query(**lagged).to_df().sort_values(["_key", "_event_time"]).reset_index(drop=True),
                iso.as_of_join(probes, feed, at="at", key="location", columns=["temp"]))

    on_server = compute()
    saved = client._capabilities
    client._capabilities = frozenset()
    try:
        locally = compute()
    finally:
        client._capabilities = saved
    pd.testing.assert_frame_equal(on_server[0], locally[0])
    pd.testing.assert_frame_equal(on_server[1].reset_index(drop=True), locally[1].reset_index(drop=True),
                                  check_dtype=False)
    assert len(on_server[0]) > 0 and on_server[1]["temp"].notna().sum() > 0
