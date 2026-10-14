"""`namespace …` and `key …`: an organization's namespaces and API keys."""

from __future__ import annotations

import click

from isodrome.cli.context import Context, pass_context
from isodrome.parse import format_ns, short_enum
from isodrome.v1 import isodrome_pb2 as pb

ROLES = {"admin": pb.ROLE_ADMIN, "writer": pb.ROLE_WRITER, "reader": pb.ROLE_READER}


@click.group()
def namespace() -> None:
    """Create, list, delete and choose namespaces."""


@namespace.command("create")
@click.argument("name")
@pass_context
def namespace_create(ctx: Context, name: str) -> None:
    """Create a namespace (admin keys only)."""
    ns = ctx.client().call("CreateNamespace", pb.CreateNamespaceRequest(name=name))
    click.echo(f"Created namespace {ns.name}.")


@namespace.command("list")
@pass_context
def namespace_list(ctx: Context) -> None:
    """List your organization's namespaces; * marks the one in use."""
    client = ctx.client()
    current = ctx.profile.namespace or client.call("WhoAmI", pb.WhoAmIRequest()).default_namespace
    for ns in client.call("ListNamespaces", pb.ListNamespacesRequest()).namespaces:
        mark = "*" if ns.name == current else " "
        click.echo(f"{mark} {ns.name:<24} created {format_ns(ns.created_at_ns)}")


@namespace.command("delete")
@click.argument("name")
@pass_context
def namespace_delete(ctx: Context, name: str) -> None:
    """Delete an empty namespace (admin keys only)."""
    ctx.client().call("DeleteNamespace", pb.DeleteNamespaceRequest(name=name))
    if ctx.profile.namespace == name:
        ctx.profile.namespace = None
        ctx.save()
    click.echo(f"Deleted namespace {name}.")


@namespace.command("use")
@click.argument("name", required=False)
@click.option("--default", "reset", is_flag=True, help="Go back to your key's default namespace.")
@pass_context
def namespace_use(ctx: Context, name: str | None, reset: bool) -> None:
    """Act on namespace NAME from now on (in this profile)."""
    if reset or not name:
        if not reset:
            raise click.UsageError("give a namespace, or --default")
        ctx.profile.namespace = None
        ctx.save()
        click.echo("Using your key's default namespace.")
        return
    names = [ns.name for ns in ctx.client().call("ListNamespaces", pb.ListNamespacesRequest()).namespaces]
    if name not in names:
        raise click.ClickException(f"no namespace {name!r}; there are: {', '.join(names) or '(none)'}")
    ctx.profile.namespace = name
    ctx.save()
    click.echo(f"Using namespace {name}.")


@click.group()
def key() -> None:
    """Create, list and revoke API keys (admin keys only)."""


@key.command("create")
@click.option("--role", type=click.Choice(list(ROLES)), required=True)
@click.option("--name", default="", help='A label, e.g. "laptop" or "ingest-bot".')
@click.option("-n", "--namespace", default="", help="Namespace used when a request names none (default: yours).")
@pass_context
def key_create(ctx: Context, role: str, name: str, namespace: str) -> None:
    """Create an API key and print it (shown only once)."""
    created = ctx.client().call(
        "CreateApiKey", pb.CreateApiKeyRequest(role=ROLES[role], default_namespace=namespace, name=name)
    )
    _print_key(created.key)
    click.echo(f"api key: {created.api_key}")
    click.echo("(shown only once: store it now)", err=True)


@key.command("list")
@pass_context
def key_list(ctx: Context) -> None:
    """List your organization's keys (never their secrets)."""
    for k in ctx.client().call("ListApiKeys", pb.ListApiKeysRequest()).keys:
        _print_key(k)


@key.command("revoke")
@click.argument("key_id")
@pass_context
def key_revoke(ctx: Context, key_id: str) -> None:
    """Revoke a key by its id; it stops working immediately."""
    _print_key(ctx.client().call("RevokeApiKey", pb.RevokeApiKeyRequest(key_id=key_id)))


def _print_key(k: pb.ApiKey) -> None:
    click.echo(
        f"{k.key_id:<14} {short_enum(pb.Role, k.role):<7} ns={k.default_namespace:<16} "
        f"{'REVOKED' if k.revoked else 'active':<8} created {format_ns(k.created_at_ns)}  {k.name}".rstrip()
    )
