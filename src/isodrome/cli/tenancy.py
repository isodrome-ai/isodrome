"""`namespace …` and `key …`: an organization's namespaces and API keys."""

from __future__ import annotations

import click

from isodrome import output
from isodrome.cli.context import Context, pass_context
from isodrome.parse import format_ns, now_ns, short_enum
from isodrome.v1 import isodrome_pb2 as pb

ROLES = {"admin": pb.ROLE_ADMIN, "writer": pb.ROLE_WRITER, "reader": pb.ROLE_READER}


@click.group()
def namespace() -> None:
    """Create, list, publish, delete and choose namespaces."""


@namespace.command("create")
@click.argument("name")
@click.option("--public", is_flag=True, help="Readable from every organization (where the server allows it).")
@pass_context
def namespace_create(ctx: Context, name: str, public: bool) -> None:
    """Create a namespace (admin keys only)."""
    ns = ctx.client().call("CreateNamespace", pb.CreateNamespaceRequest(name=name, public=public))
    click.echo(f"Created namespace {ns.name}{' (public)' if ns.public else ''}.")


@namespace.command("list")
@click.option("--mine", is_flag=True, help="Only your organization's namespaces.")
@pass_context
def namespace_list(ctx: Context, mine: bool) -> None:
    """List your organization's namespaces, then other organizations' public ones.

    * marks the one in use. ACCESS is `org` (your organization only), `public` (everyone can
    read it; yours to change) or `public, read-only` (another organization's).
    """
    client = ctx.client()
    me = ctx.me()
    in_use = ctx.profile.namespace or me.default_namespace
    namespaces = list(client.call("ListNamespaces", pb.ListNamespacesRequest()).namespaces)
    if not mine:
        namespaces += [
            n for n in client.call("ListNamespaces", pb.ListNamespacesRequest(public=True)).namespaces
            if n.organization != me.organization
        ]
    rows = []
    for n in namespaces:
        ref = ctx.display_ref(n.organization, n.name)
        ours = n.organization in ("", me.organization)
        rows.append({
            "": "*" if ref == in_use else "",
            "namespace": ref,
            "access": "org" if not n.public else "public" if ours else "public, read-only",
            "created": format_ns(n.created_at_ns)[:10],
        })
    output.Printer("table").rows(rows, ["", "namespace", "access", "created"])


@namespace.command("update")
@click.argument("name")
@click.option("--public/--private", default=None, help="Readable from every organization, or only from yours.")
@pass_context
def namespace_update(ctx: Context, name: str, public: bool | None) -> None:
    """Publish a namespace to every organization, or make it private again (admin keys only)."""
    if public is None:
        raise click.UsageError("give --public or --private")
    request = pb.UpdateNamespaceRequest(name=name)
    request.public = public
    ns = ctx.client().call("UpdateNamespace", request)
    click.echo(f"Namespace {ns.name} is now {'public: readable from every organization' if ns.public else 'private'}.")


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
    """Act on namespace NAME from now on (in this profile).

    NAME may be ORGANIZATION/NAME, another organization's public namespace: its feeds can then
    be read by their names alone.
    """
    if reset or not name:
        if not reset:
            raise click.UsageError("give a namespace, or --default")
        ctx.profile.namespace = None
        ctx.save()
        click.echo("Using your key's default namespace.")
        return
    client = ctx.client()
    organization, _, ns = name.rpartition("/")
    if organization and organization != ctx.me().organization:
        known = [
            f"{n.organization}/{n.name}"
            for n in client.call("ListNamespaces", pb.ListNamespacesRequest(public=True)).namespaces
        ]
        kind = "public namespace"
    else:
        name = ns
        known = [n.name for n in client.call("ListNamespaces", pb.ListNamespacesRequest()).namespaces]
        kind = "namespace"
    if name not in known:
        raise click.ClickException(f"no {kind} {name!r}; there are: {', '.join(known) or '(none)'}")
    ctx.profile.namespace = name
    ctx.save()
    click.echo(f"Using namespace {name}{' (read-only)' if organization and kind == 'public namespace' else ''}.")


@click.group()
def key() -> None:
    """Create, list and revoke API keys, e.g. for scripts and services."""


