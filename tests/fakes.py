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
        key = (ref.namespace or "default", ref.name)
        if key not in self.feeds:
            context.abort(grpc.StatusCode.NOT_FOUND, f"feed {ref.name} not found")
        return key

    def GetServerInfo(self, request, context):
        return pb.ServerInfo(
            version="9.9.9", api_version="v1", public_url="", max_payload_bytes=1 << 20, dedupe_window_ns=900 * 10**9
        )

    def WhoAmI(self, request, context):
        self._auth(context)
        return pb.WhoAmIResponse(
            organization="acme", default_namespace="default", role=pb.ROLE_ADMIN, key_id="testkey", email="a@acme.io",
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
        return pb.ListNamespacesResponse(namespaces=[pb.Namespace(name=n) for n in self.namespaces])

    def CreateNamespace(self, request, context):
        self._auth(context)
        self.namespaces.append(request.name)
        return pb.Namespace(name=request.name, organization="acme")

    def RevokeApiKey(self, request, context):
        self._auth(context)
        self.revoked.add(request.key_id)
        return pb.ApiKey(key_id=request.key_id, revoked=True)

    def CreateFeed(self, request, context):
        self._auth(context)
        ns = request.feed.namespace or "default"
        if (ns, request.feed.name) in self.feeds:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "feed exists")
        feed = pb.Feed(
            id=f"id-{request.feed.name}", organization="acme", namespace=ns, name=request.feed.name,
            time_field="" if request.arrival_time else (request.time_field or "event_time"),
            arrival_time=request.arrival_time, ack_mode=pb.ACK_MODE_REPLICATED, partitions=1,
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
        return pb.ListFeedsResponse(feeds=[f for (n, _), f in self.feeds.items() if n == ns])

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
            "price": pa.array([e["price"] for _, e in events], pa.float64()),
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
        yield pb.ReadResponse(batch=pb.ArrowBatch(ipc=ipc(table)), position=pb.Position(next_offsets=[table.num_rows]))

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
