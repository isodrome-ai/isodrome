"""`iso` end to end against a real server (see docker-compose.yml here).

Skipped unless ISODROME_E2E_ENDPOINT is set. ISODROME_E2E_API_KEY defaults to the local stack's
DEV-ONLY admin key.
"""

import json
import os
import time
import uuid

import pytest
from click.testing import CliRunner

from isodrome.cli import cli
from isodrome.config import Config

ENDPOINT = os.environ.get("ISODROME_E2E_ENDPOINT")
KEY = os.environ.get("ISODROME_E2E_API_KEY", "iso_devlocal_DEVONLYlocalAdminKeyNeverUseInProduction0")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not ENDPOINT, reason="set ISODROME_E2E_ENDPOINT to run against a server"),
]


def iso(*args, input=None):
    result = CliRunner().invoke(cli, list(args), input=input, catch_exceptions=False)
    return result


def ok(*args, input=None):
    result = iso(*args, input=input)
    assert result.exit_code == 0, f"iso {' '.join(args)}:\n{result.output}"
    return result


def eventually(check, timeout=30):
    """Retries `check` until it stops raising AssertionError."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return check()
        except AssertionError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def logged_in():
    ok("login", "--endpoint", ENDPOINT, "--api-key", KEY)
    ns = f"e2e{uuid.uuid4().hex[:8]}"
    ok("namespace", "create", ns)
    ok("namespace", "use", ns)
    return ns


def test_server_and_version():
    assert "api:          v1" in ok("--endpoint", ENDPOINT, "server").output
    assert "server" in ok("--endpoint", ENDPOINT, "--version").output


def test_feed_end_to_end(logged_in, tmp_path):
    ns = logged_in
    assert f"namespace in use:  {ns}" in ok("whoami").output
    ok("feed", "create", "trades", "--key", "symbol", "--time-unit", "ns")
    assert f"{ns}/trades" in ok("feed", "list").output

    t0 = time.time_ns() - 60 * 10**9
    events = tmp_path / "trades.jsonl"
    events.write_text("\n".join(
        json.dumps({"symbol": s, "price": p, "event_time": t0 + i * 10**9})
        for i, (s, p) in enumerate([("AAPL", 100.0), ("MSFT", 300.0), ("AAPL", 101.5), ("MSFT", 299.0)])
    ) + "\n")
    assert ok("feed", "push", "trades", "--file", str(events)).output.strip() == "4 accepted"
    # The same file again: recognised, not written twice.
    assert ok("feed", "push", "trades", "--file", str(events)).output.strip() == "4 accepted (4 already sent)"

    # Rejections are loud, and the exit status says so.
    bad = iso("feed", "push", "trades", "--data", '{"symbol": "AAPL", "price": 1}')
    assert bad.exit_code == 1
    assert "REJECTED --data: missing_event_time" in bad.stderr
    assert "missing_event_time" in ok("feed", "errors", "trades").output

    def query():
        rows = [json.loads(l) for l in ok("feed", "query", "trades", "--since", "1h", "-o", "json").stdout.splitlines()]
        assert sorted(r["price"] for r in rows) == [100.0, 101.5, 299.0, 300.0]
        return rows

    rows = eventually(query)
    assert {r["_key"] for r in rows} == {"AAPL", "MSFT"}
    assert ok("feed", "query", "trades", "--count", "--where", "price>200").stdout.strip() == "2"
    csv = ok("feed", "query", "trades", "-o", "csv", "-c", "price", "-w", "symbol = AAPL").stdout.splitlines()
    assert csv[0] == "price" and sorted(csv[1:]) == ["100.0", "101.5"]

    latest = [json.loads(l) for l in ok("feed", "latest", "trades", "-o", "json").stdout.splitlines()]
    assert {r["_key"]: r["price"] for r in latest} == {"AAPL": 101.5, "MSFT": 299.0}

    tail = ok("feed", "tail", "trades", "--last", "2", "--no-follow", "-o", "json").stdout.splitlines()
    assert [json.loads(l)["_payload"]["price"] for l in tail] == [101.5, 299.0]

    # By default a feed times events on arrival, so events need no timestamp.
    ok("feed", "create", "weather")
    ok("feed", "push", "weather", "--data", '{"temperature": 18.5, "city": "Dublin"}')

    def counted():
        assert ok("feed", "query", "weather", "--count").stdout.strip() == "1"

    eventually(counted)
    assert "iso feed push trades" in ok("feed", "describe", "trades").output
    ok("feed", "delete", "weather", "--yes")
    assert "weather" in ok("feed", "list", "--deleted").output
    ok("feed", "undelete", "weather")
    ok("feed", "delete", "weather", "--yes")
    ok("feed", "delete", "trades", "--yes")
    ok("namespace", "use", "--default")
    ok("namespace", "delete", ns)


def test_logout_revokes_a_signed_in_key():
    ok("login", "--endpoint", ENDPOINT, "--api-key", KEY)
    # The local stack's bootstrap key belongs to no one, so it makes organization keys.
    created = ok("key", "create", "--role", "reader", "--name", "e2e-logout", "--organization").stdout
    reader_key = next(l.split()[-1] for l in created.splitlines() if l.startswith("api key:"))
    ok("--profile", "reader", "login", "--endpoint", ENDPOINT, "--api-key", reader_key)
    ok("--profile", "reader", "logout")
    assert Config.load().profiles["reader"].api_key is None
    refused = iso("--endpoint", ENDPOINT, "--api-key", reader_key, "whoami")
    assert refused.exit_code == 1 and "UNAUTHENTICATED" in refused.output


OTHER_KEY = os.environ.get("ISODROME_E2E_OTHER_KEY")


@pytest.mark.skipif(not OTHER_KEY, reason="set ISODROME_E2E_OTHER_KEY: an admin key of a second organization")
def test_public_feeds_across_organizations():
    """`local` (allowed to publish) makes a public namespace; another organization finds and
    reads its feed, and cannot change it."""
    ns = f"pub{uuid.uuid4().hex[:8]}"
    ok("login", "--endpoint", ENDPOINT, "--api-key", KEY)
    ok("namespace", "create", ns, "--public")
    ok("feed", "create", f"{ns}/rates", "--attribution", "Test Bank", "--licence", "CC BY 4.0")
    ok("feed", "push", f"{ns}/rates", "--data", '{"ccy": "EUR", "rate": 1.08}')
    ok("feed", "create", "private_one")  # in default: not public

    other = ("--endpoint", ENDPOINT, "--api-key", OTHER_KEY)
    ref = f"local/{ns}/rates"

    def listed():
        rows = {r["feed"]: r for r in map(json.loads, ok(*other, "feed", "list", "-o", "json").stdout.splitlines())}
        assert rows[ref]["access"] == "public, read-only"
        return rows

    rows = eventually(listed)
    assert not any("private_one" in f for f in rows)
    assert ref not in ok(*other, "feed", "list", "--mine", "-o", "json").stdout
    assert f"local/{ns}" in ok(*other, "namespace", "list").stdout

    def read():
        result = ok(*other, "feed", "query", ref, "-o", "json")
        assert [json.loads(l)["rate"] for l in result.stdout.splitlines()] == [1.08]
        return result

    assert "Data: Test Bank" in eventually(read).stderr
    shown = ok(*other, "feed", "show", ref).output
    assert "public, read-only (local)" in shown and "attribution: Test Bank" in shown

    refused = iso(*other, "feed", "push", ref, "--data", "{}")
    assert refused.exit_code == 1 and "can be read, but not changed" in refused.output

    ok("feed", "delete", f"{ns}/rates", "--yes")
    ok("feed", "delete", "private_one", "--yes")
    ok("namespace", "update", ns, "--private")
    assert f"local/{ns}" not in ok(*other, "namespace", "list").stdout
