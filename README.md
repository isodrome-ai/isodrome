# Isodrome Python SDK and CLI

`isodrome` is the official Python package for Isodrome, and installs the `iso` command line.

> [!WARNING]
> This project is in **early development**. Commands and APIs may change.

## Install

```bash
pipx install isodrome        # or: uv tool install isodrome, or pip install isodrome
```

## Getting started

```bash
iso login                                    # signs in with your browser and saves a key
iso feed create weather                      # events are timed when they arrive
iso feed push weather --data '{"temperature": 18.5, "city": "Dublin"}'
iso feed query weather --since 1h
iso feed tail weather                        # the last 10 events, then new ones live
```

Events are JSON objects. A feed times each event when it arrives, unless created with
`--time-field FIELD` to use a time carried in the events (needed for late data and meaningful
as-of queries), and with `--key FIELD` keeps the newest event per key for `iso feed latest`. `iso feed push` reads `--data`, `--file` (JSON Lines, a
JSON array, or one object) or standard input, and prints every rejected event and why. Pushing
the same file twice is recognised and not written twice (within the server's 15-minute window).

## In Python

```python
import isodrome as iso

client = iso.connect()                           # uses what `iso login` saved
client.feeds(public=True)                        # a table in Jupyter
obs = client.feed("isodrome/public/met_eireann_observations")

df = obs.query(since="7d", where={"_key": "dublin-airport"}, columns=["_event_time", "temperature_c"]).to_df()

forecast = client.feed("isodrome/public/ecmwf_open_data_forecast")
forecast.query(as_of="2026-10-15T09:00Z", basis="published",          # what had been published then,
               dedupe=["_key", "_event_time"], order="publication")   # one version per hour
forecast.query(as_of_lag="24h", basis="published", dedupe=["_key", "_event_time"])  # each hour, a day ahead
iso.as_of_join(trades, obs, at="time", key="station")                 # each row with what was known then
```

`iso.read(ref, ...)`, `iso.latest(ref, ...)` and `iso.subscribe(ref, ...)` do the same in one call,
with the CLI's options (`start`, `end`, `as_of`, `as_of_basis`, `where`, `columns`, `dedupe`, `keep`,
`dedupe_order`, `limit`). Feed references may name a version or tag: `prices@2`, `prices:prod`.

Results are pandas DataFrames (`.to_df()`; also `.to_arrow()`, `.to_polars()`), carry the
position they were read at (`query.at(result.position)` repeats a read exactly) and the data's
attribution. [`examples/forecast_verification.ipynb`](examples/forecast_verification.ipynb)
scores four weather models against observations, without look-ahead;
[`examples/nfl.ipynb`](examples/nfl.ipynb) deploys the NFL example's models into your namespace and
reads their ratings, spreads and season forecasts as of any moment. `docs/SDK.md` is the design.

## Transformers

```python
import isodrome as iso

@iso.transformer(
    name="nfl-elo",
    triggers={"results": "isodrome/public/nfl_results"},
    output=iso.output("nfl_elo", key="team", time="rated_at"),
    as_of="published",
    state=True,                          # ctx.state: rebuilt only by replaying every trigger event
)
def elo(event, ctx):
    ratings = ctx.state.setdefault("ratings", {})
    ...
```

`iso transformer test` builds and verifies a project (load, static checks, a replay of recent
events, and the fixtures in `isodrome_tests/`); `iso transformer deploy` then waits through the
build and the backfill until it is live. [docs/TRANSFORMERS.md](docs/TRANSFORMERS.md) covers state,
the as-of basis, fixtures and backtests.

## Commands

| Command | What it does |
|---|---|
| `iso login` / `logout` | sign in with the browser (or `--api-key`); logout revokes the key |
| `iso whoami`, `iso server`, `iso --version` | your identity; the server's version and limits |
| `iso namespace create` / `list` / `update` / `delete` / `use` | namespaces; `update --public` publishes one to every organization; `use` sets the one commands act on |
| `iso feed create` / `list` / `show` / `describe` / `update` | feeds (`list`: yours in every namespace, and other organizations' public ones); `describe` shows how to send and query |
| `iso feed delete` / `undelete` / `errors` | soft deletion (7 days to undo); recent rejections |
| `iso feed push` / `query` / `tail` / `latest` | send and read events; `-o table\|json\|csv` |
| `iso key create` / `list` / `revoke` | API keys (personal by default, or for a service account); your sessions |
| `iso service-account create` / `list` / `delete` | identities for software (CI, services), with keys of their own |
| `iso connector templates`, `iso connection create` / `list` / `show` / `credentials` / `pause` / `resume` / `delete` | Isodrome-run downloaders that fill feeds from outside sources |
| `iso transformer test` / `deploy` / `list` / `show` / `run` / `builds` / `pause` / `resume` / `delete` | Python that Isodrome runs on feeds' events to write a feed; see [docs/TRANSFORMERS.md](docs/TRANSFORMERS.md) |

`iso <command> --help` describes each one.

## Feeds from other organizations

A feed is named `FEED` (in the namespace in use), `NAMESPACE/FEED`, or
`ORGANIZATION/NAMESPACE/FEED`. The last form reaches another organization's **public** feeds,
such as Isodrome's open data, which any signed-in user can read but only their publisher can
change:

```bash
iso feed list                                              # yours, then public ones from others
iso feed show isodrome/public/met_eireann_point_forecast   # with its source, licence and attribution
iso feed latest isodrome/public/met_eireann_point_forecast -c location -c temperature.value
iso namespace use isodrome/public                          # then refer to its feeds by name alone
```

When a feed's source asks for credit, `iso` prints the attribution (on stderr) with the data.

## Configuration and profiles

`iso` keeps its settings in `~/.config/isodrome/config.toml` (mode 0600, as it holds API keys).
Each profile has an endpoint, a key and a namespace; `iso login` signs in to the cloud
(`https://stg.api.isodrome.ai` for now). A local server has no browser sign-in, so give it its key:

```bash
iso --profile local login --endpoint http://localhost:7470 --api-key iso_...
iso profile use local          # or pass --profile local per command
```

`ISODROME_PROFILE`, `ISODROME_ENDPOINT` and `ISODROME_API_KEY` override the configuration.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest                                       # unit tests, against an in-process fake server
pip install -e '.[dev,notebook]'             # to run the example notebook
```

**The API client** in `src/isodrome/v1` is generated from `proto/isodrome/v1/isodrome.proto`,
a copy of the server's. After the server's API changes, with `isodrome-server` checked out next
to this repository (or `ISODROME_SERVER=path`):

```bash
scripts/sync_proto.sh             # copy the proto and regenerate
scripts/sync_proto.sh --check     # what CI runs: fails if either is out of date
```

**End-to-end tests** run the CLI against a real server:

```bash
docker compose -f tests/e2e/docker-compose.yml up -d --wait   # ISODROME_SERVER_IMAGE=… for another image
export ISODROME_E2E_OTHER_KEY=$(docker compose -f tests/e2e/docker-compose.yml exec -T isodrome-server \
  isodrome-server create-organization other | awk '/admin key:/ {print $3}')   # for the public-feed test
ISODROME_E2E_ENDPOINT=http://localhost:7470 pytest -m e2e tests/e2e
```

**Releases:** publishing a GitHub release builds the package and uploads it to PyPI.
