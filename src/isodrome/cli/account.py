"""Signing in and out, who you are, which server, and configuration profiles."""

from __future__ import annotations

import socket
import time
import webbrowser

import click
import grpc

from isodrome import login as device_flow
from isodrome.cli.context import Context, pass_context, warn_on_version_mismatch
from isodrome._transport import key_id
from isodrome.config import config_path
from isodrome.parse import format_ns, short_enum
from isodrome.v1 import isodrome_pb2 as pb


@click.command()
@click.option("--endpoint", "login_endpoint", help="Server to sign in to; saved in the profile.")
@click.option("--api-key", "login_key", help="Save this API key instead of signing in with the browser.")
@click.option("--no-browser", is_flag=True, help="Print the sign-in link instead of opening it.")
@click.option("--http", "http_base", help="The server's HTTP address for sign-in, if it reports none (local servers).")
@pass_context
def login(
    ctx: Context, login_endpoint: str | None, login_key: str | None, no_browser: bool, http_base: str | None
) -> None:
    """Sign in with your browser and save a personal API key.

    Signs in to the cloud by default. For a local server, which has no browser sign-in, pass
    its key: `iso --profile local login --endpoint http://localhost:7470 --api-key iso_...`.
    """
    if login_endpoint:
        ctx.endpoint_override = login_endpoint
    client = ctx.client(require_key=False)
    info = client.server_info()
    warn_on_version_mismatch(info)

    if login_key:
        api_key = login_key.strip()
        try:
            key_id(api_key)
        except ValueError as e:
            raise click.ClickException(str(e)) from None
    else:
        base = (http_base or info.public_url or client.endpoint.http_base()).rstrip("/")
        try:
            code = device_flow.start(base, f"iso on {socket.gethostname()}")
        except device_flow.Unavailable as e:
            raise click.ClickException(f"{e}; log in with an API key instead: iso login --api-key iso_...") from None
        except device_flow.LoginError as e:
            raise click.ClickException(f"sign-in failed: {e}") from None
        click.echo(f"Your code: {click.style(code.user_code, bold=True)}", err=True)
        if no_browser or not webbrowser.open(code.verification_uri_complete):
            click.echo(f"Open {code.verification_uri_complete} and check the code matches.", err=True)
        else:
            click.echo(f"Opened {code.verification_uri_complete}", err=True)
            click.echo("(check the code matches; if no browser opened, visit the link yourself)", err=True)
        click.echo("Waiting for you to sign in…", err=True)
        try:
            granted = device_flow.poll(base, code)
        except device_flow.LoginError as e:
            raise click.ClickException(f"sign-in failed: {e}") from None
        api_key = granted.api_key

    me = _whoami(ctx, api_key)
    profile = ctx.profile
    profile.endpoint = client.endpoint.url
    profile.api_key = api_key
    profile.namespace = None  # the new key's default namespace, until `iso namespace use`
    ctx.save()
    click.echo(
        f"Logged in as {_identity(me)} to {me.organization} at {client.endpoint.url} "
        f"(namespace {me.default_namespace}, role {short_enum(pb.Role, me.role)}; "
        f"{_credential(me.kind, me.expires_at_ns)})."
    )
    click.echo(f"Saved to {config_path()} (profile {ctx.profile_name}).", err=True)


def _identity(me: pb.WhoAmIResponse) -> str:
    if me.email:
        return me.email
    if me.service_account:
        return f"service account {me.service_account}"
    return f"key {me.key_id} (no owner)"


def _credential(kind: int, expires_at_ns: int) -> str:
    name = {pb.CREDENTIAL_KIND_SESSION: "session", pb.CREDENTIAL_KIND_API_KEY: "API key"}.get(kind, "key")
    if not expires_at_ns:
        return f"{name}, does not expire"
    days = (expires_at_ns - time.time_ns()) / 86_400e9
    when = format_ns(expires_at_ns)
    return f"{name}, expires {when}" + (f" (in {days:.0f} days)" if days >= 1 else "")


def _whoami(ctx: Context, api_key: str) -> pb.WhoAmIResponse:
    ctx.api_key_override = api_key
    ctx._client = None
    try:
        return ctx.client().call("WhoAmI", pb.WhoAmIRequest())
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            raise click.ClickException("the server refused that API key") from None
        raise


