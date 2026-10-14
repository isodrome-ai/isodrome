"""Signing in with the browser: the OAuth 2.0 device flow (RFC 8628) against the server.

1. `POST /auth/device/code` returns a secret device code, a short user code and a page.
2. The person opens the page, checks the code matches, signs in with Google and approves.
3. Meanwhile we poll `POST /auth/device/token` until it hands over an API key (exactly once).
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable


class LoginError(Exception):
    pass


class Unavailable(LoginError):
    """The server has no browser sign-in (e.g. a local server)."""


@dataclass
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


@dataclass
class Granted:
    api_key: str
    email: str
    organization: str
    namespace: str
    role: str


def _post(url: str, body: dict, timeout: float = 15) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not response.headers.get("content-type", "").startswith("application/json"):
                raise LoginError(
                    f"{url} did not answer as a sign-in endpoint (HTTP {response.status}); "
                    "the server or its proxy is not set up for sign-in"
                )
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as e:
        # OAuth errors come back as 4xx/5xx with a JSON body.
        try:
            return json.loads(e.read() or b"{}")
        except ValueError:
            raise LoginError(f"{url}: HTTP {e.code}") from None
    except (urllib.error.URLError, socket.timeout, ValueError) as e:
        raise LoginError(f"could not reach {url}: {getattr(e, 'reason', e)}") from None


def start(base: str, client_name: str) -> DeviceCode:
    reply = _post(f"{base}/auth/device/code", {"client_name": client_name})
    if reply.get("error") == "login_unavailable":
        raise Unavailable(reply.get("error_description") or "sign-in is not configured on this server")
    if "error" in reply:
        raise LoginError(reply.get("error_description") or reply["error"])
    try:
        return DeviceCode(
            device_code=reply["device_code"],
            user_code=reply["user_code"],
            verification_uri=reply.get("verification_uri", ""),
            verification_uri_complete=reply["verification_uri_complete"],
            expires_in=int(reply.get("expires_in", 900)),
            interval=int(reply.get("interval", 5)),
        )
    except KeyError as e:
        raise LoginError(f"unexpected reply from {base}: no {e}") from None


def poll(
    base: str,
    code: DeviceCode,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Granted:
    interval = max(code.interval, 1)
    deadline = clock() + code.expires_in
    while True:
        sleep(interval)
        reply = _post(f"{base}/auth/device/token", {"device_code": code.device_code})
        error = reply.get("error")
        if error == "authorization_pending":
            if clock() > deadline:
                raise LoginError("the login expired; run `iso login` again")
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error:
            raise LoginError(reply.get("error_description") or error)
        try:
            return Granted(
                api_key=reply["api_key"],
                email=reply.get("email", ""),
                organization=reply.get("organization", ""),
                namespace=reply.get("namespace", ""),
                role=reply.get("role", ""),
            )
        except KeyError:
            raise LoginError("the server approved the login but sent no API key") from None
