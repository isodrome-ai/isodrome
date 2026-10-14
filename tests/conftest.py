import pytest
from click.testing import CliRunner

from fakes import KEY, FakeIsodrome, serve_grpc

from isodrome.cli import cli


@pytest.fixture(autouse=True)
def config_dir(tmp_path, monkeypatch):
    """Every test gets its own empty configuration, and no ambient credentials."""
    for var in ("ISODROME_PROFILE", "ISODROME_ENDPOINT", "ISODROME_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ISODROME_CONFIG_DIR", str(tmp_path / "config"))
    return tmp_path / "config"


@pytest.fixture
def fake():
    servicer = FakeIsodrome()
    server, endpoint = serve_grpc(servicer)
    servicer.endpoint = endpoint
    yield servicer
    server.stop(None)


@pytest.fixture
def iso(fake):
    """Runs `iso …` against the fake server with its key; returns the click Result."""
    runner = CliRunner()

    def run(*args, input=None, key=True):
        prefix = ["--endpoint", fake.endpoint] + (["--api-key", KEY] if key else [])
        return runner.invoke(cli, prefix + list(args), input=input, catch_exceptions=False)

    return run
