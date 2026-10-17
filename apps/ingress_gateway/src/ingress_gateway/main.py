"""ExecuTV Ingress Gateway — Alexa+ MCP Streamable HTTP + SSE tool ticker."""

from __future__ import annotations

import contextlib
import json
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ingress_gateway.config import get_settings
from ingress_gateway.engine_client import CoreEngineClient
from ingress_gateway.mcp_server import (
    ALEXA_PLUS_MIN_SPEC,
    MCP_TOOL_DEFINITIONS,
    dispatch_mcp_tool_call,
    mcp,
)
from ingress_gateway.mcp_session import McpSessionIdMiddleware
from ingress_gateway.ticker import ticker, ticker_stream

_JSONRPC_PATHS = {"/mcp", "/mcp/v1/tools/call"}


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = "req_01"
    method: str
    params: dict[str, Any] | None = None


class JsonRpcFallbackMiddleware:
    """Handle judge-friendly JSON-RPC POSTs that are not MCP Streamable HTTP.

    Alexa+ clients send ``Accept: application/json, text/event-stream`` and go
    through the mounted MCP SDK app. Bare ``curl`` JSON-RPC hits this fallback.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if not _is_simple_jsonrpc(scope):
            await self.app(scope, receive, send)
            return
        body = await _read_body(receive)
        try:
            request = JsonRpcRequest.model_validate(json.loads(body or b"{}"))
            status, payload = await handle_mcp_jsonrpc(request)
        except Exception as exc:  # noqa: BLE001 — always return JSON-RPC errors
            status, payload = 400, {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
        raw = json.dumps(payload, default=str).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(raw)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw})


def _is_simple_jsonrpc(scope: dict[str, Any]) -> bool:
    if scope.get("type") != "http" or scope.get("method") != "POST":
        return False
    path = str(scope.get("path") or "").rstrip("/") or "/"
    if path not in _JSONRPC_PATHS:
        return False
    headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers") or []}
    return "text/event-stream" not in headers.get("accept", "").lower()


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(message.get("body") or b"")
        if not message.get("more_body"):
            return b"".join(chunks)


async def handle_mcp_jsonrpc(request: JsonRpcRequest) -> tuple[int, dict[str, Any]]:
    params = request.params or {}
    if request.method == "tools/list":
        return 200, {"jsonrpc": "2.0", "id": request.id, "result": {"tools": MCP_TOOL_DEFINITIONS}}
    if request.method == "tools/call":
        tool_name = params.get("name")
        if not tool_name:
            return 400, {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {"code": -32602, "message": "Missing tool name"},
            }
        result = await dispatch_mcp_tool_call(str(tool_name), params.get("arguments") or {})
        return 200, {"jsonrpc": "2.0", "id": request.id, "result": result}
    if request.method == "initialize":
        return 200, {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "protocolVersion": ALEXA_PLUS_MIN_SPEC,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ExecuTV Ingress Gateway", "version": "1.0.0"},
            },
        }
    if request.method == "ping":
        return 200, {"jsonrpc": "2.0", "id": request.id, "result": {}}
    return 404, {
        "jsonrpc": "2.0",
        "id": request.id,
        "error": {"code": -32601, "message": f"Method '{request.method}' not found"},
    }


def _core_health() -> dict[str, Any]:
    try:
        response = httpx.get(f"{CoreEngineClient().base_url}/health", timeout=2.0)
        body = response.json()
        if response.status_code == 200 and isinstance(body, dict):
            return body
        return {"status": "unreachable", "code": response.status_code}
    except httpx.HTTPError:
        return {"status": "unreachable"}


async def _proxy_core(request: Request) -> Response:
    url = f"{CoreEngineClient().base_url}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {}
    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            upstream = await client.request(request.method, url, content=await request.body(), headers=headers)
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"error": f"Core engine unreachable: {exc}"})
    media_type = upstream.headers.get("content-type")
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media_type)


def create_app() -> FastAPI:
    settings = get_settings()
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        host="0.0.0.0",
    )

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        session_manager = getattr(mcp, "session_manager", None)
        if session_manager is None:
            yield
            return
        async with session_manager.run():
            yield

    application = FastAPI(
        title="ExecuTV Ingress Gateway (Alexa+ MCP)",
        version="1.0.0",
        description=(
            "Self-hosted MCP Streamable HTTP server (spec 2025-11-25) at /mcp. "
            "SSE telemetry is at /events/ticker. "
            "POST /mcp/v1/tools/call is a local test helper and is not part of the compliance claim."
        ),
        lifespan=lifespan,
        servers=[{"url": "http://localhost:8000", "description": "Local Ingress Gateway"}],
    )
    application.add_middleware(JsonRpcFallbackMiddleware)
    application.add_middleware(McpSessionIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["health"], summary="Health check")
    def health_check() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "ingress_gateway",
            "core": _core_health(),
            "mcp_spec": f">={ALEXA_PLUS_MIN_SPEC}",
            "mcp": {
                "transport": "streamable-http",
                "endpoint": settings.mcp_mount_path,
                "spec_min": ALEXA_PLUS_MIN_SPEC,
                "sdk_handshake": "2025-11-25",
                "sdk_latest": "2026-07-28",
                "tools": [item["name"] for item in MCP_TOOL_DEFINITIONS],
            },
        }

    @application.api_route("/v1/briefings/current", methods=["GET"])
    @application.api_route("/api/v1/briefings/current", methods=["GET"])
    @application.api_route("/api/v1/orchestrate", methods=["POST"])
    @application.api_route("/api/v1/reason", methods=["POST"])
    async def proxy_core_for_tv(request: Request) -> Response:
        """Fire TV calls one public origin. Core stays on the private network."""
        return await _proxy_core(request)

    @application.get("/events/ticker", tags=["telemetry"], summary="SSE live tool ticker")
    async def stream_telemetry(request: Request):
        return await ticker_stream(request)

    @application.get("/events/ticker/{pairing_id}", tags=["telemetry"], summary="Paired SSE channel")
    async def stream_paired_telemetry(pairing_id: str, request: Request):
        return await ticker_stream(request, pairing_id)

    @application.get("/displays/pairing-code", tags=["telemetry"], summary="Issue a Fire TV pairing code")
    def issue_pairing_code() -> dict[str, str]:
        return {"pairing_code": ticker.issue_code()}

    @application.post("/admin/reset-scenario", tags=["admin"], summary="Restore the AcroCorp seed")
    async def reset_scenario() -> JSONResponse:
        token = get_settings().mcp_bearer_token
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{CoreEngineClient().base_url}/admin/reset-scenario",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            return JSONResponse(status_code=502, content={"error": f"Reset failed: {exc}"})
        try:
            content = response.json()
        except ValueError:
            content = {"error": response.text}
        return JSONResponse(status_code=response.status_code, content=content)

    @application.get("/mcp/tools", tags=["mcp"], summary="List MCP tools")
    def list_mcp_tools() -> dict[str, Any]:
        return {"tools": MCP_TOOL_DEFINITIONS}

    @application.post(
        "/mcp/v1/tools/call",
        tags=["mcp"],
        summary="Local JSON-RPC helper",
        description="Development helper. Not part of the Streamable HTTP compliance surface.",
    )
    async def jsonrpc_tools_call(body: JsonRpcRequest) -> JSONResponse:
        status, payload = await handle_mcp_jsonrpc(body)
        return JSONResponse(status_code=status, content=payload)

    application.mount(settings.mcp_mount_path, mcp_app)
    return application


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "ingress_gateway.main:app",
        host=settings.ingress_gateway_host,
        port=settings.ingress_gateway_port,
        reload=True,
    )
