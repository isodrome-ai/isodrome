"""`connector …` and `connection …`: Isodrome-run downloaders that fill feeds from outside sources."""

from __future__ import annotations

import json

import click

from isodrome.cli.context import Context, namespace_option, pass_context
from isodrome.parse import format_ns
from isodrome.v1 import isodrome_pb2 as pb


@click.group()
def connector() -> None:
    """The kinds of connector Isodrome can run (templates)."""


@connector.command("templates")
@click.option("--details", is_flag=True, help="Show each template's options and feeds.")
@pass_context
def connector_templates(ctx: Context, details: bool) -> None:
    """List connector templates, the kinds of source Isodrome can download from."""
    templates = ctx.client().call("ListConnectorTemplates", pb.ListConnectorTemplatesRequest()).templates
    if not templates:
        click.echo("(no connector templates)")
    for t in templates:
        every = f"every {t.poll_interval_ms // 60_000} min" if t.poll_interval_ms >= 60_000 else ""
        click.echo(f"{click.style(t.name, bold=True)} (v{t.version}) {every}".rstrip())
        click.echo(f"  {t.description}")
        if details:
            if t.options_example:
                click.echo(f"  options: {t.options_example}")
            for cred in t.credentials:
                click.echo(f"  credential {cred.name}: {cred.description}")
            for f in t.feeds:
                click.echo(f"  feed {f.name}: {f.description}")
                if f.licence:
                    click.echo(f"    licence: {f.licence}")
                if f.attribution:
                    click.echo(f"    attribution: {f.attribution}")


@click.group()
def connection() -> None:
    """Run connectors: each connection fills feeds in a namespace from a source."""


@connection.command("create")
@click.argument("name")
@click.option("--template", required=True, help="See `iso connector templates`.")
@namespace_option
@click.option("--options", "options_json", default="", help="JSON options (default: the template's).")
@click.option("--paused", is_flag=True, help="Create it without starting it.")
@click.option(
    "--credentials", "credentials_file", type=click.File("r"),
    help="A JSON file (or - for stdin) with the source credentials the template needs.",
)
@pass_context
def connection_create(ctx: Context, name, template, namespace, options_json, paused, credentials_file) -> None:
    """Create a connection: it creates its feeds and a service account to write as, then runs
    (admin keys only). Templates for sources that need your own account list the credentials
    they need (`iso connector templates --details`)."""
    if options_json:
        try:
            json.loads(options_json)
        except ValueError as e:
            raise click.BadParameter(f"not JSON: {e}", param_hint="--options") from None
    c = ctx.client().call(
        "CreateConnection",
        pb.CreateConnectionRequest(
            name=name, template=template, namespace=ctx.namespace(namespace), options_json=options_json,
            paused=paused, credentials_json=_credentials(credentials_file),
        ),
    )
    _print_connection(c)


@connection.command("credentials")
@click.argument("name")
@click.option(
    "--from", "credentials_file", type=click.File("r"), required=True,
    help="A JSON file (or - for stdin) with the credentials; they are stored encrypted and never shown.",
)
@pass_context
def connection_credentials(ctx: Context, name, credentials_file) -> None:
    """Replace a connection's source credentials; it restarts with them (admin keys only)."""
    c = ctx.client().call(
        "SetConnectionCredentials",
        pb.SetConnectionCredentialsRequest(name=name, credentials_json=_credentials(credentials_file)),
    )
    click.echo(f"Set credentials of {c.name}: {', '.join(c.credential_fields) or '(none)'}.")


def _credentials(file) -> str:
    """Credentials come from a file or stdin, never the command line (where history keeps them)."""
    if file is None:
        return ""
    text = file.read()
    try:
        values = json.loads(text)
    except ValueError as e:
        raise click.BadParameter(f"not JSON: {e}", param_hint="credentials") from None
    if not isinstance(values, dict) or not all(isinstance(v, str) for v in values.values()):
        raise click.BadParameter('expected a JSON object of strings, e.g. {"api_key": "..."}', param_hint="credentials")
    return text


@connection.command("list")
@pass_context
def connection_list(ctx: Context) -> None:
    """List the organization's connections and how they are doing."""
    connections = ctx.client().call("ListConnections", pb.ListConnectionsRequest()).connections
    if not connections:
        click.echo("(no connections)")
    for c in connections:
        last = format_ns(c.last_event_at_ns) if c.last_event_at_ns else "never"
        click.echo(
            f"{c.name:<24} {_status(c):<20} {c.template:<32} ns={c.namespace:<12} "
            f"events={c.events_sent} last={last}"
        )


@connection.command("show")
@click.argument("name")
@pass_context
def connection_show(ctx: Context, name) -> None:
    """Show a connection: status, options, feeds and progress."""
    _print_connection(ctx.client().call("GetConnection", pb.GetConnectionRequest(name=name)))


@connection.command("pause")
@click.argument("name")
@pass_context
def connection_pause(ctx: Context, name) -> None:
    """Stop a connection until it is resumed (admin keys only)."""
    c = ctx.client().call("PauseConnection", pb.PauseConnectionRequest(name=name))
    click.echo(f"Paused {c.name}.")


@connection.command("resume")
@click.argument("name")
@pass_context
def connection_resume(ctx: Context, name) -> None:
    """Start a paused connection again (admin keys only)."""
    c = ctx.client().call("ResumeConnection", pb.ResumeConnectionRequest(name=name))
    click.echo(f"Resumed {c.name} ({c.status}).")


@connection.command("delete")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Do not ask for confirmation.")
@pass_context
def connection_delete(ctx: Context, name, yes) -> None:
    """Stop a connection and delete its service account; its feeds and their data stay."""
    if not yes:
        click.confirm(f"Delete connection {name}? (Its feeds and data stay.)", abort=True, err=True)
    ctx.client().call("DeleteConnection", pb.DeleteConnectionRequest(name=name))
    click.echo(f"Deleted connection {name}.")


def _status(c: pb.Connection) -> str:
    colour = {"running": "green", "failing": "red", "paused": "yellow"}.get(c.status)
    return click.style(c.status, fg=colour) if colour else c.status


def _print_connection(c: pb.Connection) -> None:
    rows = [
        ("connection", c.name),
        ("status", _status(c) + (f": {c.status_detail}" if c.status_detail else "")),
        ("template", c.template),
        ("namespace", c.namespace),
        ("feeds", ", ".join(f"{c.namespace}/{f}" for f in c.feeds) or "(none)"),
        ("options", c.options_json or "{}"),
        ("writes as", f"service account {c.service_account}"),
        ("credentials", (", ".join(c.credential_fields) + f" (set {format_ns(c.credentials_set_at_ns)})")
         if c.credential_fields else "(none)"),
        ("events sent", str(c.events_sent)),
        ("last event", format_ns(c.last_event_at_ns) if c.last_event_at_ns else "never"),
        ("heartbeat", format_ns(c.last_heartbeat_at_ns) if c.last_heartbeat_at_ns else "never"),
        ("worker", c.worker or "(none)"),
        ("cursor", c.cursor_json or "(start)"),
        ("created", format_ns(c.created_at_ns)),
    ]
    for label, value in rows:
        click.echo(f"{label + ':':<13}{value}")
