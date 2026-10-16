"""gRPC connection to an Isodrome server: endpoint, TLS, and the API key on every call."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import grpc

from isodrome.v1 import isodrome_pb2 as pb
from isodrome.v1 import isodrome_pb2_grpc as pb_grpc

# The API version this client was generated from (proto package isodrome.v1).
API_VERSION = "v1"

# The only cloud deployment for now. Becomes the production URL once there is one.
DEFAULT_ENDPOINT = "https://stg.api.isodrome.ai"

# Query results arrive as Arrow batches, which can be large.
_MAX_MESSAGE_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class Endpoint:
    """A parsed endpoint URL: `https://host[:port]` (TLS, default 443) or `http://host[:port]`."""

    url: str
    host: str
    port: int
    tls: bool

    @classmethod
    def parse(cls, url: str) -> Endpoint:
        url = url.strip().rstrip("/")
        if "://" not in url:
            url = f"https://{url}"
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"invalid endpoint {url!r}: expected https://host[:port] or http://host:port")
        tls = parts.scheme == "https"
        return cls(url=url, host=parts.hostname, port=parts.port or (443 if tls else 80), tls=tls)

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"

    def http_base(self) -> str:
        """Where the server's HTTP pages (sign-in) are, when it reports no public URL: the same
        address behind TLS (a proxy routes them), or the next port locally (gRPC 7470, HTTP 7471)."""
        if self.tls:
            return self.url
        return f"http://{self.host}:{self.port + 1}"


def key_id(api_key: str) -> str:
    """`iso_<key_id>_<secret>` → `<key_id>`."""
    parts = api_key.split("_")
    if len(parts) != 3 or parts[0] != "iso" or not parts[1]:
        raise ValueError("not an Isodrome API key (expected iso_<key_id>_<secret>)")
    return parts[1]


class Transport:
    """The gRPC stub for the Isodrome service, with `authorization: Bearer <key>` on every call."""

    def __init__(self, endpoint: str, api_key: str | None = None):
        self.endpoint = Endpoint.parse(endpoint)
        options = [
            ("grpc.max_receive_message_length", _MAX_MESSAGE_BYTES),
            ("grpc.max_send_message_length", _MAX_MESSAGE_BYTES),
        ]
        if self.endpoint.tls:
            self._channel = grpc.secure_channel(self.endpoint.target, grpc.ssl_channel_credentials(), options)
        else:
            self._channel = grpc.insecure_channel(self.endpoint.target, options)
        self.stub = pb_grpc.IsodromeStub(self._channel)
        self._metadata = (("authorization", f"Bearer {api_key}"),) if api_key else ()

    def call(self, method: str, request, timeout: float | None = 30):
        """A unary call, e.g. `client.call("WhoAmI", pb.WhoAmIRequest())`."""
        return getattr(self.stub, method)(request, metadata=self._metadata, timeout=timeout)

    def stream(self, method: str, request, timeout: float | None = None):
        """A server- or bidi-streaming call; iterate the result for responses."""
        return getattr(self.stub, method)(request, metadata=self._metadata, timeout=timeout)

    def server_info(self, timeout: float = 10) -> pb.ServerInfo:
        return self.stub.GetServerInfo(pb.GetServerInfoRequest(), timeout=timeout)

    def close(self) -> None:
        self._channel.close()

    def __enter__(self) -> Transport:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
