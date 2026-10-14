"""`feed …`: create and manage feeds, send events, and query them."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from isodrome import output
from isodrome import push as pusher
from isodrome.cli.context import Context, namespace_option, pass_context
from isodrome.parse import (
    format_ns,
    format_position,
    now_ns,
    parse_duration,
    parse_filter,
    parse_position,
    parse_time,
    short_enum,
)
from isodrome.v1 import isodrome_pb2 as pb

TIME_UNITS = {
    "s": pb.TIME_UNIT_SECONDS,
    "ms": pb.TIME_UNIT_MILLISECONDS,
    "us": pb.TIME_UNIT_MICROSECONDS,
    "ns": pb.TIME_UNIT_NANOSECONDS,
}
ACK_MODES = {"replicated": pb.ACK_MODE_REPLICATED, "none": pb.ACK_MODE_NONE}
KEEP = {"first": pb.DEDUPE_KEEP_FIRST, "last": pb.DEDUPE_KEEP_LAST}

format_option = click.option(
    "-o", "--format", "fmt", type=click.Choice(output.FORMATS), default="table", show_default=True
)
where_option = click.option(
    "-w", "--where", "filters", multiple=True, help="Filter, e.g. 'price>100' or 'side in (buy, sell)'. Repeatable."
)
column_option = click.option("-c", "--column", "columns", multiple=True, help="Only this column. Repeatable.")
dedupe_options = [
    click.option("--dedupe", multiple=True, help="Keep one event per value of this column (e.g. _key). Repeatable."),
    click.option("--keep", type=click.Choice(list(KEEP)), default="last", show_default=True, help="With --dedupe."),
]


def _apply(options):
    def decorate(f):
        for option in reversed(options):
            f = option(f)
        return f

    return decorate


def _value(parse, text: str, what: str):
    try:
        return parse(text)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint=what) from None


def _filters(filters) -> list[pb.Filter]:
    return [_value(parse_filter, f, "--where") for f in filters]


def _dedupe(columns, keep: str) -> pb.Dedupe | None:
    return pb.Dedupe(columns=list(columns), keep=KEEP[keep]) if columns else None


@click.group()
def feed() -> None:
    """Create feeds, send events to them, and query them."""


# ---------- Managing feeds ----------


@feed.command("create")
@click.argument("name")
@namespace_option
@click.option("--key", "key_field", help="Field that keys the events (dotted path), e.g. symbol. Omit for one stream.")
@click.option("--time-field", default="", help="Field holding each event's time (default: event_time).")
@click.option("--arrival-time", is_flag=True, help="Events carry no time: use when the server receives them.")
@click.option("--time-unit", type=click.Choice(list(TIME_UNITS)), help="Unit of integer event times (recommended).")
@click.option("--ack", type=click.Choice(list(ACK_MODES)), default="replicated", show_default=True)
@click.option("--partitions", type=int, help="Partitions of a keyed feed (default: the server's).")
@pass_context
def feed_create(
    ctx: Context, name, namespace, key_field, time_field, arrival_time, time_unit, ack, partitions
) -> None:
    """Create feed NAME.

    Each event is a JSON object. Its time comes from the `event_time` field (or --time-field),
    unless --arrival-time; events without one are rejected. With --key, `iso feed latest`
    gives the newest event per key.
    """
    if arrival_time and time_field:
        raise click.UsageError("--arrival-time and --time-field are exclusive")
    request = pb.CreateFeedRequest(
        feed=ctx.feed_ref(name, namespace),
        time_field=time_field,
        arrival_time=arrival_time,
        time_unit=TIME_UNITS.get(time_unit, pb.TIME_UNIT_UNSPECIFIED),
        ack_mode=ACK_MODES[ack],
    )
    if key_field is not None:
        request.key_field = key_field
    if partitions is not None:
        request.partitions = partitions
    f = ctx.client().call("CreateFeed", request)
    click.echo(f"Created feed {f.namespace}/{f.name}.")
    if not f.arrival_time:
        click.echo(
            f"Events need the field `{f.time_field}`; create with --arrival-time if they carry no time.", err=True
        )


@feed.command("list")
@namespace_option
@click.option("--deleted", is_flag=True, help="List deleted feeds that can still be undeleted.")
@pass_context
def feed_list(ctx: Context, namespace, deleted) -> None:
    """List the feeds in a namespace."""
    feeds = ctx.client().call("ListFeeds", pb.ListFeedsRequest(namespace=ctx.namespace(namespace), deleted=deleted))
    if not feeds.feeds:
        click.echo("(no deleted feeds)" if deleted else "(no feeds)")
    for f in feeds.feeds:
        line = (
            f"{f.namespace + '/' + f.name:<32} key={(f.key_field if f.HasField('key_field') else '-'):<16} "
            f"time={'(arrival)' if f.arrival_time else f.time_field:<16} "
            f"ack={short_enum(pb.AckMode, f.ack_mode)}"
        )
        if f.deleted_at_ns:
            line += f"  deleted {format_ns(f.deleted_at_ns)}, purged {format_ns(f.purge_at_ns)} (id {f.id})"
        elif f.stats.rejections.last_hour:
            line += click.style(f"  {f.stats.rejections.last_hour} rejected in the last hour", fg="red")
        click.echo(line)


@feed.command("show")
@click.argument("name")
@namespace_option
@pass_context
def feed_show(ctx: Context, name, namespace) -> None:
    """Show a feed's settings, columns and stats."""
    _print_feed(ctx.client().call("GetFeed", pb.GetFeedRequest(feed=ctx.feed_ref(name, namespace))))


