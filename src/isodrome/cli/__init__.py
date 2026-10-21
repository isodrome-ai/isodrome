"""`iso`: the Isodrome command line."""

from __future__ import annotations

import os

# The CLI never uses gRPC across a fork, but opening a browser forks, and gRPC's fork handlers
# then log noise. Read when grpc is imported, so set first.
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")

import click  # noqa: E402
import grpc  # noqa: E402

from isodrome import __version__
from isodrome.cli.account import account_commands
from isodrome.cli.connector import connection, connector
from isodrome.cli.context import Context, Group, warn_on_version_mismatch
from isodrome.cli.feed import feed
from isodrome.cli.tenancy import key, namespace, service_account
from isodrome.cli.transformer import transformer
from isodrome._transport import API_VERSION, Transport
from isodrome.config import Config


def _print_version(ctx: click.Context, _param, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"iso {__version__} (API {API_VERSION})")
    # The server's version too, if the current profile's server answers quickly.
    params = ctx.params
    config = Config.load()
    endpoint = params.get("endpoint") or config.profile(params.get("profile")).endpoint
    try:
        with Transport(endpoint) as client:
            info = client.server_info(timeout=3)
        click.echo(f"server {info.version} (API {info.api_version}) at {endpoint}")
        warn_on_version_mismatch(info)
    except (grpc.RpcError, ValueError):
        click.echo(f"server at {endpoint}: not reachable")
    ctx.exit()


@click.group(cls=Group, context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-p", "--profile", envvar="ISODROME_PROFILE", is_eager=True, help="Configuration profile (default: the current one)."
)
@click.option("--endpoint", envvar="ISODROME_ENDPOINT", is_eager=True, help="Server URL, overriding the profile's.")
@click.option("--api-key", envvar="ISODROME_API_KEY", help="API key, overriding the profile's.")
@click.option(
    "--version", is_flag=True, expose_value=False, callback=_print_version, help="Show the client and server versions."
)
@click.pass_context
def cli(ctx: click.Context, profile: str | None, endpoint: str | None, api_key: str | None) -> None:
    """Isodrome: time-aware event feeds for trading.

    Start with `iso login`, then `iso feed create`, `iso feed push` and `iso feed query`.
    """
    context = Context(profile, endpoint, api_key)
    ctx.obj = context
    ctx.call_on_close(context.close)


for command in account_commands:
    cli.add_command(command)
cli.add_command(namespace)
cli.add_command(feed)
cli.add_command(key)
cli.add_command(service_account)
cli.add_command(connector)
cli.add_command(connection)
cli.add_command(transformer)


def main() -> None:
    cli(prog_name="iso")
