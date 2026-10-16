"""Exceptions, one per kind of failure the API reports."""

from __future__ import annotations

import functools
import time

import grpc


class IsodromeError(Exception):
    """Anything the Isodrome API refused or could not do."""

    code: grpc.StatusCode | None = None

    def __init__(self, message: str, code: grpc.StatusCode | None = None):
        super().__init__(message)
        self.code = code or type(self).code


class Unauthenticated(IsodromeError):
    """No credential, or a wrong, revoked or expired one: run `iso login`."""

    code = grpc.StatusCode.UNAUTHENTICATED


class PermissionDenied(IsodromeError):
    """The credential's role may not do this."""

    code = grpc.StatusCode.PERMISSION_DENIED


class NotFound(IsodromeError):
    """No such namespace, feed or key, in your organization (or another's public namespace)."""

    code = grpc.StatusCode.NOT_FOUND


class AlreadyExists(IsodromeError):
    code = grpc.StatusCode.ALREADY_EXISTS


class InvalidArgument(IsodromeError):
    code = grpc.StatusCode.INVALID_ARGUMENT


class FailedPrecondition(IsodromeError):
    """Not possible in the current state, e.g. re-keying a feed that has events."""

    code = grpc.StatusCode.FAILED_PRECONDITION


class Unavailable(IsodromeError):
    """Temporarily unable (already retried)."""

    code = grpc.StatusCode.UNAVAILABLE


class Rejected(IsodromeError):
    """Some pushed events were rejected; `.rejected` lists them, `.result` has the rest."""

    def __init__(self, message: str, result):
        super().__init__(message)
        self.result = result
        self.rejected = result.rejected


_BY_CODE = {cls.code: cls for cls in IsodromeError.__subclasses__() if cls.code is not None}
_RETRYABLE = (grpc.StatusCode.UNAVAILABLE,)


def translate(e: grpc.RpcError) -> IsodromeError:
    code = e.code()
    message = f"{code.name}: {e.details() or ''}"
    if code == grpc.StatusCode.UNAUTHENTICATED:
        message += " (run `iso login`, or pass api_key=)"
    return _BY_CODE.get(code, IsodromeError)(message, code)


def call(fn, *args, attempts: int = 3, **kwargs):
    """Runs a unary call; retries UNAVAILABLE with backoff, and turns gRPC errors into ours."""
    for attempt in range(attempts):
        try:
            return fn(*args, **kwargs)
        except grpc.RpcError as e:
            if e.code() in _RETRYABLE and attempt < attempts - 1:
                time.sleep(0.5 * 2**attempt)
                continue
            raise translate(e) from None
    raise AssertionError("unreachable")


def translating(fn):
    """Decorator: gRPC errors raised inside `fn` (including while streaming) become ours."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except grpc.RpcError as e:
            raise translate(e) from None

    return wrapper