@feed.command("describe")
@click.argument("name")
@namespace_option
@pass_context
def feed_describe(ctx: Context, name, namespace) -> None:
    """Show a feed and how to send to it and query it."""
    client = ctx.client()
    f = client.call("GetFeed", pb.GetFeedRequest(feed=ctx.feed_ref(name, namespace)))
    info = client.server_info()
    _print_feed(f)
    example = {"price": 101.25}
    if f.HasField("key_field") and f.key_field:
        example = {f.key_field: "AAPL", **example}
    if not f.arrival_time:
        example[f.time_field] = "2026-10-14T16:00:00Z"

    ns = f" -n {f.namespace}" if namespace else ""
    click.echo()
    click.echo(f"server:      {info.public_url or ctx.endpoint} (version {info.version}, API {info.api_version})")
    click.echo(f"limits:      {info.max_payload_bytes} bytes per event; retries de-duplicated for "
               f"{info.dedupe_window_ns // 60_000_000_000} min by message id")
    click.echo("send:")
    click.echo(f"  iso feed push {f.name}{ns} --data '{json.dumps(example)}'")
    click.echo(f"  iso feed push {f.name}{ns} --file events.jsonl     # JSON Lines or a JSON array")
    click.echo("query:")
    click.echo(f"  iso feed query {f.name}{ns} --since 1h")
    click.echo(f"  iso feed tail {f.name}{ns}")
    if f.HasField("key_field") and f.key_field:
        click.echo(f"  iso feed latest {f.name}{ns}")


@feed.command("update")
@click.argument("name")
@namespace_option
@click.option("--key", "key_field", help='New key field ("" = unkeyed); only while the feed has no events.')
@click.option("--time-field", help="New time field (dotted path).")
@click.option("--arrival-time", is_flag=True, help="No time field from now on: event time = arrival.")
@click.option("--time-unit", type=click.Choice(list(TIME_UNITS)))
@click.option("--ack", type=click.Choice(list(ACK_MODES)))
@pass_context
def feed_update(ctx: Context, name, namespace, key_field, time_field, arrival_time, time_unit, ack) -> None:
    """Change a feed's settings, for events received from now on."""
    if arrival_time and time_field:
        raise click.UsageError("--arrival-time and --time-field are exclusive")
    request = pb.UpdateFeedRequest(
        feed=ctx.feed_ref(name, namespace),
        time_unit=TIME_UNITS.get(time_unit, pb.TIME_UNIT_UNSPECIFIED),
        ack_mode=ACK_MODES.get(ack, pb.ACK_MODE_UNSPECIFIED),
    )
    if time_field is not None:
        request.time_field = time_field
    if arrival_time:
        request.arrival_time = True
    if key_field is not None:
        request.key_field = key_field
    _print_feed(ctx.client().call("UpdateFeed", request))


