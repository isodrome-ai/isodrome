"""`feed …`: create and manage feeds, send events, and query them."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from isodrome import _output as output
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
DEDUPE_ORDERS = {"arrival": pb.DEDUPE_ORDER_ARRIVAL, "publication": pb.DEDUPE_ORDER_PUBLICATION}
AS_OF_BASES = {"received": pb.AS_OF_BASIS_RECEIVED, "published": pb.AS_OF_BASIS_PUBLISHED}

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
    click.option(
        "--dedupe-order", type=click.Choice(list(DEDUPE_ORDERS)), default="arrival", show_default=True,
        help="With --dedupe: which version is first/last, by arrival or by publication time.",
    ),
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


# Bookkeeping a person rarely needs in a table: positions, ids and (for most feeds) arrival.
_INTERNAL = ("_partition", "_offset", "_message_id", "_receive_time")


def _readable(table):
    """A table without internal columns, nor `_key` or `_published_time` when they are empty."""
    drop = [c for c in _INTERNAL if c in table.column_names]
    for optional in ("_key", "_published_time"):
        if optional in table.column_names and table.column(optional).null_count == table.num_rows:
            drop.append(optional)
    return table.drop_columns(drop)


def _filters(filters) -> list[pb.Filter]:
    return [_value(parse_filter, f, "--where") for f in filters]


def _dedupe(columns, keep: str, order: str) -> pb.Dedupe | None:
    return pb.Dedupe(columns=list(columns), keep=KEEP[keep], order=DEDUPE_ORDERS[order]) if columns else None


def _attribution(ctx: Context, ref: pb.FeedRef) -> None:
    """Data from a source that asks for credit is shown with it (on stderr, apart from the data)."""
    f = ctx.client().call("GetFeed", pb.GetFeedRequest(feed=ref))
    if f.attribution:
        click.secho(f"Data: {f.attribution}", dim=True, err=True)


@click.group()
def feed() -> None:
    """Create feeds, send events to them, and query them."""


# ---------- Managing feeds ----------


# Where the data comes from and on what terms: shown with the feed, and with its data.
provenance_options = [
    click.option("--description", help="What the feed holds."),
    click.option("--licence", help='The terms the data may be used on, e.g. "CC BY 4.0".'),
    click.option("--attribution", help="Credit to show wherever the data is shown."),
    click.option("--source-url", help="Where the data comes from."),
]


@feed.command("create")
@click.argument("name")
@namespace_option
@click.option("--key", "key_field", help="Field that keys the events (dotted path), e.g. symbol. Omit for one stream.")
@click.option(
    "--time-field", help="Field holding each event's own time, e.g. event_time. Default: the time it arrives."
)
@click.option("--time-unit", type=click.Choice(list(TIME_UNITS)), help="Unit of integer event times (recommended).")
@click.option(
    "--publication-time-field", help="Field holding when the source published each event (optional; for as-of)."
)
@click.option("--arrival-time", is_flag=True, hidden=True)  # the default; accepted for explicitness
@click.option("--ack", type=click.Choice(list(ACK_MODES)), default="replicated", show_default=True)
@click.option("--partitions", type=int, help="Partitions of a keyed feed (default: the server's).")
@_apply(provenance_options)
@pass_context
def feed_create(
    ctx: Context, name, namespace, key_field, time_field, time_unit, publication_time_field, arrival_time, ack,
    partitions, description, licence, attribution, source_url,
) -> None:
    """Create feed NAME (or NAMESPACE/NAME).

    Each event is a JSON object. By default its time is when it arrives; with --time-field it
    is the event's own time from that field, and events without it are rejected (late events
    then sort into place, and queries by time and as-of mean what happened when). With --key,
    `iso feed latest` gives the newest event per key.
    """
    if time_unit and not time_field:
        time_field = "event_time"  # a unit only makes sense for times carried in the events
    if arrival_time and time_field:
        raise click.UsageError("--arrival-time and --time-field are exclusive")
    request = pb.CreateFeedRequest(
        feed=ctx.writable_ref(name, namespace),
        time_field=time_field or "",
        arrival_time=not time_field,
        time_unit=TIME_UNITS.get(time_unit, pb.TIME_UNIT_UNSPECIFIED),
        ack_mode=ACK_MODES[ack],
        description=description or "",
        licence=licence or "",
        attribution=attribution or "",
        source_url=source_url or "",
    )
    if key_field is not None:
        request.key_field = key_field
    if partitions is not None:
        request.partitions = partitions
    if publication_time_field:
        request.publication_time_field = publication_time_field
    f = ctx.client().call("CreateFeed", request)
    click.echo(f"Created feed {f.namespace}/{f.name}{' (public)' if f.public else ''}.")
    if f.arrival_time:
        click.echo("Events are timed when they arrive (--time-field to use a time in the events).", err=True)
    else:
        click.echo(f"Events need the field `{f.time_field}`; events without it are rejected.", err=True)


@feed.command("list")
@click.option(
    "-n", "--namespace", default=None,
    help="Only this namespace (NAME, or ORGANIZATION/NAME for another organization's public one).",
)
@click.option("--public", "public_only", is_flag=True, help="Only public feeds (readable from every organization).")
@click.option("--mine", is_flag=True, help="Only your organization's feeds.")
@click.option("--deleted", is_flag=True, help="Deleted feeds that can still be undeleted.")
@format_option
@pass_context
def feed_list(ctx: Context, namespace, public_only, mine, deleted, fmt) -> None:
    """List feeds: your organization's, in every namespace, and other organizations' public ones.

    FEED is how to refer to each one in other commands: NAMESPACE/FEED in your organization,
    ORGANIZATION/NAMESPACE/FEED in another. ACCESS says who can read it: `org` (your
    organization), `public` (everyone; yours to change) or `public, read-only` (another
    organization's).
    """
    client = ctx.client()
    me = ctx.me()
    if namespace:
        organization, ns = ctx.scope(namespace)
        places = [(organization, ns)]
    else:
        places = [
            ("", n.name)
            for n in client.call("ListNamespaces", pb.ListNamespacesRequest()).namespaces
            if n.public or not public_only
        ]
        if not mine and not deleted:
            places += [
                (n.organization, n.name)
                for n in client.call("ListNamespaces", pb.ListNamespacesRequest(public=True)).namespaces
                if n.organization != me.organization
            ]
    rows = []
    for organization, ns in places:
        listed = client.call(
            "ListFeeds", pb.ListFeedsRequest(organization=organization, namespace=ns, deleted=deleted)
        )
        for f in listed.feeds:
            if public_only and not f.public:
                continue
            ours = f.organization in ("", me.organization)
            received = f.stats.last_receive_time_ns
            row = {
                "feed": ctx.display_ref(f.organization, f.namespace, f.name),
                "access": "org" if not f.public else "public" if ours else "public, read-only",
                "key": f.key_field if f.HasField("key_field") and f.key_field else "-",
                "time": "(arrival)" if f.arrival_time else f.time_field,
                "last received": _ago(received) if received else "-",
                "description": f.description,
            }
            if deleted:
                row["deleted"] = format_ns(f.deleted_at_ns)
                row["purged"] = format_ns(f.purge_at_ns)
                row["id"] = f.id
            elif f.stats.rejections.last_hour:
                row["rejected (1h)"] = f.stats.rejections.last_hour
            rows.append(row)
    if fmt != "table":
        columns = list(dict.fromkeys(c for row in rows for c in row))
        output.Printer(fmt).rows(rows, columns)
        return
    if not rows:
        click.echo("(no deleted feeds)" if deleted else "(no feeds)")
        return
    printer = output.Printer("table", max_width=50)
    columns = list(dict.fromkeys(c for row in rows for c in row))
    printer.rows(rows, columns)
    if any(r.get("rejected (1h)") for r in rows):
        click.secho("Some feeds are rejecting events: see `iso feed errors FEED`.", fg="red", err=True)


@feed.command("show")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@pass_context
def feed_show(ctx: Context, feed_ref, namespace) -> None:
    """Show a feed's settings, source, columns and stats."""
    _print_feed(ctx, ctx.client().call("GetFeed", pb.GetFeedRequest(feed=ctx.feed_ref(feed_ref, namespace))))


@feed.command("describe")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@pass_context
def feed_describe(ctx: Context, feed_ref, namespace) -> None:
    """Show a feed and how to send to it and query it."""
    client = ctx.client()
    f = client.call("GetFeed", pb.GetFeedRequest(feed=ctx.feed_ref(feed_ref, namespace)))
    info = client.server_info()
    _print_feed(ctx, f)
    ours = f.organization in ("", ctx.me().organization)
    # The shortest reference that works from here.
    ref = feed_ref if not namespace else ctx.display_ref(f.organization, f.namespace, f.name)

    click.echo()
    click.echo(f"server:      {info.public_url or ctx.endpoint} (version {info.version}, API {info.api_version})")
    if ours:
        click.echo(f"limits:      {info.max_payload_bytes} bytes per event; retries de-duplicated for "
                   f"{info.dedupe_window_ns // 60_000_000_000} min by message id")
        click.echo("send:")
        click.echo(f"  iso feed push {ref} --data '{json.dumps(_example_event(f))}'")
        click.echo(f"  iso feed push {ref} --file events.jsonl     # JSON Lines or a JSON array")
    else:
        click.echo(f"access:      read-only: {f.organization} publishes it")
    click.echo("query:")
    click.echo(f"  iso feed query {ref} --since 1h")
    click.echo(f"  iso feed tail {ref}")
    if f.HasField("key_field") and f.key_field:
        click.echo(f"  iso feed latest {ref}")


@feed.command("update")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@click.option("--key", "key_field", help='New key field ("" = unkeyed); only while the feed has no events.')
@click.option("--time-field", help="New time field (dotted path).")
@click.option("--arrival-time", is_flag=True, help="No time field from now on: event time = arrival.")
@click.option("--time-unit", type=click.Choice(list(TIME_UNITS)))
@click.option("--publication-time-field", help='Field holding when the source published each event ("" = none).')
@click.option("--ack", type=click.Choice(list(ACK_MODES)))
@_apply(provenance_options)
@pass_context
def feed_update(
    ctx: Context, feed_ref, namespace, key_field, time_field, arrival_time, time_unit, publication_time_field, ack,
    description, licence, attribution, source_url,
) -> None:
    """Change a feed's settings (for events received from now on) or its description."""
    if arrival_time and time_field:
        raise click.UsageError("--arrival-time and --time-field are exclusive")
    request = pb.UpdateFeedRequest(
        feed=ctx.writable_ref(feed_ref, namespace),
        time_unit=TIME_UNITS.get(time_unit, pb.TIME_UNIT_UNSPECIFIED),
        ack_mode=ACK_MODES.get(ack, pb.ACK_MODE_UNSPECIFIED),
    )
    if time_field is not None:
        request.time_field = time_field
    if arrival_time:
        request.arrival_time = True
    for field, value in (
        ("key_field", key_field),
        ("publication_time_field", publication_time_field),
        ("description", description),
        ("licence", licence),
        ("attribution", attribution),
        ("source_url", source_url),
    ):
        if value is not None:
            setattr(request, field, value)
    _print_feed(ctx, ctx.client().call("UpdateFeed", request))


@feed.command("delete")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@click.option("-y", "--yes", is_flag=True, help="Do not ask for confirmation.")
@pass_context
def feed_delete(ctx: Context, feed_ref, namespace, yes) -> None:
    """Delete a feed. It can be undeleted until its data is purged (7 days by default).

    Refused while a connection writes to it or a transformer writes or reads it: delete those
    first (the error names them)."""
    ref = ctx.writable_ref(feed_ref, namespace)
    if not yes:
        click.confirm(f"Delete feed {ref.namespace or '(default)'}/{ref.name}?", abort=True, err=True)
    f = ctx.client().call("DeleteFeed", pb.DeleteFeedRequest(feed=ref))
    click.echo(
        f"Deleted {f.namespace}/{f.name}. Its data is purged at {format_ns(f.purge_at_ns)}; "
        f"until then: iso feed undelete {f.namespace}/{f.name}"
    )


@feed.command("undelete")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@click.option("--id", "feed_id", default="", help="Which one, if several deleted feeds had this name.")
@pass_context
def feed_undelete(ctx: Context, feed_ref, namespace, feed_id) -> None:
    """Restore a deleted feed."""
    f = ctx.client().call(
        "UndeleteFeed", pb.UndeleteFeedRequest(feed=ctx.writable_ref(feed_ref, namespace), id=feed_id)
    )
    click.echo(f"Restored {f.namespace}/{f.name}.")


@feed.command("errors")
@click.argument("feed_ref", metavar="FEED")
@namespace_option
@click.option("--limit", default=20, show_default=True, help="Most recent first; at most 1,000.")
@pass_context
def feed_errors(ctx: Context, feed_ref, namespace, limit) -> None:
    """Show the most recently rejected events and why."""
    rejections = ctx.client().call(
        "ListRejections", pb.ListRejectionsRequest(feed=ctx.feed_ref(feed_ref, namespace), limit=limit)
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


_SAMPLES = {
    pb.COLUMN_TYPE_BOOL: True,
    pb.COLUMN_TYPE_INT64: 1,
    pb.COLUMN_TYPE_FLOAT64: 1.5,
    pb.COLUMN_TYPE_STRING: "text",
    pb.COLUMN_TYPE_JSON: [],
}


def _example_event(f: pb.Feed) -> dict:
    """An event shaped like the feed's: its inferred columns (nested back from dotted names),
    plus the key and time fields it needs. Before any are inferred, a placeholder."""
    example: dict = {}

    def put(path: str, value) -> None:
        *parents, leaf = path.split(".")
        node = example
        for part in parents:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                return
        node.setdefault(leaf, value)

    for column in f.columns:
        put(column.name, _SAMPLES.get(column.type, "text"))
    if not example:
        put("value", 1.5)
    if f.HasField("key_field") and f.key_field:
        put(f.key_field, "key-1")
    if not f.arrival_time:
        put(f.time_field, "2026-10-14T16:00:00Z")
    return example


def _ago(ns: int) -> str:
    """How long ago, roughly: "45s ago", "3h ago", "12d ago"."""
    seconds = max((now_ns() - ns) / 1e9, 0)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds / size:.0f}{unit} ago"
    return f"{seconds:.0f}s ago"


def _indent(detail: str, by: int = 4) -> str:
    """Text that may span lines (e.g. a JSON error with a caret), indented to stay under its label."""
    return ("\n" + " " * by).join(line.expandtabs(4) for line in detail.strip().splitlines() if line.strip())


def _print_feed(ctx: Context, f: pb.Feed) -> None:
    ours = f.organization in ("", ctx.me().organization)
    rows = [
        ("feed", f"{f.organization}/{f.namespace}/{f.name}"),
        ("access", "your organization" if not f.public else "public" if ours else f"public, read-only ({f.organization})"),
    ]
    rows += [(label, value) for label, value in (
        ("description", f.description),
        ("source", f.source_url),
        ("licence", f.licence),
        ("attribution", f.attribution),
    ) if value]
    rows += [
        ("id", f.id),
        ("key field", f.key_field if f.HasField("key_field") and f.key_field else "(none: one ordered stream)"),
        ("time field", "(none: event time = arrival)" if f.arrival_time else f.time_field),
        ("time unit", short_enum(pb.TimeUnit, f.time_unit)),
    ]
    if f.publication_time_field:
        rows.append(("published", f"field {f.publication_time_field} (as-of --as-of-basis published)"))
    rows += [
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
        click.echo(f"{name + ':':<13}{_indent(value, 13)}")
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
@click.argument("name", metavar="FEED")
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

    result = pusher.send(ctx.client(), ctx.writable_ref(name, namespace), items, batch_size=max(batch_size, 1))
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
@click.argument("name", metavar="FEED")
@namespace_option
@click.option("--since", help="Events from this long ago, e.g. 15m, 1h, 7d.")
@click.option("--start", help="Inclusive start of event time (RFC 3339 or integer ns).")
@click.option("--end", help="Exclusive end of event time.")
@click.option("--as-of", help="Only what had been received by then: replays what was known at that moment.")
@click.option(
    "--as-of-lag", help="Each event as known this long before its own time, e.g. 24h (a forecast a day ahead)."
)
@click.option(
    "--as-of-basis", type=click.Choice(list(AS_OF_BASES)), default="received", show_default=True,
    help="With --as-of or --as-of-lag: what Isodrome had received, or what the source had published.",
)
@where_option
@column_option
@click.option("--limit", default=100, show_default=True, help="Most rows to return; 0 for all.")
@click.option("--payload", is_flag=True, help="Include the original JSON event (_payload).")
@click.option("--count", is_flag=True, help="Print only the number of matching events.")
@click.option("--payloads", is_flag=True,
              help="Print each event's original JSON, one per line (for scripts; like `isodrome-dev read --json`).")
@click.option("--at-position", help="Repeat an earlier query exactly: the position it printed.")
@click.option("--system", is_flag=True, help="In a table, also show _partition, _offset, _message_id, _receive_time.")
@_apply(dedupe_options)
@format_option
@pass_context
def feed_query(
    ctx: Context, name, namespace, since, start, end, as_of, as_of_lag, as_of_basis, filters, columns, limit, payload, count, payloads,
    at_position, system, dedupe, keep, dedupe_order, fmt,
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
    if as_of_lag:
        if "read.as_of_lag" not in ctx.client(require_key=False).server_info().capabilities:
            raise click.ClickException("this server does not support --as-of-lag (the Python SDK can do it locally)")
        request.as_of_lag_ns = _value(parse_duration, as_of_lag, "--as-of-lag")
    if as_of or as_of_lag:
        request.as_of_basis = AS_OF_BASES[as_of_basis]
    if at_position:
        request.at_position.CopyFrom(_value(parse_position, at_position, "--at-position"))
    if d := _dedupe(dedupe, keep, dedupe_order):
        request.dedupe.CopyFrom(d)
    if payloads:
        if count:
            raise click.UsageError("--payloads and --count are exclusive")
        request.include_payload = True
        request.columns[:] = ["_payload"]
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
        if payloads:
            for value in table.column("_payload").to_pylist():
                if value is not None:
                    click.echo(value)
            continue
        if not count:
            if limit:
                table = table.slice(0, max(limit - shown, 0))
            shown += table.num_rows
            if fmt == "table" and not columns and not system:
                table = _readable(table)
            printer.table(table)
    if count:
        click.echo(rows)
        return
    if payloads:
        if rows:
            _attribution(ctx, request.feed)
        return
    printer.finish("(no events)")
    if rows:
        _attribution(ctx, request.feed)
    if limit and rows > limit:
        click.echo(f"(first {limit} events; --limit to see more, --limit 0 for all)", err=True)
    if position is not None and fmt == "table":
        click.echo(f"position {format_position(position)} (--at-position to repeat this query exactly)", err=True)


@feed.command("tail")
@click.argument("name", metavar="FEED")
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
    dedupe, keep, dedupe_order, fmt,
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
    if d := _dedupe(dedupe, keep, dedupe_order):
        request.dedupe.CopyFrom(d)

    _attribution(ctx, request.feed)
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
@click.argument("name", metavar="FEED")
@namespace_option
@click.option("-k", "--key", "keys", multiple=True, help="Only this key. Repeatable.")
@column_option
@format_option
@pass_context
def feed_latest(ctx: Context, name, namespace, keys, columns, fmt) -> None:
    """Show the newest event per key."""
    response_ref = ctx.feed_ref(name, namespace)
    response = ctx.client().call(
        "Latest", pb.LatestRequest(feed=response_ref, keys=list(keys), columns=list(columns))
    )
    printer = output.Printer(fmt)
    table = output.decode(response.batch.ipc)
    printer.table(table)
    printer.finish("(no events)")
    if table is not None and table.num_rows:
        _attribution(ctx, response_ref)
