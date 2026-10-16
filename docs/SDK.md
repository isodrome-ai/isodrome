# Proposal: the `isodrome` Python SDK

Status: phases 1 and 2 **built**, phase 3 partly (see [Plan](#plan)); this document is now the
design record.
Covers the interface for data exploration in notebooks, the demo that proves it
(`examples/forecast_verification.ipynb`), and how it leads to transformers.

## Why now

The CLI can create, push and inspect feeds. Anyone who wants to *work with* the data still has
to drop to raw gRPC and Arrow, as the prototype behind this proposal did. Meanwhile staging has
real, continuously updated public data: four forecast models (Met Éireann, ECMWF, DWD ICON-EU,
NOAA GFS), Met Éireann observations back to 1946, weather warnings and postal codes.

What Isodrome has that a Parquet bucket does not is **time done right**: three times per event
(event, publication, receive), as-of queries on either basis, de-duplication by arrival or by
publication, and positions that repeat a query exactly. The SDK must make those one argument
away, or the product's main idea stays invisible.

The SDK is also the prerequisite for transformers. A transformer's inputs are queries, and its
backtest is the same query run over history, so the query object designed here is the one that
transformers will declare.

## What was measured

Against staging, reading `isodrome/public` feeds with the existing generated client:

| Read | Rows | Transferred | Time |
|---|---|---|---|
| 3 days of observations, one station, 2 columns | 46 | small | 0.5 s |
| 3 days of a forecast feed, one location, 4 columns | 372–5,876 | small | 0.3 s |
| Dublin Airport since 1946, 2 columns | 707,879 | 11.5 MB | 1.5 s |
| Dublin Airport since 1946, all columns | 707,879 | 237 MB | 6.0 s |

Two consequences for the design:

- **Choosing columns is the big lever (20× less data).** The interface makes it natural, and
  shows the size of a read in progress.
- **Point-in-time questions were not one server call** (now they are: see
  [Server work](#server-work-this-needed)). "Each model's forecast for every
  hour, as it stood 24 hours before" needs every version, then a local per-row filter (see
  [Time](#time-the-three-clocks)). It works today (the prototype scored the models: 24-hour MAE
  ECMWF IFS 0.99 °C, AIFS 0.82 °C, GFS 0.74 °C at Dublin Airport); a server addition would push
  it down.

## Principles

1. **Notebook first.** Every object has a useful `repr` in Jupyter (feeds, schemas, results), and
   a result shows its data's attribution.
2. **pandas by default, Arrow inside.** `.to_df()` gives a pandas DataFrame (UTC timestamps to
   the nanosecond), everywhere a result can be had. `.to_arrow()` and `.to_polars()` (an
   optional extra) are there too.
3. **Time is explicit.** Every time argument takes a `datetime`, a pandas `Timestamp`, an
   RFC 3339 string, integer nanoseconds or a relative string (`"1h"`). Every result keeps
   `_event_time`, `_published_time` and `_receive_time` available. `as_of` always names its
   basis.
4. **Same words as the CLI.** A feed is `"FEED"`, `"NAMESPACE/FEED"` or `"ORG/NAMESPACE/FEED"`;
   `query`, `latest`, `tail`, `push`, `where`, `dedupe` mean what they mean in `iso`. The SDK
   uses `iso login`'s saved credentials, so a notebook needs no key pasted into it.
5. **Lazy queries, eager results.** A query is an immutable description that can be inspected,
   reused, extended and passed around (later: to a transformer). Nothing runs until a result is
   asked for.
6. **Reproducible by default.** Every result records the position it was read at, and
   `query.at(position)` reads exactly the same events again. Such reads are immutable, so they
   can be cached safely.

## The interface

### Connecting

```python
import isodrome as iso

client = iso.connect()                  # the CLI's current profile (`iso login`)
client = iso.connect(profile="local")   # another profile
client = iso.connect(api_key=..., endpoint="https://stg.api.isodrome.ai")  # e.g. CI, service accounts
client                                  # repr: who you are, organization, server, session expiry
```

`ISODROME_API_KEY`, `ISODROME_ENDPOINT` and `ISODROME_PROFILE` work as in the CLI. Module-level
shortcuts (`iso.feed(...)`, `iso.feeds()`) use a default client created on first use, for
one-cell notebooks.

### Finding feeds

```python
client.feeds()                          # every feed you can read: yours, then public ones
client.feeds(public=True)               # FeedList: renders as a table; iterable; .to_pandas()
client.namespaces()

forecast = client.feed("isodrome/public/ecmwf_open_data_forecast")
forecast                                # repr: description, licence, attribution, key and time
                                        # fields, columns and types, event counts, freshness
forecast.columns                        # {"t2m_k": float64, "model": string, ...}
forecast.attribution                    # "Copyright ..."; also shown with every result
```

### Querying

One method, `query`, takes everything the server can do as keyword arguments; the same
options also chain, for building queries up in steps.

```python
q = forecast.query(
    since="3d",                                  # or start=..., end=... (event time)
    where={"_key": "dublin-airport"},            # equality; or expressions, below
    columns=["valid_time", "model", "t2m_k"],
)
q = q.where(iso.col("t2m_k") > 283.15)           # chaining returns a new query
q                                                # repr: the request, in words

df = q.to_df()                                   # pandas; or .to_arrow(), .to_polars(), .count()
```

- **Filters** map onto the server's structured filters: `iso.col(name)` supports `==`, `!=`,
  `<`, `<=`, `>`, `>=`, `.isin([...])`, `.is_null()` and `.is_not_null()`. Several are ANDed. An
  expression the server cannot run (an OR, a function) raises with a hint to filter the frame
  instead: the SDK never quietly downloads more than asked.
- **Columns:** system columns (`_event_time`, `_published_time`, `_receive_time`, `_key`, ...)
  are always available by name. `columns=None` means all, and a large read without `columns`
  shows its size in the progress bar.
- **Limits:** `limit=` as on the server. There is no silent default limit in the SDK (unlike the
  CLI's table output).

### Results

`q.fetch()` returns a `Result`, and the `to_*` shortcuts are `q.fetch().to_*()`.

```python
r = q.fetch()
r.to_df(); r.to_arrow(); r.to_polars()
r.position          # where in the feed's log this read ended
r.attribution       # credit to show with the data; Result's repr shows it under the table
r.server_ms         # time the server spent

again = q.at(r.position).to_df()   # the same events, whatever has arrived since
```

`Result` renders in Jupyter as the first rows, the shape, the time range covered, and the
attribution.

### Time: the three clocks

Every event has an event time (when it happened, or the hour a forecast is for), a publication
time (when the source published it; may be blank) and a receive time (when Isodrome had it).
The SDK names them the same way everywhere.

```python
# What was known at a moment, on either basis:
forecast.query(as_of="2026-10-15T09:00Z")                     # what Isodrome had received
forecast.query(as_of="2026-10-15T09:00Z", basis="published")  # what the source had published

# One version per key and hour: the latest published (corrections and new model runs win).
forecast.query(dedupe=["_key", "_event_time"], keep="last", order="publication")

# Every version, with all three times: the raw material for point-in-time work.
forecast.versions(since="7d", where={"_key": "dublin-airport"}).to_df()
```

**Point-in-time per row** answers questions where "as of" differs per row, such as "the forecast
for each hour as it stood 24 hours earlier" (forecast verification), or features for a training
set without look-ahead:

```python
# A fixed lead: each event as known `lag` before its own event time.
forecast.query(since="7d", as_of_lag="24h", basis="published", dedupe=["_key", "_event_time"])

# Arbitrary times per row, Feast-style: for each row of `left`, the latest version of `right`
# known at that row's time.
iso.as_of_join(left=trades, right=forecast, on="_key", at="trade_time", basis="published")
```

Both run locally today: the SDK reads the versions, keeps those known in time (publication
time, falling back to receive time, as the server does), then de-duplicates (`as_of_lag`) or
matches each row with pandas' `merge_asof` (`as_of_join`). Filters that could otherwise bring
back a superseded version are applied after de-duplication, as on the server. That is correct,
but downloads every version; phase 3 asks the server to do it (see
[Server work](#server-work-this-needed)).

### Latest and live

```python
forecast.latest()                                   # newest event per key
forecast.latest(keys=["dublin-airport"], columns=["t2m_k"])

for batch in forecast.tail(last=10):                # history, then live; Ctrl-C (or break) stops
    print(batch.to_df())

for batch in forecast.subscribe(start="beginning", speed=50, follow=False):   # replay, paced
    ...
async for batch in forecast.subscribe_async(last=10):   # the same, for asyncio code
    ...

forecast.watch(columns=["_key", "t2m_k"])           # Jupyter: a table that updates in place
```

### Writing

```python
feed = client.create_feed("research/scores", key="model", time_field="valid_time")
feed.push(df)                     # pandas/polars/Arrow/list of dicts; message ids derived from the
                                  # rows, so re-running the cell does not write twice
feed.push(df, raise_on_reject=False).rejected   # rejections returned, not just printed
```

### Errors

Exceptions mirror the API's status codes: `iso.NotFound`, `iso.PermissionDenied`,
`iso.Unauthenticated` (with "run `iso login`"), `iso.InvalidArgument`, `iso.Unavailable`
(retried with backoff before it is raised), and `iso.Rejected` for pushes.

## The demo: which forecast should you trust for Dublin tomorrow?

A notebook, `examples/forecast_verification.ipynb`, that runs against staging with nothing but
`iso login`:

1. **Discover:** `iso.feeds(public=True)`, which shows four forecast models, observations,
   warnings, and their licences.
2. **Look at one feed:** `client.feed("isodrome/public/met_eireann_observations")`: Dublin
   Airport's hourly temperature since 1946, plotted (two columns, 1.5 s).
3. **The three clocks:** one forecast hour with all its versions: each model run is a new
   version, published hours apart. `versions()` shows why "the forecast" is ambiguous until you
   say *as of when*.
4. **As of:** "what did ECMWF say at 09:00 about 15:00?" in one query, on the publication basis.
5. **Verification:** for each model, the forecast as it stood 24 hours before each hour, joined
   to what was then observed: mean absolute error and bias per model and lead time, as a chart.
   No look-ahead is possible, because of how the data is queried.
6. **Reproducibility:** `r.position`, then the same scorecard re-read exactly after new data has
   arrived.
7. **Live:** `forecast.watch()` as the next model run lands.

It shows what nobody gets from a Parquet dump: correct as-of answers, versions, and exact
repeats.

## Towards transformers (direction, not v1)

A transformer turns input feeds into an output feed, continuously. With the query object above,
its descriptor is mostly already there:

```python
@iso.transformer(
    inputs={
        "forecast": iso.feed("isodrome/public/ecmwf_open_data_forecast").query(
            columns=["valid_time", "model", "t2m_k"], dedupe=["_key", "_event_time"], order="publication"),
        "observed": iso.feed("isodrome/public/met_eireann_observations").query(
            columns=["temperature_c"]),
    },
    output="research/forecast_errors",
    key="model",
    time="valid_time",
)
def forecast_errors(forecast: pl.DataFrame, observed: pl.DataFrame) -> pl.DataFrame:
    ...

forecast_errors.backtest(since="30d")   # the same function over history, locally, as of each step
forecast_errors.deploy()                # later: Isodrome runs it on new events
```

What this asks of the SDK now is only that queries are plain, serialisable values: no hidden
state, and no callables inside them. Then a transformer descriptor can carry them to the
server.

## Package layout

```
isodrome/
  __init__.py      connect, feed, feeds, namespaces, col, as_of_join, exceptions
  client.py        Client: whoami, feeds(), feed(), namespaces(), create_feed()
  _feed.py         Feed: metadata, query(), versions(), latest(), tail(), subscribe(), watch(), push()
  query.py         Query (immutable, serialisable with to_dict()), col() expressions
  result.py        Result: to_df(), to_arrow(), to_polars(), position, attribution, Jupyter repr
  pit.py           as_of_join (pandas merge_asof)
  errors.py        typed exceptions, retries
  _transport.py    the gRPC connection (shared with the CLI)
  cli/             the `iso` command
```

Dependencies: `grpcio`, `protobuf`, `pyarrow` and `pandas`. Extras: `isodrome[polars]` and
`isodrome[notebook]` (Jupyter and matplotlib, for the examples).

## Plan

| Phase | What | Rough size |
|---|---|---|
| 1 | **Built.** `connect`, `feeds`, `feed`, `Query` (all server options), `Result` with conversions, positions and attribution, `latest`, `versions`, errors, Jupyter reprs. (Not yet: the CLI's `query`/`latest` rebuilt on it.) | the bulk |
| 2 | **Built.** Local point-in-time (`as_of_lag=`, `as_of_join`), `tail`/`subscribe`/`subscribe_async`/`watch`, `push` from frames; the demo notebook | medium |
| 3 | **Partly built.** Server push-down: `as_of_lag` (`read.as_of_lag`), `as_of_join` (`lookup`), read estimates with large-read warnings and progress (`read.estimate`), feed freshness (`feeds.freshness`), each used only where the server lists it, with the local code as the fallback. Still to do: a local cache of position-pinned reads, a full async client | |
| 4 | Transformer descriptor, `backtest`, deploy | after transformers exist on the server |

## Server work this needed

Done in isodrome-server `45cf1b4`, and used by the SDK where `ServerInfo.capabilities` lists it:

1. **Per-row as-of in `Read`** (`as_of_lag_ns`, capability `read.as_of_lag`).
2. **Point-in-time `Lookup`** for (key, time) probes (`lookup`), behind `iso.as_of_join` when the
   query has no time window or as-of of its own.
3. **Read size up front** (`estimated_rows`, `estimated_bytes`, `estimate_only`;
   `read.estimate`): `Query.estimate()`, a `LargeReadWarning` for big reads of every column,
   and a progress bar when `tqdm` is installed.
4. **Feed freshness** (`last_event_time_ns`, `last_receive_time_ns`, `last_published_time_ns`;
   `feeds.freshness`).
5. **Intact gRPC errors through staging's proxy.**

An end-to-end test checks that the server and the SDK's local code give identical answers.
Later, for transformers: a way to declare and run user code against queries.

## Decisions (taken)

1. **pandas** is the default: `.to_df()` returns a pandas DataFrame everywhere; Arrow and Polars
   are available.
2. **Sync first**; `subscribe_async` for asyncio code; a full async client later.
3. **`as_of_lag=`** names the per-row as-of, matching the server field it will map to.
4. **The demo** lives in `examples/` and runs in CI against staging when a key is configured.