@feed.command("delete")
@click.argument("name")
@namespace_option
@click.option("-y", "--yes", is_flag=True, help="Do not ask for confirmation.")
@pass_context
def feed_delete(ctx: Context, name, namespace, yes) -> None:
    """Delete a feed. It can be undeleted until its data is purged (7 days by default)."""
    ref = ctx.feed_ref(name, namespace)
    if not yes:
        click.confirm(f"Delete feed {ref.namespace or '(default)'}/{name}?", abort=True, err=True)
    f = ctx.client().call("DeleteFeed", pb.DeleteFeedRequest(feed=ref))
    click.echo(
        f"Deleted {f.namespace}/{f.name}. Its data is purged at {format_ns(f.purge_at_ns)}; "
        f"until then: iso feed undelete {f.name}"
    )


@feed.command("undelete")
@click.argument("name")
@namespace_option
@click.option("--id", "feed_id", default="", help="Which one, if several deleted feeds had this name.")
@pass_context
def feed_undelete(ctx: Context, name, namespace, feed_id) -> None:
    """Restore a deleted feed."""
    f = ctx.client().call("UndeleteFeed", pb.UndeleteFeedRequest(feed=ctx.feed_ref(name, namespace), id=feed_id))
    click.echo(f"Restored {f.namespace}/{f.name}.")


@feed.command("errors")
@click.argument("name")
@namespace_option
@click.option("--limit", default=20, show_default=True, help="Most recent first; at most 1,000.")
@pass_context
def feed_errors(ctx: Context, name, namespace, limit) -> None:
    """Show the most recently rejected events and why."""
    rejections = ctx.client().call(
        "ListRejections", pb.ListRejectionsRequest(feed=ctx.feed_ref(name, namespace), limit=limit)
    ).rejections
    if not rejections:
        click.echo("(no rejected events)")
    for r in rejections:
        click.echo(
            f"{format_ns(r.rejected_at_ns)}  {click.style(short_enum(pb.RejectionReason, r.reason), fg='red'):<24} "
            f"{r.message_id}  {_indent(r.detail)}"
        )
        payload = r.payload.decode("utf-8", "replace")
        if r.original_payload_bytes > len(r.payload):
            payload += f"… ({r.original_payload_bytes} bytes)"
        click.echo(f"    {payload}")


def _indent(detail: str) -> str:
    """The server's details can span lines (e.g. a JSON error with a caret); keep them under their event."""
    return "\n    ".join(line.expandtabs(4) for line in detail.strip().splitlines() if line.strip())


def _print_feed(f: pb.Feed) -> None:
    rows = [
        ("feed", f"{f.organization}/{f.namespace}/{f.name}"),
        ("id", f.id),
        ("key field", f.key_field if f.HasField("key_field") and f.key_field else "(none: one ordered stream)"),
        ("time field", "(none: event time = arrival)" if f.arrival_time else f.time_field),
        ("time unit", short_enum(pb.TimeUnit, f.time_unit)),
        ("ack mode", short_enum(pb.AckMode, f.ack_mode)),
        ("partitions", str(f.partitions)),
        ("created", format_ns(f.created_at_ns)),
    ]
    if f.deleted_at_ns:
        rows.append(("deleted", f"{format_ns(f.deleted_at_ns)}; purged {format_ns(f.purge_at_ns)}"))
    s = f.stats
    rows.append(
        (
            "stats",
            f"flushed={s.events_flushed} pending={s.events_pending_flush} flush_lag={s.flush_lag_ms}ms "
            f"files={s.file_count} schema_conflicts={s.schema_conflicts}",
        )
    )
    for name, value in rows:
        click.echo(f"{name + ':':<13}{value}")
    r = s.rejections
    if r.last_hour:
        reasons = ", ".join(f"{k} ×{v}" for k, v in sorted(r.last_hour_by_reason.items(), key=lambda kv: -kv[1]))
        click.secho(
            f"WARNING:     {r.last_hour} events rejected in the last hour ({reasons}); see `iso feed errors {f.name}`",
            fg="red",
        )
        if r.HasField("latest"):
            click.secho(f"             latest: {r.latest.detail}", fg="red")
    click.echo("columns:")
    if not f.columns:
        click.echo("  (none yet: columns are inferred from the events)")
    for c in f.columns:
        click.echo(f"  {c.name:<32} {short_enum(pb.ColumnType, c.type):<8} first seen {format_ns(c.first_seen_ns)}")


