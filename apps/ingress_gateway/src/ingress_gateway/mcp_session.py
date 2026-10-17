"""MCP session, bearer, protocol, and Origin gates for Streamable HTTP."""

from __future__ import annotations

import hmac
import json
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

from ingress_gateway.config import get_settings

LOCAL_SIM_SESSION_ID = "executv-local-sim"
current_session_id: ContextVar[str] = ContextVar("mcp_session_id", default="")
SUPPORTED_PROTOCOL_VERSIONS = {"2025-11-25", "2026-07-28"}
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "host.docker.internal")


def _headers(scope: MutableMapping[str, Any]) -> dict[str, str]:
    return {name.decode("latin1").lower(): value.decode("latin1") for name, value in scope.get("headers") or []}


def _is_local(headers: dict[str, str]) -> bool:
    host = headers.get("host", "")
    origin = headers.get("origin", "")
    host_local = any(token in host for token in _LOCAL_HOSTS)
    origin_local = not origin or any(token in origin for token in _LOCAL_HOSTS)
    return host_local and origin_local


def _bearer_ok(headers: dict[str, str]) -> bool:
    token = get_settings().mcp_bearer_token
    presented = headers.get("authorization", "")
    if not token or not presented.lower().startswith("bearer "):
        return False
    return hmac.compare_digest(presented.split(" ", 1)[1].strip(), token)


def _origin_ok(headers: dict[str, str]) -> bool:
    origin = headers.get("origin", "")
    if not origin:
        return True
    allowed = set(get_settings().cors_origin_list)
    return origin in allowed


def _protocol_ok(headers: dict[str, str]) -> bool:
    version = headers.get("protocol-version") or headers.get("mcp-protocol-version") or ""
    return version in SUPPORTED_PROTOCOL_VERSIONS


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(message.get("body") or b"")
        if not message.get("more_body"):
            return b"".join(chunks)


def _json_method(body: bytes) -> str:
    if not body:
        return ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if isinstance(payload, dict):
        return str(payload.get("method") or "")
    return ""


def _session_value(scope: MutableMapping[str, Any]) -> str:
    for name, value in scope.get("headers") or []:
        if name.lower() == b"mcp-session-id":
            return value.decode("latin1")
    return ""


def _reject(status: int, message: str) -> dict[str, Any]:
    raw = json.dumps({"error": message}).encode("utf-8")
    return {
        "status": status,
        "body": raw,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(raw)).encode("ascii")),
        ],
    }


class McpSessionIdMiddleware:
    """Enforce bearer, Origin, and protocol gates. Inject a session id only for local clients."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path") or "")
        protected = path.startswith("/mcp") or path == "/admin/reset-scenario"
        if not protected:
            await self.app(scope, receive, send)
            return

        headers = _headers(scope)
        if not _bearer_ok(headers):
            await _send_json(send, 401, "Unauthorized")
            return
        if not _origin_ok(headers):
            await _send_json(send, 403, "Origin is not allowed")
            return

        method = str(scope.get("method") or "").upper()
        if path.startswith("/mcp") and _is_local(headers):
            has_session = any(name.lower() == b"mcp-session-id" for name, _value in scope.get("headers") or [])
            if not has_session:
                scope = {
                    **scope,
                    "headers": [
                        *list(scope.get("headers") or []),
                        (b"mcp-session-id", LOCAL_SIM_SESSION_ID.encode("ascii")),
                    ],
                }
        session_token = current_session_id.set(_session_value(scope))
        try:
            if method == "POST" and path.startswith("/mcp"):
                await self._guard_post(scope, receive, send)
                return
            await self.app(scope, receive, send)
        finally:
            current_session_id.reset(session_token)

    async def _guard_post(self, scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        headers = _headers(scope)
        body = await _read_body(receive)
        if not _protocol_ok(headers):
            await _send_json(send, 400, "protocol-version must be 2025-11-25 or a newer supported version")
            return
        rpc_method = _json_method(body)
        has_session = any(name.lower() == b"mcp-session-id" for name, _value in scope.get("headers") or [])
        if rpc_method not in {"", "initialize", "ping"} and not has_session and not _is_local(headers):
            await _send_json(send, 400, "mcp-session-id is required")
            return

        async def replay() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)


async def _send_json(send: Any, status: int, message: str) -> None:
    rejected = _reject(status, message)
    await send({"type": "http.response.start", "status": rejected["status"], "headers": rejected["headers"]})
    await send({"type": "http.response.body", "body": rejected["body"]})
