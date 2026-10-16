"""What every command shares: the chosen profile, the connection, and error reporting."""

from __future__ import annotations

import os

import click
import grpc

from isodrome._transport import API_VERSION, Transport
from isodrome.config import Config, Profile
from isodrome.v1 import isodrome_pb2 as pb

# Hints for errors a person can do something about.
_HINTS = {
    grpc.StatusCode.UNAUTHENTICATED: "your credential is missing, revoked or expired; run `iso login`",
    grpc.StatusCode.PERMISSION_DENIED: "your key's role does not allow this (see `iso whoami`)",
}


class Context:
    def __init__(self, profile: str | None, endpoint: str | None, api_key: str | None):
        self.config = Config.load()
        self.profile_name = profile or self.config.current
        self.endpoint_override = endpoint
        self.api_key_override = api_key
        self._client: Transport | None = None
        self._me: pb.WhoAmIResponse | None = None

    @property
    def profile(self) -> Profile:
        return self.config.profile(self.profile_name)

    @property
    def endpoint(self) -> str:
        return self.endpoint_override or self.profile.endpoint

    @property
    def api_key(self) -> str | None:
        return self.api_key_override or self.profile.api_key

    def client(self, require_key: bool = True) -> Transport:
        if require_key and not self.api_key:
            raise click.ClickException(
                f"not logged in (profile {self.profile_name!r}); run `iso login`"
                + (f" --profile {self.profile_name}" if self.profile_name != self.config.current else "")
            )
        if self._client is None:
            try:
                self._client = Transport(self.endpoint, self.api_key)
            except ValueError as e:
                raise click.ClickException(str(e)) from None
        return self._client

    def me(self) -> pb.WhoAmIResponse:
        if self._me is None:
            self._me = self.client().call("WhoAmI", pb.WhoAmIRequest())
        return self._me

    def scope(self, explicit: str | None) -> tuple[str, str]:
        """(organization, namespace) a command acts on: `--namespace`, else `iso namespace use`'s
        choice, else ("", "") (your organization; the credential's default namespace). Either may
        be `org/namespace`: another organization's public namespace."""
        text = explicit or self.profile.namespace or ""
        organization, _, namespace = text.rpartition("/")
        return organization, namespace

    def namespace(self, explicit: str | None) -> str:
        """The namespace in your own organization a command acts on ("": the default one)."""
        organization, namespace = self.scope(explicit)
        return "" if organization else namespace

    def feed_ref(self, ref: str, namespace: str | None) -> pb.FeedRef:
        """`feed`, `namespace/feed` or `organization/namespace/feed` → a FeedRef."""
        parts = ref.split("/")
        if len(parts) > 3 or not all(parts):
            raise click.BadParameter(f"{ref!r}: expected FEED, NAMESPACE/FEED or ORGANIZATION/NAMESPACE/FEED")
        if len(parts) > 1 and namespace:
            raise click.UsageError(f"{ref!r} names its namespace already; leave out --namespace")
        if len(parts) == 3:
            return pb.FeedRef(organization=parts[0], namespace=parts[1], name=parts[2])
        if len(parts) == 2:
            return pb.FeedRef(namespace=parts[0], name=parts[1])
        organization, ns = self.scope(namespace)
        return pb.FeedRef(organization=organization, namespace=ns, name=ref)

    def writable_ref(self, ref: str, namespace: str | None) -> pb.FeedRef:
        """A FeedRef for a change, which only your own organization's feeds allow."""
        feed = self.feed_ref(ref, namespace)
        if feed.organization:
            if feed.organization != self.me().organization:
                raise click.ClickException(
                    f"{feed.organization}/{feed.namespace}/{feed.name} belongs to another organization: "
                    "its public feeds can be read, but not changed"
                )
            feed.organization = ""
        return feed

    def display_ref(self, organization: str, namespace: str, name: str = "") -> str:
        """How to refer to a namespace or feed from here: `namespace[/feed]` in your
        organization, `organization/namespace[/feed]` in another."""
        prefix = "" if organization in ("", self.me().organization) else f"{organization}/"
        return prefix + namespace + (f"/{name}" if name else "")

    def save(self) -> None:
        self.config.save()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


def warn_on_version_mismatch(info: pb.ServerInfo) -> None:
    if info.api_version and info.api_version != API_VERSION:
        click.secho(
            f"warning: the server speaks API {info.api_version}, this client {API_VERSION}; "
            "upgrade with `pipx upgrade isodrome`",
            fg="yellow",
            err=True,
        )


def rpc_error_message(e: grpc.RpcError) -> str:
    code = e.code()
    details = e.details() or ""
    if code == grpc.StatusCode.UNAVAILABLE and ("connect" in details.lower() or "dns" in details.lower()):
        return f"cannot reach the server: {details}"
    message = f"{code.name}: {details}"
    if hint := _HINTS.get(code):
        message += f"\n  ({hint})"
    return message


class Group(click.Group):
    """Reports gRPC errors as one line instead of a traceback."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except grpc.RpcError as e:
            if os.environ.get("ISODROME_DEBUG"):
                raise
            raise click.ClickException(rpc_error_message(e)) from None
        except KeyboardInterrupt:
            raise click.exceptions.Exit(130) from None


pass_context = click.make_pass_decorator(Context)

namespace_option = click.option(
    "-n", "--namespace", default=None,
    help="Namespace (default: `iso namespace use`, else your key's default); ORGANIZATION/NAME for another's public one.",
)
