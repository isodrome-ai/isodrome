# Transformers

A **transformer** is Python that Isodrome runs on feeds' events to write a feed: live as events
arrive, and over history (a backtest) with exactly the same results. This page covers writing one,
testing it, deploying it and reading what it writes. The server's own reference is
`isodrome-server/docs/CLI.md` ("Transformers", "Projects, builds and verification").

## Writing one

A project is a directory: `main.py` (or the modules named in `pyproject.toml`'s
`[tool.isodrome] modules`), its requirements (`requirements.txt`, `pyproject.toml` or `uv.lock`),
and optionally fixtures in `isodrome_tests/`. The code declares its transformers:

```python
import isodrome as iso

SCHEDULE = "isodrome/public/nfl_schedule"

@iso.transformer(
    name="nfl-elo",
    triggers={"results": "isodrome/public/nfl_results", "schedule": SCHEDULE},
    output=iso.output("nfl_elo", key="team", time="rated_at", publication_time="rated_at"),
    as_of="published",
    state=True,
)
def elo(event, ctx):
    ratings = ctx.state.setdefault("ratings", {})
    ...
    return [{"team": "KC", "elo": 1650.2, "rated_at": event["kickoff"]}]
```

- `entrypoint(event, ctx)` returns a dict, a list of dicts, yields dicts, or returns None. `event`
  has its JSON fields by key or attribute, and `event.key`, `event.event_time_ns`,
  `event.receive_time_ns`, `event.published_time_ns`, `event.trigger`.
- **Triggers** are the feeds whose events invoke it; a trigger may give a **window** instead of
  one event: `iso.feed(ref, window=10)` (the last 10 events) or `window="10m"` (10 minutes of
  event time), sliding by default, or `{"duration": "1h", "tumbling": True, "all_keys": True}`.
