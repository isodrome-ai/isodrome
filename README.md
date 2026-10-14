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
iso feed create weather --arrival-time       # events without a timestamp get their arrival time
iso feed push weather --data '{"temperature": 18.5, "city": "Dublin"}'
iso feed query weather --since 1h
iso feed tail weather                        # the last 10 events, then new ones live
```

Events are JSON objects. A feed takes each event's time from its `event_time` field (or
`--time-field`) unless created with `--arrival-time`, and with `--key FIELD` keeps the newest
event per key for `iso feed latest`. `iso feed push` reads `--data`, `--file` (JSON Lines, a
JSON array, or one object) or standard input, and prints every rejected event and why.

## Commands

| Command | What it does |
|---|---|
| `iso login` / `logout` | sign in with the browser (or `--api-key`); logout revokes the key |
| `iso whoami`, `iso server`, `iso --version` | your identity; the server's version and limits |
| `iso namespace create` / `list` / `delete` / `use` | namespaces; `use` sets the one commands act on |
| `iso key create` / `list` / `revoke` | API keys (admin) |
| `iso feed create` / `list` / `show` / `describe` / `update` | feeds; `describe` shows how to send and query |
| `iso feed delete` / `undelete` / `errors` | soft deletion (7 days to undo); recent rejections |
| `iso feed push` / `query` / `tail` / `latest` | send and read events; `-o table\|json\|csv` |

`iso <command> --help` describes each one.

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
ISODROME_E2E_ENDPOINT=http://localhost:7470 pytest -m e2e tests/e2e
```

**Releases:** publishing a GitHub release builds the package and uploads it to PyPI.
