"""In-process stand-ins for the server: a gRPC Isodrome service and the sign-in HTTP endpoints."""

from __future__ import annotations

import json
import threading
from concurrent import futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import grpc
import pyarrow as pa

from isodrome.v1 import isodrome_pb2 as pb
from isodrome.v1 import isodrome_pb2_grpc as pb_grpc

KEY = "iso_testkey_SECRETsecretSECRETsecret0"
SESSION_EXPIRES_NS = 4_102_444_800 * 10**9  # 2100-01-01


def ipc(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()


class FakeIsodrome(pb_grpc.IsodromeServicer):
    """Just enough of the API for the CLI: one org, feeds, and events kept in a list.
    Events must be JSON objects with a "price" field (else rejected as MISSING_KEY)."""

    def __init__(self):
        self.namespaces = ["default"]
        self.public_namespaces: set[str] = set()
        self.service_accounts: list[pb.ServiceAccount] = []
        self.connections: list[pb.Connection] = []
        self.requests: list[str] = []
        self.capabilities: list[str] = []
        self.role = pb.ROLE_ADMIN
        self._init_transformers()
        self.estimate = (0, 0)
        self.feeds: dict[tuple[str, str], pb.Feed] = {}
        self.events: dict[tuple[str, str], list[tuple[int, dict]]] = {}
        self.seen_ids: set[str] = set()
        self.revoked: set[str] = set()
        self.keys: list[pb.ApiKey] = []
        self.send_requests = 0
        self.last_read: pb.ReadRequest | None = None

    def _auth(self, context):
        metadata = dict(context.invocation_metadata())
        auth = metadata.get("authorization", "")
        if auth != f"Bearer {KEY}" or "testkey" in self.revoked:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid API key")

    def _feed(self, ref, context) -> tuple[str, str]:
        # Another organization's feeds are stored under "org/namespace".
        ns = ref.namespace or "default"
        key = (f"{ref.organization}/{ns}" if ref.organization not in ("", "acme") else ns, ref.name)
        if key not in self.feeds:
            context.abort(grpc.StatusCode.NOT_FOUND, f"feed {ref.name} not found")
        return key

    def GetServerInfo(self, request, context):
        return pb.ServerInfo(
            version="9.9.9", api_version="v1", public_url="", max_payload_bytes=1 << 20, dedupe_window_ns=900 * 10**9,
            capabilities=self.capabilities,
        )

    def Lookup(self, request, context):
        """Answers each probe with a row whose `value` is the probe's index (the logic itself is
        the server's; this checks the request and how the answer is put back together)."""
        self._auth(context)
        self.last_lookup = request
        probes = pa.ipc.open_stream(request.probe_batch.ipc).read_all()
        n = probes.num_rows
        # Answered in reverse, in two batches, and with no row for the last probe: order and
        # gaps are the client's to handle.
        rows = list(range(n - 1))[::-1]
        for chunk in (rows[: len(rows) // 2], rows[len(rows) // 2:]):
            if not chunk:
                continue
            table = pa.table({
                "_probe": pa.array(chunk, pa.int64()),
                "_at": probes.column("_at").take(chunk),
                "_event_time": probes.column("_at").take(chunk),
                "_published_time": pa.array([None] * len(chunk), pa.timestamp("ns", tz="UTC")),
                "_receive_time": probes.column("_at").take(chunk),
                "value": pa.array([float(i) for i in chunk]),
            })
            yield pb.LookupResponse(batch=pb.ArrowBatch(ipc=ipc(table)))

    def WhoAmI(self, request, context):
        self._auth(context)
        return pb.WhoAmIResponse(
            organization="acme", default_namespace="default", role=self.role, key_id="testkey", email="a@acme.io",
            kind=pb.CREDENTIAL_KIND_SESSION, expires_at_ns=SESSION_EXPIRES_NS,
        )

    def CreateApiKey(self, request, context):
        self._auth(context)
        self.last_key_request = request
        key = pb.ApiKey(
            key_id=f"k{len(self.keys)}", role=request.role, name=request.name, kind=pb.CREDENTIAL_KIND_API_KEY,
            owner="a@acme.io" if request.personal else "", default_namespace="default",
        )
        self.keys.append(key)
        return pb.CreateApiKeyResponse(key=key, api_key=f"iso_{key.key_id}_SECRETsecretSECRETsecret")

    def ListApiKeys(self, request, context):
        self._auth(context)
        return pb.ListApiKeysResponse(keys=self.keys)

    def ListNamespaces(self, request, context):
        self._auth(context)
        if request.public:
            mine = [pb.Namespace(name=n, organization="acme", public=True) for n in sorted(self.public_namespaces)]
            return pb.ListNamespacesResponse(
                namespaces=mine + [pb.Namespace(name="public", organization="isodrome", public=True)]
            )
        return pb.ListNamespacesResponse(namespaces=[
            pb.Namespace(name=n, organization="acme", public=n in self.public_namespaces) for n in self.namespaces
        ])

    def CreateNamespace(self, request, context):
        self._auth(context)
        self.namespaces.append(request.name)
        if request.public:
            self.public_namespaces.add(request.name)
        return pb.Namespace(name=request.name, organization="acme", public=request.public)

    def UpdateNamespace(self, request, context):
        self._auth(context)
        (self.public_namespaces.add if request.public else self.public_namespaces.discard)(request.name)
        return pb.Namespace(name=request.name, organization="acme", public=request.public)

    def CreateServiceAccount(self, request, context):
        self._auth(context)
        sa = pb.ServiceAccount(id=f"sa{len(self.service_accounts)}", name=request.name, role=request.role)
        self.service_accounts.append(sa)
        return sa

    def ListServiceAccounts(self, request, context):
        self._auth(context)
        return pb.ListServiceAccountsResponse(service_accounts=self.service_accounts)

    def ListConnectorTemplates(self, request, context):
        self._auth(context)
        return pb.ListConnectorTemplatesResponse(templates=[pb.ConnectorTemplate(
            name="met_eireann.point_forecast", version=1, description="Forecasts", poll_interval_ms=900_000,
            options_example='{"locations": []}', feeds=[pb.ConnectorFeed(name="forecast", licence="CC BY 4.0")],
        )])

    def CreateConnection(self, request, context):
        self._auth(context)
        c = pb.Connection(
            name=request.name, template=request.template, namespace=request.namespace or "default",
            options_json=request.options_json or "{}", status="paused" if request.paused else "pending",
            paused=request.paused, service_account=f"connection-{request.name}", feeds=["forecast"],
            credential_fields=sorted(json.loads(request.credentials_json)) if request.credentials_json else [],
        )
        self.connections.append(c)
        return c

    def SetConnectionCredentials(self, request, context):
        self._auth(context)
        c = next(c for c in self.connections if c.name == request.name)
        del c.credential_fields[:]
        c.credential_fields.extend(sorted(json.loads(request.credentials_json)))
        return c

    def ListConnections(self, request, context):
        self._auth(context)
        return pb.ListConnectionsResponse(connections=self.connections)

    def RevokeApiKey(self, request, context):
        self._auth(context)
        self.revoked.add(request.key_id)
        return pb.ApiKey(key_id=request.key_id, revoked=True)

    def CreateFeed(self, request, context):
        self._auth(context)
        self.requests.append("CreateFeed")
        if request.feed.organization not in ("", "acme"):
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "another organization's feed")
        ns = request.feed.namespace or "default"
        if (ns, request.feed.name) in self.feeds:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "feed exists")
        feed = pb.Feed(
            id=f"id-{request.feed.name}", organization="acme", namespace=ns, name=request.feed.name,
            time_field="" if request.arrival_time else (request.time_field or "event_time"),
            arrival_time=request.arrival_time, ack_mode=pb.ACK_MODE_REPLICATED, partitions=1,
            public=ns in self.public_namespaces, attribution=request.attribution, licence=request.licence,
        )
        if request.HasField("key_field"):
            feed.key_field = request.key_field
        self.feeds[(ns, request.feed.name)] = feed
        self.events[(ns, request.feed.name)] = []
        return feed

    def GetFeed(self, request, context):
        self._auth(context)
        return self.feeds[self._feed(request.feed, context)]

    def ListFeeds(self, request, context):
        self._auth(context)
        ns = request.namespace or "default"
        if request.organization not in ("", "acme"):
            ns = f"{request.organization}/{ns}"
        return pb.ListFeedsResponse(feeds=[f for (n, _), f in self.feeds.items() if n == ns])

    def add_public_feed(self):
        """isodrome/public/forecasts: another organization's public feed, with an attribution."""
        key = ("isodrome/public", "forecasts")
        self.feeds[key] = pb.Feed(
            id="id-forecasts", organization="isodrome", namespace="public", name="forecasts", key_field="location",
            time_field="valid_to", public=True, description="Point forecasts", licence="CC BY 4.0",
            attribution="Copyright Met Éireann", publication_time_field="published",
        )
        self.events[key] = [(1, {"price": 7.5, "symbol": "dublin"})]

    def Send(self, request_iterator, context):
        self._auth(context)
        for request in request_iterator:
            self.send_requests += 1
            key = self._feed(request.feed, context)
            response = pb.SendResponse()
            for event in request.events:
                try:
                    body = json.loads(event.payload)
                except ValueError:
                    response.rejected.add(message_id=event.message_id, reason=pb.REJECTION_REASON_INVALID_JSON,
                                          detail="not JSON")
                    continue
                if "price" not in body:
                    response.rejected.add(message_id=event.message_id, reason=pb.REJECTION_REASON_MISSING_KEY,
                                          detail="no price")
                    continue
                duplicate = event.message_id in self.seen_ids
                if not duplicate:
                    self.seen_ids.add(event.message_id)
                    self.events[key].append((len(self.events[key]) * 1_000_000_000 + 1, body))
                response.accepted.add(message_id=event.message_id, duplicate=duplicate)
            yield response

    def _table(self, key, columns=()) -> pa.Table:
        events = self.events[key]
        table = pa.table({
            "_event_time": pa.array([t for t, _ in events], pa.timestamp("ns", tz="UTC")),
            "price": pa.array([e.get("price") for _, e in events], pa.float64()),
            "_key": pa.array([e.get("symbol") for _, e in events], pa.string()),
            "_payload": pa.array([json.dumps(e) for _, e in events], pa.string()),
        })
        table = table.append_column("_offset", pa.array(range(len(events)), pa.int64()))
        return table.select(list(columns)) if columns else table.drop_columns(["_offset"])

    def Read(self, request, context):
        self._auth(context)
        self.last_read = request
        table = self._table(self._feed(request.feed, context), request.columns)
        if request.HasField("limit"):
            table = table.slice(0, request.limit)
        first = pb.ReadResponse(position=pb.Position(next_offsets=[table.num_rows]),
                                estimated_rows=self.estimate[0], estimated_bytes=self.estimate[1])
        if request.estimate_only:
            yield first
            return
        first.batch.ipc = ipc(table)
        yield first

    def Latest(self, request, context):
        self._auth(context)
        table = self._table(self._feed(request.feed, context), request.columns)
        return pb.LatestResponse(batch=pb.ArrowBatch(ipc=ipc(table.slice(table.num_rows - 1))))

    def Subscribe(self, request, context):
        self._auth(context)
        table = self._table(self._feed(request.feed, context), request.columns)
        if request.WhichOneof("start") == "from_last":
            table = table.slice(max(table.num_rows - request.from_last, 0))
        yield pb.SubscribeResponse(batch=pb.ArrowBatch(ipc=ipc(table)))
        yield pb.SubscribeResponse(caught_up=pb.CaughtUp(history_events=table.num_rows))
        yield pb.SubscribeResponse(heartbeat=pb.Heartbeat(server_time_ns=1))


def serve_grpc(servicer: FakeIsodrome):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    pb_grpc.add_IsodromeServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    return server, f"http://127.0.0.1:{port}"


class FakeSignIn:
    """`/auth/device/code` and `/auth/device/token`: pending for `pending_polls` polls, then
    approved with KEY (or `final_error`)."""

    def __init__(
        self, pending_polls: int = 2, final_error: str | None = None, slow_down_once: bool = False,
        unavailable: bool = False,
    ):
        self.unavailable = unavailable
        self.pending_polls = pending_polls
        self.final_error = final_error
        self.slow_down_once = slow_down_once
        self.polls = 0
        self.client_names: list[str] = []

    def serve(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
                if fake.unavailable:
                    self._reply(503, {"error": "login_unavailable",
                                      "error_description": "sign-in is not configured on this server"})
                elif self.path == "/auth/device/code":
                    fake.client_names.append(body.get("client_name", ""))
                    self._reply(200, {
                        "device_code": "dev-123", "user_code": "WDJB-MJHT",
                        "verification_uri": "http://x/device", "verification_uri_complete": "http://x/device?code=WDJB-MJHT",
                        "expires_in": 900, "interval": 1,
                    })
                elif self.path == "/auth/device/token":
                    assert body["device_code"] == "dev-123"
                    fake.polls += 1
                    if fake.slow_down_once and fake.polls == 1:
                        self._reply(400, {"error": "slow_down"})
                    elif fake.polls <= fake.pending_polls:
                        self._reply(400, {"error": "authorization_pending"})
                    elif fake.final_error:
                        self._reply(400, {"error": fake.final_error, "error_description": "declined in the browser"})
                    else:
                        self._reply(200, {"api_key": KEY, "email": "a@acme.io", "organization": "acme",
                                          "namespace": "default", "role": "admin"})
                else:
                    self._reply(404, {})

            def _reply(self, status, body):
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeTransformers:
    """Mixed into FakeIsodrome: a deploy whose build goes queued → building → verifying → ready,
    then a stateful transformer whose backfill counts down to 0, one step per poll."""

    def _init_transformers(self):
        self.bundles: dict[str, bytes] = {}
        self.deploys: list[pb.DeployTransformerRequest] = []
        self.build_polls = 0
        self.transformer_polls = 0
        self.build_outcome = "ready"
        self.build_steps = None
        self.unavailable_polls = 0  # statuses returned poll by poll (default: building, verifying ×2, outcome)
        self.report = {"passed": True, "stages": [
            {"stage": "load", "ok": True, "startup_ms": 120, "memory_bytes": 40_000_000},
            {"stage": "replay", "ok": True, "events": 1000, "errors": 0, "outputs": 1000, "ms_per_event": 0.2,
             "deterministic": True},
            {"stage": "fixtures", "ok": True, "files": [
                {"file": "ratings.jsonl", "cases": 3, "failures": []},
                {"file": "nfl-lines/lines.jsonl", "cases": 2, "failures": [
                    {"line": 2, "expected": [{"spread": 3.5}], "got": [{"spread": 3.0}]}]},
            ]},
        ]}
        self.runs: list[pb.StartTransformerRunRequest] = []

    def UploadBundle(self, request_iterator, context):
        self._auth(context)
        import hashlib

        data = b"".join(r.chunk for r in request_iterator)
        sha = hashlib.sha256(data).hexdigest()
        self.bundles[sha] = data
        return pb.UploadBundleResponse(sha256=sha, size_bytes=len(data))

    def DeployTransformer(self, request, context):
        self._auth(context)
        self.deploys.append(request)
        self.build_polls = 0
        return self._build("queued")

    def _build(self, status):
        r = self.deploys[-1]
        b = pb.TransformerBuild(id="b1", namespace="default", transformer=r.transformer.name or "nfl-elo",
                                status=status, validate_only=r.validate_only, python_version="3.12",
                                created_at_ns=1, report_json=json.dumps(self.report) if status in (
                                    "ready", "verification_failed") else "")
        if status == "ready":
            b.finished_at_ns = 2
            b.transformer_version = 0 if r.validate_only else 3
        if status == "verification_failed":
            b.status_detail = "fixtures failed"
        return b

    def GetTransformerBuild(self, request, context):
        self._auth(context)
        if self.unavailable_polls > 0:   # the server restarting mid-build
            self.unavailable_polls -= 1
            context.abort(grpc.StatusCode.UNAVAILABLE, "restarting")
        self.build_polls += 1
        steps = self.build_steps or ["building", "verifying", "verifying", self.build_outcome]
        return self._build(steps[min(self.build_polls - 1, len(steps) - 1)])

    def GetTransformer(self, request, context):
        self._auth(context)
        self.transformer_polls += 1
        remaining = max(0, 3 - self.transformer_polls) * 1000
        return pb.Transformer(
            name=request.transformer.name, namespace="default", version=3, status="running",
            stateful=True, last_heartbeat_at_ns=10, events_in=22260,
            stats=pb.TransformerStats(backfill_remaining=remaining, code_state_bytes=4200),
            output=pb.TransformerOutput(feed="nfl_elo", pinned=pb.FeedRef(namespace="default", name="nfl_elo", version=1)),
        )

    def ListTransformers(self, request, context):
        self._auth(context)
        return pb.ListTransformersResponse(transformers=[pb.Transformer(
            name="nfl-elo", namespace="default", version=3, status="running", stateful=True,
            stats=pb.TransformerStats(backfill_remaining=1500))])

    def StartTransformerRun(self, request, context):
        self._auth(context)
        self.runs.append(request)
        return pb.TransformerRun(id="r1", transformer=request.transformer.name, version=3, status="pending",
                                 output=pb.FeedRef(namespace="default", name=request.into or "x_run", version=1))

    def GetTransformerRun(self, request, context):
        self._auth(context)
        return pb.TransformerRun(id="r1", transformer="nfl-elo", version=3, status="done", progress=1.0,
                                 events_in=10, events_out=10,
                                 output=pb.FeedRef(namespace="default", name="x_run", version=1))


for _name, _value in vars(FakeTransformers).items():
    if callable(_value) and not _name.startswith("__"):
        setattr(FakeIsodrome, _name, _value)