@key.command("create")
@click.option("--role", type=click.Choice(list(ROLES)), required=True, help="For a personal key: at most yours.")
@click.option("--name", default="", help='A label, e.g. "laptop" or "ingest-bot".')
@click.option(
    "-n", "--namespace", default=None, help="Namespace the key uses when a request names none (default: the one in use)."
)
@click.option(
    "--service-account", help="A key for this service account, acting as it (admins only); e.g. for CI."
)
@click.option(
    "--organization", "organization_key", is_flag=True,
    help="An organization key with a fixed role, owned by no one (admins only).",
)
@pass_context
def key_create(
    ctx: Context, role: str, name: str, namespace: str, service_account: str | None, organization_key: bool
) -> None:
    """Create an API key and print it (shown only once).

    By default the key is personal: it acts as you, with at most --role, so it follows your
    membership and stops working if you leave the organization. For software that runs on its
    own, prefer a service account's key (--service-account).
    """
    if service_account and organization_key:
        raise click.UsageError("--service-account and --organization are exclusive")
    created = ctx.client().call(
        "CreateApiKey",
        pb.CreateApiKeyRequest(
            role=ROLES[role],
            default_namespace=ctx.namespace(namespace),
            name=name,
            personal=not (organization_key or service_account),
            service_account=service_account or "",
        ),
    )
    _print_key(created.key)
    click.echo(f"api key: {created.api_key}")
    click.echo("(shown only once: store it now)", err=True)


@key.command("list")
@pass_context
def key_list(ctx: Context) -> None:
    """List keys and sessions, revoked ones included (admins: the organization's; others: your own).
    * marks the one in use."""
    client = ctx.client()
    current = client.call("WhoAmI", pb.WhoAmIRequest()).key_id
    for k in client.call("ListApiKeys", pb.ListApiKeysRequest()).keys:
        _print_key(k, current=k.key_id == current)


@key.command("revoke")
@click.argument("key_id")
@pass_context
def key_revoke(ctx: Context, key_id: str) -> None:
    """Revoke a key or session by its id; it stops working immediately."""
    _print_key(ctx.client().call("RevokeApiKey", pb.RevokeApiKeyRequest(key_id=key_id)))


def _print_key(k: pb.ApiKey, current: bool = False) -> None:
    kind = {pb.CREDENTIAL_KIND_SESSION: "session", pb.CREDENTIAL_KIND_API_KEY: "api key"}.get(k.kind, "key")
    if k.revoked:
        state = "REVOKED"
    elif k.expires_at_ns and k.expires_at_ns < now_ns():
        state = "expired"
    else:
        state = "active"
    expires = f"  expires {format_ns(k.expires_at_ns)[:10]}" if k.expires_at_ns else ""
    click.echo(
        f"{'*' if current else ' '} {k.key_id:<14} {kind:<8} {short_enum(pb.Role, k.role):<7} {state:<8} "
        f"{(k.owner or '(organization)'):<24} ns={k.default_namespace:<12} "
        f"created {format_ns(k.created_at_ns)[:10]}{expires}  {k.name}".rstrip()
    )


@click.group("service-account")
def service_account() -> None:
    """Identities for software, which cannot sign in and hold API keys (admin keys only)."""


@service_account.command("create")
@click.argument("name")
@click.option("--role", type=click.Choice(list(ROLES)), required=True)
@pass_context
def service_account_create(ctx: Context, name: str, role: str) -> None:
    """Create a service account; then `iso key create --service-account NAME` gives it a key."""
    sa = ctx.client().call("CreateServiceAccount", pb.CreateServiceAccountRequest(name=name, role=ROLES[role]))
    click.echo(f"Created service account {sa.name} ({short_enum(pb.Role, sa.role)}).")
    click.echo(f"Give it a key: iso key create --service-account {sa.name} --role {short_enum(pb.Role, sa.role)}",
               err=True)


@service_account.command("list")
@pass_context
def service_account_list(ctx: Context) -> None:
    """List the organization's service accounts."""
    accounts = ctx.client().call("ListServiceAccounts", pb.ListServiceAccountsRequest()).service_accounts
    if not accounts:
        click.echo("(no service accounts)")
    for sa in accounts:
        click.echo(f"{sa.name:<32} {short_enum(pb.Role, sa.role):<7} created {format_ns(sa.created_at_ns)[:10]}")


@service_account.command("delete")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Do not ask for confirmation.")
@pass_context
def service_account_delete(ctx: Context, name: str, yes: bool) -> None:
    """Delete a service account, revoking all its keys at once."""
    if not yes:
        click.confirm(f"Delete service account {name} and revoke its keys?", abort=True, err=True)
    ctx.client().call("DeleteServiceAccount", pb.DeleteServiceAccountRequest(name=name))
    click.echo(f"Deleted service account {name}; its keys no longer work.")
