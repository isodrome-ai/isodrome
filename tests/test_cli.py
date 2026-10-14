"""The `iso` commands against an in-process fake server."""

import json

from click.testing import CliRunner

from fakes import KEY, FakeSignIn

from isodrome import login as device_flow
from isodrome.cli import cli
from isodrome.config import Config


def test_not_logged_in(iso):
    result = iso("whoami", key=False)
    assert result.exit_code == 1
    assert "not logged in" in result.output and "iso login" in result.output


def test_bad_key_is_one_line_with_a_hint(fake):
    result = CliRunner().invoke(cli, ["--endpoint", fake.endpoint, "--api-key", "iso_x_wrong", "whoami"])
    assert result.exit_code == 1
    assert "UNAUTHENTICATED" in result.output and "iso login" in result.output
    assert "Traceback" not in result.output


def test_whoami(iso):
    result = iso("whoami")
    assert result.exit_code == 0, result.output
    assert "signed in as:      a@acme.io" in result.output and "admin" in result.output
    assert "credential:        session, expires 2100-01-01T00:00:00Z" in result.output


def test_login_on_a_server_without_sign_in(fake):
    http, base = FakeSignIn(unavailable=True).serve()
    try:
        result = CliRunner().invoke(cli, ["--endpoint", fake.endpoint, "login", "--http", base])
    finally:
        http.shutdown()
    assert result.exit_code == 1
    assert "not configured on this server" in result.output and "iso login --api-key" in result.output


def test_keys_are_personal_unless_asked(iso, fake):
    created = iso("key", "create", "--role", "writer", "--name", "bot")
    assert created.exit_code == 0, created.output
    assert "api key: iso_k0_" in created.stdout
    assert iso("key", "create", "--role", "reader", "--organization").exit_code == 0
    assert [k.owner for k in fake.keys] == ["a@acme.io", ""]
    listed = iso("key", "list").stdout.splitlines()
    assert listed[0].startswith("  k0 ") and "a@acme.io" in listed[0] and "api key" in listed[0] and "bot" in listed[0]
    assert "(organization)" in listed[1]


def test_login_with_key_saves_profile(iso, fake):
    result = iso("--profile", "local", "login", "--api-key", KEY, key=False)
    assert result.exit_code == 0, result.output
    assert "Logged in as a@acme.io to acme" in result.output and "session, expires 2100" in result.output
    config = Config.load()
    assert config.profiles["local"].api_key == KEY
    assert config.profiles["local"].endpoint == fake.endpoint


def test_login_device_flow(fake, monkeypatch):
    sign_in = FakeSignIn(pending_polls=2, slow_down_once=True)
    http, base = sign_in.serve()
    monkeypatch.setattr(device_flow.time, "sleep", lambda s: None)
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    try:
        result = CliRunner().invoke(cli, ["--endpoint", fake.endpoint, "login", "--http", base])
    finally:
        http.shutdown()
    assert result.exit_code == 0, result.output
    assert "WDJB-MJHT" in result.output and opened == ["http://x/device?code=WDJB-MJHT"]
    # slow_down, authorization_pending, approved
    assert sign_in.polls == 3 and sign_in.client_names[0].startswith("iso on ")
    assert Config.load().profile().api_key == KEY


def test_login_declined(fake, monkeypatch):
    http, base = FakeSignIn(pending_polls=0, final_error="access_denied").serve()
    monkeypatch.setattr(device_flow.time, "sleep", lambda s: None)
    try:
        result = CliRunner().invoke(cli, ["--endpoint", fake.endpoint, "login", "--http", base, "--no-browser"])
    finally:
        http.shutdown()
    assert result.exit_code == 1 and "declined in the browser" in result.output
    assert Config.load().profile().api_key is None


def test_logout_revokes_then_forgets(iso, fake):
    iso("login", "--api-key", KEY, key=False)
    result = CliRunner().invoke(cli, ["logout"])
    assert result.exit_code == 0, result.output
    assert fake.revoked == {"testkey"}
    assert Config.load().profile().api_key is None
    # Already revoked: the server refuses the key, and logging out again is harmless.
    assert CliRunner().invoke(cli, ["logout"]).output.startswith("Not logged in")


def test_logout_keeps_key_when_server_unreachable(iso, fake):
    iso("login", "--api-key", KEY, key=False)
    config = Config.load()
    config.profile().endpoint = "http://127.0.0.1:1"
    config.save()
    result = CliRunner().invoke(cli, ["logout"])
    assert result.exit_code == 1 and "still saved" in result.output
    assert Config.load().profile().api_key == KEY
    assert CliRunner().invoke(cli, ["logout", "--local-only"]).exit_code == 0
    assert Config.load().profile().api_key is None


