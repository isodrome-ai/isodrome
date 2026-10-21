"""A stateful transformer against a real server with a transformer worker (see docker-compose.yml
here): deployed with the SDK, backfilled, then live; and `iso transformer test`'s fixtures.
Skipped unless ISODROME_E2E_ENDPOINT is set, or when the server has no worker for transformers."""

import os
import textwrap
import time
import uuid

import pytest
from click.testing import CliRunner

import isodrome as iso
from isodrome.cli import cli
from isodrome.v1 import isodrome_pb2 as pb

ENDPOINT = os.environ.get("ISODROME_E2E_ENDPOINT")
KEY = os.environ.get("ISODROME_E2E_API_KEY", "iso_devlocal_DEVONLYlocalAdminKeyNeverUseInProduction0")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not ENDPOINT, reason="set ISODROME_E2E_ENDPOINT to run against a server"),
]

PROJECT = '''
import isodrome as iso


@iso.transformer(
    name="{name}",
    triggers={{"counts": "{trigger}"}},
    output=iso.output("{output}", key="k", time="at"),
    state=True,
)
def running_total(event, ctx):
    totals = ctx.state.setdefault("totals", {{}})
    totals[event["k"]] = totals.get(event["k"], 0) + event["n"]
    return {{"k": event["k"], "at": event["at"], "total": totals[event["k"]]}}
'''

FIXTURE = (
    '{"event": {"k": "a", "n": 2, "at": "2026-01-01T00:00:00Z"}, "expect": [{"k": "a", "at": "2026-01-01T00:00:00Z", "total": 2}]}\n'
    '{"event": {"k": "a", "n": 3, "at": "2026-01-01T00:01:00Z"}, "expect": [{"k": "a", "at": "2026-01-01T00:01:00Z", "total": 5}]}\n'
)


def eventually(check, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return check()
        except AssertionError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


@pytest.fixture
def client():
    with iso.connect(endpoint=ENDPOINT, api_key=KEY) as c:
        yield c


@pytest.fixture
def setup(client, tmp_path):
    suffix = uuid.uuid4().hex[:6]
    names = {"name": f"total-{suffix}", "trigger": f"counts_{suffix}", "output": f"totals_{suffix}"}
    feed = client.create_feed(names["trigger"], key="k", time_field="at")
    # History before the deploy: the backfill must replay it all, in order, into the state.
    feed.push([{"k": "a" if i % 2 else "b", "n": 1, "at": f"2026-01-01T00:{i:02d}:00Z"} for i in range(40)])
    project = tmp_path / "project"
    (project / "isodrome_tests").mkdir(parents=True)
    (project / "main.py").write_text(textwrap.dedent(PROJECT.format(**names)))
    (project / "requirements.txt").write_text("")
    (project / "isodrome_tests" / "totals.jsonl").write_text(FIXTURE)
    return names, feed, project


def _worker_or_skip(client):
    try:
        listed = client.transformers()
    except iso.IsodromeError as e:
        pytest.skip(f"no transformers on this server: {e}")
    return listed


def test_a_stateful_transformer_backfills_then_runs_live(client, setup):
    _worker_or_skip(client)
    names, feed, project = setup
    eventually(lambda: _count(feed, 40))
    build = client.deploy_transformer(project, name=names["name"], progress=True)
    assert build.status == "ready"
    info = client.transformer(names["name"])
    assert info.stateful and info.backfill_remaining == 0

    out = client.feed(names["output"])
    final = eventually(lambda: _totals(out, {"a": 20, "b": 20}))
    assert len(final) == 40   # one output per replayed trigger event

    feed.push({"k": "a", "n": 5, "at": "2026-01-02T00:00:00Z"})   # live: the state carries on
    eventually(lambda: _totals(out, {"a": 25, "b": 20}))
    assert client.transformer(names["name"]).refresh().stats.code_state_bytes > 0

    client._transport.call("DeleteTransformer", pb.DeleteTransformerRequest(
        transformer=pb.TransformerRef(name=names["name"])))


def test_iso_transformer_test_prints_the_fixtures(client, setup):
    _worker_or_skip(client)
    names, _, project = setup
    result = CliRunner().invoke(cli, ["--endpoint", ENDPOINT, "--api-key", KEY, "transformer", "test",
                                      str(project), "--name", names["name"]])
    assert result.exit_code == 0, result.output
    assert "verified (not deployed)" in result.stdout
    assert "totals.jsonl: 2 case(s), ok" in result.stdout


def _count(feed, n):
    assert feed.query().count() == n


def _totals(out, expected):
    df = out.query(columns=["_key", "_event_time", "total"]).to_df()
    last = df.sort_values("_event_time").groupby("_key")["total"].last().to_dict()
    assert last == expected, last
    return df
