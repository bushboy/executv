"""HTTP client for the Core Business Engine orchestration API."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx

from ingress_gateway.config import get_settings


def _reachable_base_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 8001
    if host == "core_engine":
        try:
            socket.getaddrinfo(host, port)
        except OSError:
            parsed = parsed._replace(netloc=f"127.0.0.1:{port}")
            return urlunparse(parsed).rstrip("/")
    return url.rstrip("/")


class CoreEngineClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = _reachable_base_url(base_url or get_settings().core_engine_url)

    async def orchestrate(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        *,
        org_id: str = "org_acme_corp",
    ) -> dict[str, Any]:
        params = parameters or {}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/orchestrate",
                json={
                    "transaction_id": f"mcp_{uuid4().hex[:12]}",
                    "tool_name": tool_name,
                    "session_context": {
                        "user_id": "usr_exec_01",
                        "org_id": str(params.get("org_id") or org_id),
                        "channel_source": "alexa_mcp",
                    },
                    "parameters": params,
                },
            )
            response.raise_for_status()
            body = response.json()
        return body if isinstance(body, dict) else {"result": body}