def test_namespace_use(iso, fake):
    assert iso("namespace", "create", "research").exit_code == 0
    assert iso("namespace", "use", "nope").exit_code == 1
    assert iso("namespace", "use", "research").exit_code == 0
    assert Config.load().profile().namespace == "research"
    assert "* research" in iso("namespace", "list").output
    iso("feed", "create", "quotes", "--arrival-time")
    assert ("research", "quotes") in fake.feeds
    assert iso("namespace", "use", "--default").exit_code == 0
    assert Config.load().profile().namespace is None


def test_feed_lifecycle(iso, fake, tmp_path):
    result = iso("feed", "create", "trades", "--key", "symbol")
    assert result.exit_code == 0 and "Created feed default/trades" in result.output
    assert "Events need the field `event_time`" in result.output
    assert "default/trades" in iso("feed", "list").output
    shown = iso("feed", "describe", "trades").output
    assert "key field:   symbol" in shown and "iso feed push trades --data" in shown

    events = tmp_path / "events.jsonl"
    events.write_text('{"price": 1}\n{"price": 2}\n{"nope": 3}\nnot json\n')
    result = iso("feed", "push", "trades", "--file", str(events), "--data", '{"price": 3}', "--batch-size", "2")
    assert result.exit_code == 1
    assert f"REJECTED {events}:3: missing_key" in result.stderr
    assert f"REJECTED {events}:4: invalid_json" in result.stderr
    assert "3 accepted, 2 REJECTED" in result.stderr
    assert fake.send_requests == 3

    result = iso("feed", "push", "trades", input='[{"price": 4}]')
    assert result.exit_code == 0 and result.output.strip() == "1 accepted"

    result = iso("feed", "query", "trades", "--since", "1h", "--format", "json", "--limit", "3")
    assert result.exit_code == 0, result.output
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    # --data events are sent before --file ones.
    assert [r["price"] for r in rows] == [3.0, 1.0, 2.0]
    assert "first 3 events" in result.stderr
    assert fake.last_read.limit == 4 and fake.last_read.HasField("start_event_time_ns")

    assert iso("feed", "query", "trades", "--count").stdout.strip() == "4"
    csv = iso("feed", "query", "trades", "-o", "csv", "-c", "price", "--where", "price>1").stdout.splitlines()
    assert csv[0] == "price" and len(csv) == 5
    assert fake.last_read.filters[0].column == "price"

    tail = iso("feed", "tail", "trades", "--last", "2", "--no-follow", "-o", "json")
    assert tail.exit_code == 0, tail.output
    tail = tail.stdout.splitlines()
    assert [json.loads(line)["_payload"]["price"] for line in tail] == [2, 4]

    latest = iso("feed", "latest", "trades")
    assert latest.exit_code == 0 and "price" in latest.output


def test_feed_not_found(iso):
    result = iso("feed", "show", "missing")
    assert result.exit_code == 1 and "NOT_FOUND" in result.output


def test_bad_arguments(iso):
    iso("feed", "create", "t", "--arrival-time")
    assert iso("feed", "query", "t", "--since", "soon").exit_code == 2
    assert iso("feed", "query", "t", "--where", "bogus").exit_code == 2
    assert iso("feed", "create", "u", "--arrival-time", "--time-field", "ts").exit_code == 2


def test_version_shows_server(iso):
    result = iso("--version")
    assert result.exit_code == 0
    assert "API v1" in result.output and "server 9.9.9" in result.output


def test_profiles(iso):
    iso("--profile", "local", "login", "--api-key", KEY, key=False)
    runner = CliRunner()
    assert runner.invoke(cli, ["profile", "use", "local"]).exit_code == 0
    listed = runner.invoke(cli, ["profile", "list"]).output
    assert "* local" in listed and "logged in" in listed
    # The current profile is used without --endpoint or --api-key.
    assert "a@acme.io" in runner.invoke(cli, ["whoami"]).output


def test_login_against_a_server_without_sign_in(fake):
    # e.g. a proxy that sends /auth/* to gRPC: HTTP 200 with no JSON.
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.send_response(200)
            self.send_header("content-type", "application/grpc")
            self.send_header("content-length", "0")
            self.end_headers()

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    try:
        result = CliRunner().invoke(
            cli, ["--endpoint", fake.endpoint, "login", "--http", f"http://127.0.0.1:{http.server_address[1]}"]
        )
    finally:
        http.shutdown()
    assert result.exit_code == 1 and "not set up for sign-in" in result.output


def test_pushing_a_file_twice_is_idempotent(iso, fake, tmp_path):
    iso("feed", "create", "t", "--arrival-time")
    events = tmp_path / "e.jsonl"
    events.write_text('{"price": 1}\n{"price": 1}\n')
    assert iso("feed", "push", "t", "-f", str(events)).output.strip() == "2 accepted"
    assert iso("feed", "push", "t", "-f", str(events)).output.strip() == "2 accepted (2 already sent)"
    events.write_text('{"price": 1}\n{"price": 2}\n')  # line 2 edited: a new event
    assert iso("feed", "push", "t", "-f", str(events)).output.strip() == "2 accepted (1 already sent)"
    assert len(fake.events[("default", "t")]) == 3
