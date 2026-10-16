"""The SDK's entry point: `iso.connect()`, then feeds."""

from __future__ import annotations

import html
import os
from typing import TYPE_CHECKING

from isodrome import errors
from isodrome._transport import Transport
from isodrome.config import Config
from isodrome._feed import Feed, FeedList
from isodrome.parse import format_ns, short_enum
from isodrome.v1 import isodrome_pb2 as pb

if TYPE_CHECKING:
    import pandas as pd

_TIME_UNITS = {"s": pb.TIME_UNIT_SECONDS, "ms": pb.TIME_UNIT_MILLISECONDS, "us": pb.TIME_UNIT_MICROSECONDS,
               "ns": pb.TIME_UNIT_NANOSECONDS}


def connect(profile: str | None = None, *, api_key: str | None = None, endpoint: str | None = None) -> Client:
    """A connection to Isodrome.

    By default it uses what `iso login` saved (the current profile, or `profile`), so a notebook
    needs no key in it. `api_key` and `endpoint` (or ISODROME_API_KEY, ISODROME_ENDPOINT,
    ISODROME_PROFILE) override it, e.g. for a service account in CI.
    """
    config = Config.load()
    name = profile or os.environ.get("ISODROME_PROFILE") or config.current
    saved = config.profile(name)
    endpoint = endpoint or os.environ.get("ISODROME_ENDPOINT") or saved.endpoint
    api_key = api_key or os.environ.get("ISODROME_API_KEY") or saved.api_key
    if not api_key:
        raise errors.Unauthenticated(f"not logged in (profile {name!r}): run `iso login`, or pass api_key=")
    return Client(Transport(endpoint, api_key), namespace=saved.namespace, profile=name)


