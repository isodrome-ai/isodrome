"""Transformers: the manifest contract, deploying and testing (CLI and SDK), and reads inside
Isodrome."""

import json
import os
import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from fakes import KEY

import isodrome as iso
from isodrome import deploy
from isodrome.cli import cli
from isodrome.v1 import isodrome_pb2 as pb

HARNESS = Path(os.environ.get(
    "ISODROME_HARNESS",
    Path(__file__).resolve().parents[2] / "isodrome-server" / "crates" / "connector-worker" / "src" / "harness.py",
))


# ---------- The manifest ----------


def test_state_goes_into_the_manifest():
    @iso.transformer(name="elo", triggers={"results": "isodrome/public/nfl_results"},
                     output=iso.output("nfl_elo", key="team", time="rated_at"), as_of="published", state=True)
    def elo(event, ctx):
        return None

    m = elo.__isodrome_transformer__
    assert m["state"] is True and m["manifest_version"] == 1 and m["name"] == "elo"
    assert m["entrypoint"] == f"{__name__}:test_state_goes_into_the_manifest.<locals>.elo"
    assert m["output"] == {"feed": "nfl_elo", "key": "team", "time": "rated_at", "publication_time": None,
                           "description": ""}
    assert json.loads(json.dumps(m)) == m        # JSON as it is
    assert elo(None, None) is None               # the function itself is unchanged


def test_names_default_from_the_function():
    @iso.transformer(triggers={"t": "x"})
    def season_odds(event, ctx):
        pass

    assert season_odds.__isodrome_transformer__["name"] == "season-odds"
    assert "state" not in season_odds.__isodrome_transformer__


def test_mistakes_are_caught_at_declaration():
    with pytest.raises(ValueError, match="cannot be used with state=True"):
        iso.transformer(triggers={"t": "x"}, state=True, on_restart="latest")
    with pytest.raises(ValueError, match="as_of"):
        iso.transformer(triggers={"t": "x"}, as_of="whenever")
    with pytest.raises(ValueError, match="at least one trigger"):
        iso.transformer(output="o")
    with pytest.raises(TypeError):
        iso.transformer(triggers={"t": "x"}, state="yes")
    with pytest.raises(ValueError, match="400 days"):
        iso.feed("isodrome/public/nfl_schedule", horizon="401d")
    assert iso.feed("isodrome/public/nfl_schedule", horizon="400d")["horizon"] == "400d"
    with pytest.raises(ValueError):
        iso.feed("x", window="ten minutes")


def test_a_feed_spec_is_a_plain_dict_and_never_connects_for_dunders(monkeypatch):
    spec = iso.feed("isodrome/public/met_eireann_observations", window="24h")
    assert spec == {"feed": "isodrome/public/met_eireann_observations", "window": "24h", "horizon": None}
    assert isinstance(spec, dict) and json.dumps(spec)
    monkeypatch.setattr(iso, "_client", lambda: pytest.fail("connected"))
    assert getattr(spec, "__isodrome_transformer__", None) is None   # what the harness probes
    assert not hasattr(spec, "_private")
    assert repr(spec) == "iso.feed('isodrome/public/met_eireann_observations', window='24h')"


def test_a_feed_spec_is_the_feed_in_a_notebook(fake, monkeypatch):
    client = iso.connect(endpoint=fake.endpoint, api_key=KEY)
    client.create_feed("prices")
    monkeypatch.setattr(iso, "_client", lambda: client)
    spec = iso.feed("prices")
    spec.push({"price": 1.0})
    assert spec.query().to_df()["price"].tolist() == [1.0]
    assert iso.read("prices").to_df()["price"].tolist() == [1.0]
    assert iso.latest("prices").to_df()["price"].tolist() == [1.0]