# ---------- Data ----------


@feed.command("push")
@click.argument("name")
@namespace_option
@click.option("-d", "--data", multiple=True, help="An event (JSON object) or a JSON array of them. Repeatable.")
@click.option(
    "-f", "--file", "files", multiple=True, type=click.Path(allow_dash=True, dir_okay=False),
    help="JSON Lines, a JSON array, or one JSON object; - for stdin. Repeatable.",
)
@click.option("--batch-size", default=pusher.DEFAULT_BATCH_SIZE, show_default=True, help="Events per request.")
@click.option("-q", "--quiet", is_flag=True, help="Print only rejections.")
@pass_context
def feed_push(ctx: Context, name, namespace, data, files, batch_size, quiet) -> None:
    """Send events to a feed.

    Retries never write an event twice. Events from --file get ids from the file and their
    place in it, so pushing the same file again is answered "already sent" (within the server's
    de-duplication window, 15 minutes by default). Every rejected event is printed with the
    reason, and the exit status is 1 if any were rejected.
    """
    if not data and not files:
        if sys.stdin.isatty():
            raise click.UsageError("give events with --data or --file (or pipe them in)")
        files = ("-",)
    try:
        items = [
            pusher.Item(source=where, payload=payload)
            for i, text in enumerate(data, 1)
            for where, payload in pusher.parse_events(text, f"--data #{i}" if len(data) > 1 else "--data")
        ]
        for path in files:
            if path == "-":
                items += [pusher.Item(source=w, payload=p) for w, p in pusher.parse_events(sys.stdin.read(), "stdin")]
            else:
                items += [
                    pusher.Item(source=w, payload=p, message_id=pusher.stable_id(path, w, p))
                    for w, p in pusher.parse_events(Path(path).read_text(), path)
                ]
    except ValueError as e:
        raise click.ClickException(str(e)) from None
    if not items:
        raise click.ClickException("no events to send")

    result = pusher.send(ctx.client(), ctx.feed_ref(name, namespace), items, batch_size=max(batch_size, 1))
    for item, rejection in result.rejected:
        click.secho(
            f"REJECTED {item.source}: {short_enum(pb.RejectionReason, rejection.reason)}: {_indent(rejection.detail)}",
            fg="red", bold=True, err=True,
        )
        if item.payload:
            payload = item.payload.decode("utf-8", "replace")
            click.secho(f"    {payload[:200]}{'…' if len(payload) > 200 else ''}", fg="red", err=True)
    summary = f"{result.accepted} accepted"
    if result.duplicates:
        summary += f" ({result.duplicates} already sent)"
    if result.rejected:
        click.secho(f"{summary}, {len(result.rejected)} REJECTED (see above, or `iso feed errors {name}`)",
                    fg="red", bold=True, err=True)
        click.get_current_context().exit(1)
    elif not quiet:
        click.echo(summary)