class Client:
    """A connection to Isodrome: find feeds, then query them."""

    def __init__(self, transport: Transport, namespace: str | None = None, profile: str | None = None):
        self._transport = transport
        self._namespace = namespace or ""  # `iso namespace use`: NAME or ORG/NAME
        self.profile = profile
        self._me: pb.WhoAmIResponse | None = None
        self._capabilities: frozenset[str] | None = None

    @property
    def endpoint(self) -> str:
        return self._transport.endpoint.url

    def whoami(self) -> pb.WhoAmIResponse:
        """Who this connection acts as: email (or service account), organization, role, expiry."""
        if self._me is None:
            self._me = errors.call(self._transport.call, "WhoAmI", pb.WhoAmIRequest())
        return self._me

    @property
    def capabilities(self) -> frozenset[str]:
        """Features the server has beyond the base API (e.g. "read.as_of_lag", "lookup"). The SDK
        uses each only where it exists, and does the same work locally otherwise."""
        if self._capabilities is None:
            self._capabilities = frozenset(errors.call(self._transport.server_info).capabilities)
        return self._capabilities

    @property
    def organization(self) -> str:
        return self.whoami().organization

    # ----- feeds -----

    def feed(self, ref: str) -> Feed:
        """A feed: "FEED" (in the namespace in use), "NAMESPACE/FEED", or
        "ORGANIZATION/NAMESPACE/FEED" (another organization's public feeds)."""
        feed_ref = self._ref(ref)
        meta = errors.call(self._transport.call, "GetFeed", pb.GetFeedRequest(feed=feed_ref))
        return Feed(self, meta, feed_ref)

    def feeds(self, *, public: bool | None = None, mine: bool = False, namespace: str | None = None) -> FeedList:
        """The feeds you can read: your organization's (every namespace), then other
        organizations' public ones. `public=True` for public ones only, `mine=True` for your
        organization's only, `namespace="NAME"` (or "ORG/NAME") for one namespace."""
        me = self.whoami()
        if namespace:
            organization, _, ns = namespace.rpartition("/")
            places = [(organization, ns)]
        else:
            places = [("", n.name) for n in errors.call(
                self._transport.call, "ListNamespaces", pb.ListNamespacesRequest()).namespaces]
            if not mine:
                places += [(n.organization, n.name) for n in errors.call(
                    self._transport.call, "ListNamespaces", pb.ListNamespacesRequest(public=True)).namespaces
                    if n.organization != me.organization]
        feeds = FeedList()
        for organization, ns in places:
            listed = errors.call(
                self._transport.call, "ListFeeds", pb.ListFeedsRequest(organization=organization, namespace=ns)
            )
            for meta in listed.feeds:
                if public is not None and meta.public != public:
                    continue
                ref = pb.FeedRef(organization=meta.organization, namespace=meta.namespace, name=meta.name)
                feeds.append(Feed(self, meta, ref, complete=False))
        return feeds

    def namespaces(self, *, mine: bool = False) -> pd.DataFrame:
        """Your organization's namespaces, then other organizations' public ones."""
        import pandas as pd

        me = self.whoami()
        found = list(errors.call(self._transport.call, "ListNamespaces", pb.ListNamespacesRequest()).namespaces)
        if not mine:
            found += [n for n in errors.call(self._transport.call, "ListNamespaces",
                                             pb.ListNamespacesRequest(public=True)).namespaces
                      if n.organization != me.organization]
        return pd.DataFrame([{
            "organization": n.organization or me.organization,
            "namespace": n.name,
            "public": n.public,
            "created": pd.Timestamp(n.created_at_ns, unit="ns", tz="UTC"),
        } for n in found])

    def create_feed(
        self,
        name: str,
        *,
        key: str | None = None,
        time_field: str | None = None,
        time_unit: str | None = None,
        publication_time_field: str | None = None,
        description: str = "",
        licence: str = "",
        attribution: str = "",
        source_url: str = "",
        ack: str = "replicated",
        partitions: int | None = None,
    ) -> Feed:
        """Create a feed in your organization: "FEED" (namespace in use) or "NAMESPACE/FEED".

        Events are timed when they arrive unless `time_field` names a field holding their own
        time. `key` makes `latest()` give the newest event per value of that field."""
        ref = self._ref(name)
        if ref.organization and ref.organization != self.organization:
            raise errors.PermissionDenied(f"{name}: feeds can only be created in your own organization")
        ref.organization = ""
        if time_unit and not time_field:
            time_field = "event_time"
        request = pb.CreateFeedRequest(
            feed=ref,
            time_field=time_field or "",
            arrival_time=not time_field,
            time_unit=_TIME_UNITS[time_unit] if time_unit else pb.TIME_UNIT_UNSPECIFIED,
            ack_mode=pb.ACK_MODE_NONE if ack == "none" else pb.ACK_MODE_REPLICATED,
            description=description,
            licence=licence,
            attribution=attribution,
            source_url=source_url,
        )
        if key is not None:
            request.key_field = key
        if partitions is not None:
            request.partitions = partitions
        if publication_time_field:
            request.publication_time_field = publication_time_field
        meta = errors.call(self._transport.call, "CreateFeed", request)
        return Feed(self, meta, pb.FeedRef(namespace=meta.namespace, name=meta.name))

    def _ref(self, ref: str) -> pb.FeedRef:
        parts = ref.split("/")
        if len(parts) > 3 or not all(parts):
            raise ValueError(f"{ref!r}: expected FEED, NAMESPACE/FEED or ORGANIZATION/NAMESPACE/FEED")
        if len(parts) == 3:
            return pb.FeedRef(organization=parts[0], namespace=parts[1], name=parts[2])
        if len(parts) == 2:
            return pb.FeedRef(namespace=parts[0], name=parts[1])
        organization, _, ns = self._namespace.rpartition("/")
        return pb.FeedRef(organization=organization, namespace=ns, name=ref)

    # ----- lifecycle and display -----

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _identity(self) -> list[tuple[str, str]]:
        me = self.whoami()
        who = me.email or (f"service account {me.service_account}" if me.service_account else f"key {me.key_id}")
        expires = format_ns(me.expires_at_ns) if me.expires_at_ns else "never"
        return [
            ("signed in as", who),
            ("organization", me.organization),
            ("role", short_enum(pb.Role, me.role)),
            ("namespace", self._namespace or me.default_namespace),
            ("server", self.endpoint),
            ("expires", expires),
        ]

    def __repr__(self) -> str:
        try:
            details = ", ".join(f"{k} {v}" for k, v in self._identity()[:3])
        except errors.IsodromeError as e:
            details = f"not working: {e}"
        return f"<isodrome.Client {self.endpoint}: {details}>"

    def _repr_html_(self) -> str:
        rows = "".join(f"<tr><th style='text-align:left;padding-right:1em'>{html.escape(k)}</th>"
                       f"<td style='text-align:left'>{html.escape(v)}</td></tr>" for k, v in self._identity())
        return f"<table>{rows}</table>"