@click.command()
@click.option("--local-only", is_flag=True, help="Forget the key here without revoking it on the server.")
@pass_context
def logout(ctx: Context, local_only: bool) -> None:
    """Revoke this profile's API key on the server and forget it here."""
    profile = ctx.profile
    if not profile.api_key:
        click.echo(f"Not logged in (profile {ctx.profile_name}).")
        return
    if not local_only:
        ctx.api_key_override = profile.api_key
        try:
            ctx.client().call("RevokeApiKey", pb.RevokeApiKeyRequest(key_id=key_id(profile.api_key)))
        except grpc.RpcError as e:
            # A key the server no longer accepts is as good as revoked.
            if e.code() not in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.NOT_FOUND):
                raise click.ClickException(
                    f"could not revoke the key ({e.code().name}: {e.details()}); it is still saved. "
                    "Retry, or `iso logout --local-only` to forget it without revoking."
                ) from None
        except ValueError:
            pass  # not an Isodrome key: nothing to revoke
    profile.api_key = None
    ctx.save()
    click.echo("Logged out." if not local_only else "Forgot the key (it was not revoked).")


@click.command()
@pass_context
def whoami(ctx: Context) -> None:
    """Show who your API key belongs to, and its organization, namespace and role."""
    me = ctx.client().call("WhoAmI", pb.WhoAmIRequest())
    rows = [
        ("signed in as", _identity(me)),
        ("credential", _credential(me.kind, me.expires_at_ns)),
        ("organization", me.organization),
        ("default namespace", me.default_namespace),
        ("namespace in use", ctx.profile.namespace or me.default_namespace),
        ("role", short_enum(pb.Role, me.role)),
        ("key id", me.key_id),
        ("server", ctx.endpoint),
        ("profile", ctx.profile_name),
    ]
    for name, value in rows:
        click.echo(f"{name + ':':<19}{value}")


@click.command()
@pass_context
def server(ctx: Context) -> None:
    """Show the server's version, address and limits."""
    info = ctx.client(require_key=False).server_info()
    click.echo(f"endpoint:     {ctx.endpoint}")
    click.echo(f"version:      {info.version} {info.revision}".rstrip())
    click.echo(f"api:          {info.api_version}")
    click.echo(f"public url:   {info.public_url or '(not configured)'}")
    click.echo(f"max payload:  {info.max_payload_bytes} bytes")
    click.echo(f"dedupe:       {info.dedupe_window_ns // 1_000_000_000} s")
    warn_on_version_mismatch(info)


@click.group()
def profile() -> None:
    """Switch between servers and accounts (e.g. the cloud and a local stack)."""


@profile.command("list")
@pass_context
def profile_list(ctx: Context) -> None:
    """List profiles; * marks the current one."""
    if not ctx.config.profiles:
        click.echo("(no profiles yet: `iso login` creates one)")
    for name, p in sorted(ctx.config.profiles.items()):
        mark = "*" if name == ctx.config.current else " "
        state = "logged in" if p.api_key else "logged out"
        ns = f"  namespace {p.namespace}" if p.namespace else ""
        click.echo(f"{mark} {name:<16} {p.endpoint:<36} {state}{ns}")


@profile.command("use")
@click.argument("name")
@pass_context
def profile_use(ctx: Context, name: str) -> None:
    """Make NAME the current profile (created if new)."""
    ctx.config.profile(name)
    ctx.config.current = name
    ctx.save()
    click.echo(f"Using profile {name} ({ctx.config.profile(name).endpoint}).")


@profile.command("delete")
@click.argument("name")
@pass_context
def profile_delete(ctx: Context, name: str) -> None:
    """Delete profile NAME from this machine (its key is not revoked; `iso logout` first for that)."""
    if ctx.config.profiles.pop(name, None) is None:
        raise click.ClickException(f"no profile {name!r}")
    if ctx.config.current == name:
        ctx.config.current = "default"
    ctx.save()
    click.echo(f"Deleted profile {name}.")


account_commands = [login, logout, whoami, server, profile]