@pytest.mark.skipif(not HARNESS.exists(), reason="needs isodrome-server next to this repository (or ISODROME_HARNESS)")
def test_the_servers_harness_reads_our_manifests(tmp_path):
    """The harness that runs transformers in Isodrome imports this package (as a project that
    installs the SDK would) and collects exactly the manifest we declare."""
    (tmp_path / "main.py").write_text('''
import isodrome as iso

SCHEDULE = iso.feed("isodrome/public/nfl_schedule", horizon="400d")   # module-level: probed by the harness

@iso.transformer(
    name="nfl-season",
    triggers={"ratings": "nfl_elo"},
    dependencies={"schedule": SCHEDULE},
    output=iso.output("nfl_season_odds", key="team", time="as_of", publication_time="as_of"),
    as_of="published",
    state=True,
)
def season(event, ctx):
    ctx.state["n"] = ctx.state.get("n", 0) + 1
    return {"team": "KC", "n": ctx.state["n"]}
''')
    src = Path(iso.__file__).resolve().parents[1]
    env = dict(os.environ, ISODROME_CODE_DIR=str(tmp_path), PYTHONPATH=f"{tmp_path}{os.pathsep}{src}")
    out = subprocess.run([sys.executable, str(HARNESS), "--manifest"], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=60)
    message = json.loads(out.stdout.strip().splitlines()[-1])
    assert message["t"] == "manifest", out.stdout + out.stderr
    [m] = message["transformers"]
    assert m["name"] == "nfl-season" and m["state"] is True and m["entrypoint"] == "main:season"
    assert m["dependencies"]["schedule"] == {"feed": "isodrome/public/nfl_schedule", "window": None, "horizon": "400d"}


def test_inside_isodrome_reads_go_through_the_runtime(monkeypatch):
    calls = []
    runtime = types.ModuleType("isodrome_runtime")
    runtime.get = lambda feed, key=None: calls.append(("get", feed, key)) or {"team": "KC"}
    runtime.read = lambda feed, start=None, end=None, limit=1000: calls.append(("read", feed, start, end, limit)) or []
    monkeypatch.setitem(sys.modules, "isodrome_runtime", runtime)
    assert iso.get(iso.feed("isodrome/public/nfl_elo"), "KC") == {"team": "KC"}
    assert iso.read("nfl_elo", start=1, end=2) == []
    assert calls == [("get", "isodrome/public/nfl_elo", "KC"), ("read", "nfl_elo", 1, 2, 1000)]
    with pytest.raises(TypeError, match="inside a transformer"):
        iso.read("nfl_elo", as_of="2026-01-01")
    with pytest.raises(RuntimeError, match="inside a transformer"):
        iso.feed("nfl_elo").query()


# ---------- Packing and requests ----------


def test_pack_leaves_out_what_does_not_belong(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    (tmp_path / "isodrome_tests" / "nfl-elo").mkdir(parents=True)
    (tmp_path / "isodrome_tests" / "nfl-elo" / "cases.jsonl").write_text("{}\n")
    for junk in (".venv/lib.py", "__pycache__/main.cpython-312.pyc", ".git/HEAD", "notes.pyc", ".env"):
        (tmp_path / junk).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / junk).write_text("junk")
    bundle = deploy.pack(tmp_path)
    assert sorted(zipfile.ZipFile(__import__("io").BytesIO(bundle)).namelist()) == [
        "isodrome_tests/nfl-elo/cases.jsonl", "main.py"]
    assert deploy.pack(tmp_path) == bundle   # same files, same bundle


def test_overrides_become_the_request():
    r = deploy.request(deploy.Overrides(
        name="nfl-season", state=True, basis="published", triggers={"ratings": "nfl_elo"},
        dependencies={"schedule": ("isodrome/public/nfl_schedule", "400d")}, windows={"ratings": "10m"},
        output="odds", key="team"), bundle_sha256="abc", validate_only=True)
    assert r.stateful and r.validate_only and r.as_of_basis == pb.AS_OF_BASIS_PUBLISHED
    assert r.dependencies[0].horizon_ns == 400 * 86400 * 10**9
    assert r.triggers[0].window.duration_ns == 600 * 10**9
    assert (r.output.feed, r.output.key_field) == ("odds", "team")


# ---------- The CLI ----------


@pytest.fixture
def no_waiting(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(deploy, "time", types.SimpleNamespace(
        monotonic=lambda: clock["t"], sleep=lambda s: clock.__setitem__("t", clock["t"] + s)))
    # The module, not the click group of the same name that isodrome.cli exports.
    monkeypatch.setattr(sys.modules["isodrome.cli.transformer"], "time", deploy.time)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "main.py").write_text("import isodrome as iso\n")
    return tmp_path


def test_deploy_shows_phases_then_waits_for_the_backfill(iso, fake, project, no_waiting):
    result = iso("transformer", "deploy", str(project), "--name", "nfl-elo", "--state")
    assert result.exit_code == 0, result.output
    request = fake.deploys[-1]
    assert request.stateful and not request.validate_only and request.bundle_sha256 in fake.bundles
    err = result.stderr
    assert "building" in err and "verifying" in err and err.index("building") < err.index("verifying")
    assert "backfill: 2,000 trigger events to replay" in err
    assert "nfl-elo v3 is live" in result.stdout
    assert "fixtures   FAILED" not in result.stdout


