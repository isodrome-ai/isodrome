"""Sending events: reading them from text, giving each a message id, and batching them."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Iterable, Iterator

import grpc

from isodrome.v1 import isodrome_pb2 as pb

# Per request. The server's gRPC limit is 4 MiB; leave room for framing.
MAX_BATCH_BYTES = 3 * 1024 * 1024
DEFAULT_BATCH_SIZE = 500
_RETRYABLE = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


@dataclass
class Item:
    """One event to send, and where it came from (for error messages)."""

    source: str  # e.g. "line 12" or "--data #2"
    payload: bytes
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def parse_events(text: str, source: str = "") -> Iterator[tuple[str, bytes]]:
    """A JSON object, a JSON array of objects, or JSON Lines → (where, payload) pairs.

    Payloads are passed through as given (one per array element or line), so the server judges
    them: a line that is not valid JSON is still sent and comes back as a visible rejection.
    """
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("["):
        try:
            events = json.loads(stripped)
        except ValueError as e:
            raise ValueError(f"{source or 'input'}: not a valid JSON array: {e}") from None
        for i, event in enumerate(events):
            yield f"{source}[{i}]", json.dumps(event, separators=(",", ":")).encode()
        return
    try:
        # A single (possibly multi-line, pretty-printed) object.
        event = json.loads(stripped)
        yield source or "event", json.dumps(event, separators=(",", ":")).encode()
        return
    except ValueError:
        pass
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip():
            yield f"{source}:{n}" if source else f"line {n}", line.strip().encode()


def stable_id(path: str, where: str, payload: bytes) -> str:
    """A message id derived from the file, the event's place in it and its content: pushing the
    same file again is answered `duplicate` instead of writing every event twice (within the
    server's de-duplication window), while an edited event gets a new id."""
    digest = hashlib.sha256(f"{os.path.abspath(path)}\0{where}\0".encode() + payload).digest()
    return digest[:16].hex()


def batches(items: Iterable[Item], size: int = DEFAULT_BATCH_SIZE, max_bytes: int = MAX_BATCH_BYTES):
    batch, batch_bytes = [], 0
    for item in items:
        cost = len(item.payload) + len(item.message_id) + 16
        if batch and (len(batch) >= size or batch_bytes + cost > max_bytes):
            yield batch
            batch, batch_bytes = [], 0
        batch.append(item)
        batch_bytes += cost
    if batch:
        yield batch


@dataclass
class Result:
    accepted: int = 0
    duplicates: int = 0
    rejected: list[tuple[Item, pb.Rejection]] = field(default_factory=list)


def send_batch(client, feed: pb.FeedRef, batch: list[Item], attempts: int = 3) -> pb.SendResponse:
    """Sends one batch, retrying on transient errors. Retries are safe: the same message ids
    make the server answer `duplicate` instead of writing twice."""
    request = pb.SendRequest(
        feed=feed,
        events=[pb.Event(payload=item.payload, message_id=item.message_id) for item in batch],
    )
    for attempt in range(attempts):
        try:
            return next(iter(client.stream("Send", iter([request]), timeout=60)))
        except grpc.RpcError as e:
            if e.code() not in _RETRYABLE or attempt == attempts - 1:
                raise
            time.sleep(0.5 * 2**attempt)
    raise AssertionError("unreachable")


def send(client, feed: pb.FeedRef, items: Iterable[Item], batch_size: int = DEFAULT_BATCH_SIZE) -> Result:
    result = Result()
    for batch in batches(items, batch_size):
        response = send_batch(client, feed, batch)
        by_id = {item.message_id: item for item in batch}
        result.accepted += len(response.accepted)
        result.duplicates += sum(1 for a in response.accepted if a.duplicate)
        for rejection in response.rejected:
            item = by_id.get(rejection.message_id) or Item(source="?", payload=b"", message_id=rejection.message_id)
            result.rejected.append((item, rejection))
    return result
