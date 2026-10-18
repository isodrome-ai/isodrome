"""The SDK's entry point: `iso.connect()`, then feeds."""

from __future__ import annotations

import html
import os
from typing import TYPE_CHECKING

from isodrome import errors
from isodrome._transport import Transport
from isodrome.config import Config
from isodrome._feed import Feed, FeedList
from isodrome.parse import feed_ref, format_ns, short_enum
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
        organization, _, ns = self._namespace.rpartition("/")
        return feed_ref(ref, organization, ns)

    # ----- transformers -----

    def transformers(self):
        """The organization's transformers, as a DataFrame."""
        import pandas as pd

        listed = errors.call(self._transport.call, "ListTransformers", pb.ListTransformersRequest()).transformers
        return pd.DataFrame([{
            "transformer": f"{t.namespace}/{t.name}", "version": t.version, "status": t.status,
            "stateful": t.stateful, "backfill_remaining": t.stats.backfill_remaining,
            "events_in": t.events_in, "events_out": t.events_out, "errors": t.errors,
        } for t in listed])

    def transformer(self, name: str, namespace: str | None = None) -> TransformerInfo:
        t = errors.call(self._transport.call, "GetTransformer", pb.GetTransformerRequest(
            transformer=pb.TransformerRef(namespace=namespace or "", name=name)))
        return TransformerInfo(self, t)

    def deploy_transformer(self, path=".", *, name: str = "", namespace: str = "", state: bool = False,
                           test: bool = False, wait: bool = True, progress: bool = True, **overrides):
        """Deploys a project (a directory whose code declares transformers) or one .py file, and
        waits: through the build's phases (verifying a stateful transformer replays its whole
        history, so this can take minutes), then through its backfill until it is live.
        `test=True` builds and verifies without deploying. Overrides: python, triggers,
        dependencies, windows, output, key, time, publication_time, entrypoint, basis,
        on_restart, paused, max_error_rate, sample_events, allow_unverified.

        Returns the build (`.status`, `.report_json`); raises if it did not become ready."""
        from isodrome import deploy

        say = _say(progress)
        o = deploy.Overrides(name=name, namespace=namespace, state=state, **overrides)
        build = deploy.start(self._transport, path, o, validate_only=test, on_message=say)
        say(f"build {build.id} {build.status}")
        if not wait:
            return build
        build = deploy.wait_for_build(
            self._transport, build,
            on_phase=lambda b, s: say(f"  {s:>6.1f} s  {b.status}"),
            on_tick=lambda b, s: say(f"  {s:>6.1f} s  still {b.status}"),
        )
        for line in deploy.describe_build(build):
            say(line)
        if build.status != "ready":
            raise errors.FailedPrecondition(f"{build.status}: {build.status_detail or 'see the report'}")
        if not test and not o.paused:
            seen = {"n": None}

            def on_progress(t, s):
                n = t.stats.backfill_remaining
                if n and n != seen["n"]:
                    say(f"  {s:>6.1f} s  backfill: {n:,} trigger events to replay")
                    seen["n"] = n

            t = deploy.wait_for_backfill(self._transport, build, on_progress=on_progress)
            say(f"{t.name} v{t.version} is live")
        return build

    def test_transformer(self, path=".", **options):
        """Builds and verifies a project like deploy_transformer, without deploying it."""
        return self.deploy_transformer(path, test=True, **options)

    def run_transformer(self, name: str, start, end, *, into: str = "", namespace: str = "",
                        wait: bool = True, progress: bool = True) -> pb.TransformerRun:
        """A backtest: the triggers' events with event time in [start, end), replayed exactly as
        live saw them (a stateful transformer's state warmed up from the first trigger event),
        into `into` (default NAME_run). Waits for it unless `wait=False`; read the result with
        `iso.feed(run.output...)` or `client.feed(...)`."""
        import time as _time

        from isodrome.parse import to_ns

        say = _say(progress)
        run = errors.call(self._transport.call, "StartTransformerRun", pb.StartTransformerRunRequest(
            transformer=pb.TransformerRef(namespace=namespace, name=name),
            start_ns=to_ns(start), end_ns=to_ns(end), into=into))
        last = None
        while wait and run.status not in ("done", "failed", "cancelled"):
            _time.sleep(1)
            run = errors.call(self._transport.call, "GetTransformerRun", pb.GetTransformerRunRequest(id=run.id))
            if (run.status, round(run.progress, 2)) != last:
                say(f"  run {run.status} {run.progress * 100:5.1f}%  {run.events_in:,} in, {run.events_out:,} out")
                last = (run.status, round(run.progress, 2))
        if wait and run.status != "done":
            raise errors.FailedPrecondition(f"run {run.status}: {run.status_detail}")
        return run

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


# ---------- Transformers ----------


class TransformerInfo:
    """A deployed transformer, as last fetched (`refresh()` fetches again)."""

    def __init__(self, client: Client, t: pb.Transformer):
        self._client = client
        self._t = t

    name = property(lambda self: self._t.name)
    namespace = property(lambda self: self._t.namespace)
    version = property(lambda self: self._t.version)
    status = property(lambda self: self._t.status)
    stateful = property(lambda self: self._t.stateful)
    stats = property(lambda self: self._t.stats)
    backfill_remaining = property(lambda self: self._t.stats.backfill_remaining)
    proto = property(lambda self: self._t)

    @property
    def output(self) -> str:
        """The feed it writes, as a reference for `iso.feed(...)`."""
        p = self._t.output.pinned
        return f"{p.organization}/{p.namespace}/{p.name}" if p.organization else f"{p.namespace}/{p.name}"

    def refresh(self) -> TransformerInfo:
        self._t = errors.call(self._client._transport.call, "GetTransformer", pb.GetTransformerRequest(
            transformer=pb.TransformerRef(namespace=self._t.namespace, name=self._t.name)))
        return self

    def run(self, start, end, into: str = "", wait: bool = True, progress: bool = True):
        """A backtest over trigger events with event time in [start, end); see Client.run_transformer."""
        return self._client.run_transformer(self.name, start, end, into=into, namespace=self.namespace,
                                            wait=wait, progress=progress)

    def __repr__(self) -> str:
        from isodrome.deploy import describe_transformer

        return "\n".join(describe_transformer(self._t))


def _say(enabled: bool):
    import sys

    return (lambda text: print(text, file=sys.stderr, flush=True)) if enabled else (lambda text: None)