@feed.command("query")
@click.argument("name")
@namespace_option
@click.option("--since", help="Events from this long ago, e.g. 15m, 1h, 7d.")
@click.option("--start", help="Inclusive start of event time (RFC 3339 or integer ns).")
@click.option("--end", help="Exclusive end of event time.")
@click.option("--as-of", help="Only what had been received by then: replays what was known at that moment.")
@where_option
@column_option
@click.option("--limit", default=100, show_default=True, help="Most rows to return; 0 for all.")
@click.option("--payload", is_flag=True, help="Include the original JSON event (_payload).")
@click.option("--count", is_flag=True, help="Print only the number of matching events.")
@click.option("--at-position", help="Repeat an earlier query exactly: the position it printed.")
@_apply(dedupe_options)
@format_option
@pass_context
def feed_query(
    ctx: Context, name, namespace, since, start, end, as_of, filters, columns, limit, payload, count,
    at_position, dedupe, keep, fmt,
) -> None:
    """Read a feed's events by event time, filters and as-of."""
    if since and start:
        raise click.UsageError("--since and --start are exclusive")
    request = pb.ReadRequest(
        feed=ctx.feed_ref(name, namespace),
        filters=_filters(filters),
        columns=list(columns),
        include_payload=payload,
    )
    if since:
        request.start_event_time_ns = now_ns() - _value(parse_duration, since, "--since")
    if start:
        request.start_event_time_ns = _value(parse_time, start, "--start")
    if end:
        request.end_event_time_ns = _value(parse_time, end, "--end")
    if as_of:
        request.as_of_ns = _value(parse_time, as_of, "--as-of")
    if at_position:
        request.at_position.CopyFrom(_value(parse_position, at_position, "--at-position"))
    if d := _dedupe(dedupe, keep):
        request.dedupe.CopyFrom(d)
    if count:
        request.columns[:] = request.columns or ["_offset"]  # no data needed, just rows
    elif limit:
        request.limit = limit + 1  # one more, to tell whether there were more

    printer = output.Printer(fmt)
    rows, position, shown = 0, None, 0
    for message in ctx.client().stream("Read", request, timeout=300):
        if message.HasField("position"):
            position = message.position
        table = output.decode(message.batch.ipc)
        if table is None:
            continue
        rows += table.num_rows
        if not count:
            if limit:
                table = table.slice(0, max(limit - shown, 0))
            shown += table.num_rows
            printer.table(table)
    if count:
        click.echo(rows)
        return
    printer.finish("(no events)")
    if limit and rows > limit:
        click.echo(f"(first {limit} events; --limit to see more, --limit 0 for all)", err=True)
    if position is not None and fmt == "table":
        click.echo(f"position {format_position(position)} (--at-position to repeat this query exactly)", err=True)


@feed.command("tail")
@click.argument("name")
@namespace_option
@click.option("-l", "--last", default=10, show_default=True, help="Start with the last N events.")
@click.option("--from-beginning", is_flag=True, help="Start with the first event.")
@click.option("--from", "from_time", help="Start from this event time (RFC 3339 or integer ns).")
@click.option("--speed", type=float, help="Replay history paced by event time (1 = real time).")
@click.option("--no-follow", is_flag=True, help="Stop once history is printed; do not wait for new events.")
@where_option
@column_option
@_apply(dedupe_options)
@format_option
@pass_context
def feed_tail(
    ctx: Context, name, namespace, last, from_beginning, from_time, speed, no_follow, filters, columns,
    dedupe, keep, fmt,
) -> None:
    """Print recent events, then new ones as they arrive (Ctrl-C to stop)."""
    columns = list(columns) or ["_event_time", "_key", "_payload"]
    request = pb.SubscribeRequest(
        feed=ctx.feed_ref(name, namespace),
        filters=_filters(filters),
        columns=columns,
        delivery=pb.DELIVERY_CONFIRMED,
        include_payload="_payload" in columns,
    )
    if from_beginning:
        request.from_beginning = True
    elif from_time:
        request.from_event_time_ns = _value(parse_time, from_time, "--from")
    elif last > 0:
        request.from_last = last
    else:
        request.from_now = True
    if speed is not None:
        request.speed = speed
    if d := _dedupe(dedupe, keep):
        request.dedupe.CopyFrom(d)

    printer = output.Printer(fmt)
    stream = ctx.client().stream("Subscribe", request)
    try:
        for message in stream:
            kind = message.WhichOneof("message")
            if kind == "batch":
                printer.table(output.decode(message.batch.ipc))
            elif kind == "caught_up":
                if no_follow:
                    break
                if fmt == "table":
                    click.echo("--- live ---", err=True)
    finally:
        stream.cancel()


@feed.command("latest")
@click.argument("name")
@namespace_option
@click.option("-k", "--key", "keys", multiple=True, help="Only this key. Repeatable.")
@column_option
@format_option
@pass_context
def feed_latest(ctx: Context, name, namespace, keys, columns, fmt) -> None:
    """Show the newest event per key."""
    response = ctx.client().call(
        "Latest", pb.LatestRequest(feed=ctx.feed_ref(name, namespace), keys=list(keys), columns=list(columns))
    )
    printer = output.Printer(fmt)
    printer.table(output.decode(response.batch.ipc))
    printer.finish("(no events)")