- **Dependencies** are feeds it reads as of each trigger: `ctx.<name>.at(key)` (the version with
  the greatest event time at or before the trigger's) and `ctx.<name>.history(key, start, end)`.
  Each keeps a **horizon** of event time in memory: default 24 hours, at most **400 days**
  (`iso.feed(SCHEDULE, horizon="400d")`: a season's schedule, a year of reference data).
- **Free reads**: `iso.get(feed, key)` and `iso.read(feed, start, end, limit=1000)` read any feed
  as known by the trigger (reference data that does not belong in the flow).
- **Output**: `iso.output(feed, key=..., time=..., publication_time=...)`, a feed in the
  transformer's namespace. A row without the time field takes its trigger's time.

### What a trigger sees: the as-of basis

- `as_of="received"` (the default): exactly what Isodrome had **received** when the trigger
  arrived. Triggers are replayed in **arrival** order.
- `as_of="published"`: what the sources had **published** by the time the trigger itself was
  published, for backfilled history. Triggers are replayed in **publication order**
  (publication time, else event time), and each one sees what had been published by then.
  (Earlier server versions replayed in event-time order.)

Either way, a backtest computes exactly what live computed.

### State: `ctx.state`

With `state=True` (or `iso transformer deploy --state`), `ctx.state` is a dict the code keeps from
one event to the next: running totals, ratings, standings.

- It holds **JSON types only**: str keys, lists not tuples, numbers, strings, booleans, None. It
  is checked to read back unchanged.
- At most **2 MB** serialised (`stats.code_state_bytes` shows its size).
- It is **only ever what replaying the triggers gives**. Each new version (the first deploy and
  every redeploy) replays every trigger event in the basis's order before it goes live. A
  backtest warms it up from the very first trigger event. It is **never carried** from one
  version to the next, and cannot be set from outside.
- **Verification is the backfill**: a stateful build's verification replays the whole history
  in the sandbox, and the version it deploys publishes that replay's outputs and continues from
  its final state, rather than replaying it again. So a stateful deploy takes as long as the
  replay: minutes for years of history.
- Each stateful version writes a **new version of its output feed**: a bare read gets the
  latest, and `feed@1` keeps the first version's history, so histories never mix. A transformer
  reading the old version goes on reading it until it is redeployed too.
- `on_restart="latest"` is refused with state: skipping events would make the state something no
  replay gives.

## Fixtures

Fixtures run at every test and deploy, in the project's `isodrome_tests/`:

- `isodrome_tests/*.jsonl` apply to every transformer the project declares;
- `isodrome_tests/<transformer-name>/*.jsonl` apply to that transformer only.

Each file is one scenario, run in a fresh process: windows and **`ctx.state` carry from line to
line** within a file. Each line is one trigger event and what it should produce:

```json
{"trigger": "results", "event": {"game_id": "2025_01_BUF_KC", "home_score": 27}, "key": "2025_01_BUF_KC",
 "event_time": "2025-09-07T20:25:00Z", "published_time": "2025-09-08T00:00:00Z",
 "dependencies": {"schedule": [{"key": "...", "event_time": "...", "fields": {}, "published_time": "..."}]},
 "expect": [{"team": "KC", "elo": 1652.0}]}
```

`trigger`, `key`, `event_time`, `published_time` and `dependencies` are optional;
`"expect_error": true` expects the event to raise.

## Testing and deploying

```bash
iso transformer test docs/examples/nfl --name nfl-elo     # build and verify; deploys nothing
iso transformer deploy docs/examples/nfl --name nfl-elo   # build, verify, then wait until it is live
```

Both upload the project, have Isodrome install its requirements, then verify it:

- `load`: it starts and imports within the memory limit;
- `static`: an undeclared `ctx.<name>` or a wrong signature fail; network libraries, wall-clock
  time and unseeded randomness are warnings;
- `replay`: the triggers' recent events (1,000 each by default), exactly as a backtest would:
  exceptions, the output contract, memory, time per event, and a second run identical;
- `fixtures`: each file and its cases, with what was expected and what came back.

While it waits, the CLI shows the build's phases (`queued`, `building`, `verifying`, `ready`),
and a line every 30 seconds through a long verification (a stateful transformer's replays its
whole history; there is no timeout). After a deploy is ready it waits until the new version is
live, showing any backfill still to replay. A failed build never changes the running version.

Not in `iso` yet: `run-local` (a backtest on your machine) and `deploy --local-backfill` (the
history replayed on your machine and verified by sampling). Both are in `isodrome-dev` for now.

The same from Python:

```python
client = iso.connect()
client.test_transformer("docs/examples/nfl", name="nfl-elo")
client.deploy_transformer("docs/examples/nfl", name="nfl-elo")       # waits until live
client.transformer("nfl-elo")                                         # status, state, backfill, stats
run = client.run_transformer("nfl-season", "2025-09-01", "2026-03-01", into="odds_2025")
```

Deploy options override the declaration: `--trigger name=feed`, `--dependency
name=feed,horizon=400d`, `--window trigger=10m,tumbling`, `--basis published`, `--state`,
`--output/--key/--time/--publication-time`, `--python 3.13`, `--paused`, `--max-error-rate`,
`--sample-events`, `--allow-unverified`, `--no-wait`.

## Inspecting and backtesting

```bash
iso transformer list                        # versions, status, events, stateful, backfill to go
iso transformer show nfl-season             # inputs pinned, basis, state, backfill, stats
iso transformer builds nfl-season           # and: iso transformer build ID [--log] [--lockfile]
iso transformer run nfl-season --from 2025-09-01 --to 2026-03-01 --into odds_2025
iso transformer pause|resume|delete NAME
```

A run replays the triggers' events in `[from, to)` exactly as live saw them, a stateful
transformer's state warmed up from the very first trigger event, into its own feed.

## Reading what it writes

The output is an ordinary feed, in the transformer's namespace:

```bash
iso feed latest nfl_elo -c team -c elo
iso feed query nfl_lines --start 2025-11-27 --end 2025-12-02 --dedupe _key --keep last
iso feed query nfl_lines --as-of 2025-11-30 --as-of-basis published --dedupe _key
```

```python
iso.latest("nfl_elo").to_df()
iso.read("nfl_lines", start="2025-11-27", end="2025-12-02", dedupe=["_key"]).to_df()
iso.read("nfl_lines", as_of="2025-11-30", as_of_basis="published", dedupe=["_key"],
         dedupe_order="publication").to_df()
for batch in iso.subscribe("nfl_elo", last=10):
    ...
```

Feed references may name a version or tag: `nfl_elo@2`, `nfl_elo:prod`.

Feed deletion is refused while a connection writes to the feed or a transformer writes or reads
it: delete those first (the error names them).

[`examples/nfl.ipynb`](../examples/nfl.ipynb) walks through deploying the NFL example's models into
your namespace and reading their feeds: the public inputs are `isodrome/public/nfl_schedule`,
`nfl_results`, `nfl_team_games` and `nfl_injuries`; the models' outputs (`nfl_elo`, `nfl_spread`,
`nfl_forecast`, …) are yours, in the namespace you deployed to.