def test_test_prints_the_fixtures_and_fails_on_them(iso, fake, project, no_waiting):
    fake.build_outcome = "verification_failed"
    fake.report["stages"][2]["ok"] = False
    result = iso("transformer", "test", str(project))
    assert result.exit_code == 1 and fake.deploys[-1].validate_only
    out = result.stdout
    assert "fixtures   FAILED   2 file(s), 5 case(s), 1 failed" in out
    assert "ratings.jsonl: 3 case(s), ok" in out
    assert "nfl-lines/lines.jsonl: 2 case(s), 1 failed" in out
    assert 'line 2: expected [{"spread": 3.5}]' in out and 'got [{"spread": 3.0}]' in out
    assert fake.transformer_polls == 0   # a test deploys nothing, so there is no backfill to wait for


def test_a_long_verification_says_it_is_still_going(iso, fake, project, no_waiting):
    fake.build_steps = ["building"] + ["verifying"] * 80 + ["ready"]   # 80 s of verification
    result = iso("transformer", "test", str(project))
    assert result.exit_code == 0, result.output
    assert "still verifying (verifying a stateful transformer replays its whole history)" in result.stderr


def test_show_and_list_describe_state_and_backfill(iso, fake):
    shown = iso("transformer", "show", "nfl-elo").stdout
    assert "stateful:        yes" in shown and "backfill:        2,000 trigger events" in shown
    assert "ctx.state:       4.2 KB saved" in shown
    listed = iso("transformer", "list").stdout
    assert "stateful" in listed and "backfill 1,500 to go" in listed


def test_published_basis_is_described_as_publication_order():
    t = pb.Transformer(name="x", as_of_basis=pb.AS_OF_BASIS_PUBLISHED)
    assert "as published when the trigger was" in "\n".join(deploy.describe_transformer(t))


def test_run_a_backtest(iso, fake, no_waiting):
    result = iso("transformer", "run", "nfl-season", "--from", "2025-09-01", "--to", "2026-03-01", "--into", "odds_2025")
    assert result.exit_code == 0, result.output
    run = fake.runs[-1]
    assert run.into == "odds_2025" and run.start_ns == 1756684800 * 10**9
    assert "status:          done (100.0%)" in result.stdout


def test_the_sdk_deploys_and_waits(fake, project, no_waiting):
    client = iso.connect(endpoint=fake.endpoint, api_key=KEY)
    build = client.deploy_transformer(project, name="nfl-elo", state=True, progress=False)
    assert build.status == "ready" and fake.deploys[-1].stateful and fake.transformer_polls >= 3
    info = client.transformer("nfl-elo")
    assert info.stateful and info.output == "default/nfl_elo" and "stateful:        yes" in repr(info)
    assert client.run_transformer("nfl-elo", "2025-09-01", "2026-03-01", progress=False).status == "done"


def test_versions_and_tags_in_feed_references(iso, fake):
    iso("feed", "create", "prices")
    iso("feed", "query", "prices@2")
    assert (fake.last_read.feed.name, fake.last_read.feed.version) == ("prices", 2)
    iso("feed", "query", "default/prices:prod")
    assert (fake.last_read.feed.namespace, fake.last_read.feed.tag) == ("default", "prod")
    assert iso("feed", "query", "prices@x").exit_code == 2


def test_a_build_outlives_the_server_restarting(iso, fake, project, no_waiting):
    fake.unavailable_polls = 5
    result = iso("transformer", "test", str(project))
    assert result.exit_code == 0, result.output
    assert result.stderr.count("server unavailable, retrying") == 1
    assert "verified (not deployed)" in result.stdout


def test_query_payloads_one_per_line(iso, fake):
    iso("feed", "create", "t")
    iso("feed", "push", "t", "--data", '{"price": 1}', "--data", '{"price": 2}')
    result = iso("feed", "query", "t", "--payloads")
    assert result.exit_code == 0, result.output
    assert [json.loads(line) for line in result.stdout.splitlines()] == [{"price": 1}, {"price": 2}]
    assert fake.last_read.include_payload and list(fake.last_read.columns) == ["_payload"]
