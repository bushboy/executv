"""Alexa+ MCP server: Streamable HTTP spec ≥ 2025-11-25."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from mcp.server.mcpserver import MCPServer
from mcp_types.version import (
    LATEST_HANDSHAKE_VERSION,
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
)

from ingress_gateway.engine_client import CoreEngineClient
from ingress_gateway.mcp_session import current_session_id
from ingress_gateway.ticker import ticker

ALEXA_PLUS_MIN_SPEC = "2025-11-25"
assert ALEXA_PLUS_MIN_SPEC in SUPPORTED_PROTOCOL_VERSIONS
assert LATEST_HANDSHAKE_VERSION >= ALEXA_PLUS_MIN_SPEC
assert LATEST_PROTOCOL_VERSION >= ALEXA_PLUS_MIN_SPEC

_SESSION = {"type": "string", "description": "MCP session id that owns the challenge gate."}

MCP_TOOL_DEFINITIONS = [
    {
        "name": "get_executive_brief",
        "description": "Fetch the daily executive summary, top KPIs, and operational alerts.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": _SESSION, "window": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "explain_metric_change",
        "description": "Explain variance drivers behind a metric, including Region B margin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string"},
                "window": {"type": "string"},
                "dimension": {"type": "string"},
                "session_id": _SESSION,
            },
            "required": ["metric_name", "window", "session_id"],
        },
    },
    {
        "name": "get_pending_decisions",
        "description": "List pending executive approvals and auto-approved delegated items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": _SESSION,
                "limit": {"type": "integer"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "execute_decision",
        "description": "Evaluate playbook rules, execute a zero-turn decision, or open a challenge gate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
                "choice": {"type": "string"},
                "comment": {"type": "string"},
                "session_id": _SESSION,
            },
            "required": ["decision_id", "choice", "session_id"],
        },
    },
    {
        "name": "start_workflow",
        "description": "Initiate an operational workflow instance such as an RFQ response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_name": {"type": "string"},
                "context": {"type": "object"},
                "session_id": _SESSION,
            },
            "required": ["workflow_name", "session_id"],
        },
    },
    {
        "name": "get_workflow_status",
        "description": "Query the status and current step of an active workflow instance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_name": {"type": "string"},
                "session_id": _SESSION,
            },
            "required": ["workflow_name", "session_id"],
        },
    },
    {
        "name": "get_recent_events",
        "description": "Query live operational event feeds, including the Gate 4 Ring camera.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}, "session_id": _SESSION},
            "required": ["session_id"],
        },
    },
    {
        "name": "register_display_pairing",
        "description": "Bind an MCP session to a Fire TV pairing code for targeted SSE.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pairing_code": {"type": "string"},
                "session_id": _SESSION,
            },
            "required": ["pairing_code", "session_id"],
        },
    },
]
assert len(MCP_TOOL_DEFINITIONS) == 8
_TOOL_BY_NAME = {item["name"]: item for item in MCP_TOOL_DEFINITIONS}


mcp = MCPServer(
    name="ExecuTV Ingress Gateway",
    version="1.0.0",
    instructions=(
        "Alexa+ MCP tools for the ExecuTV executive workstation. "
        "Transport is Streamable HTTP. Negotiated protocol versions include "
        f"{ALEXA_PLUS_MIN_SPEC} and {LATEST_PROTOCOL_VERSION}. "
        "Use get_executive_brief for the dual Alexa + Fire TV morning brief. "
        "Use get_recent_events for Ring / site / delivery Live Alerts."
    ),
)


def _desc(name: str) -> str:
    return str(_TOOL_BY_NAME[name]["description"])


def _engine_parameters(arguments: dict[str, Any]) -> dict[str, Any]:
    params = dict(arguments)
    if "metric" in params and "metric_name" not in params:
        params["metric_name"] = params["metric"]
    if "period" in params and "window" not in params:
        params["window"] = params["period"]
    if "metric_name" in params and "metric" not in params:
        params["metric"] = params["metric_name"]
    if "window" in params and "period" not in params:
        window = str(params["window"])
        params["period"] = "Q3-2026" if window in {"wow", "qoq", ""} else window
    if "action" in params and "choice" not in params:
        params["choice"] = params["action"]
    if "workflow_type" in params and "workflow_name" not in params:
        params["workflow_name"] = params["workflow_type"]
    if not params.get("session_id"):
        header_session = current_session_id.get()
        if header_session:
            params["session_id"] = header_session
    context = params.get("context")
    if isinstance(context, dict):
        for key, value in context.items():
            params.setdefault(key, value)
    return params


def _narration(payload: dict[str, Any]) -> str:
    voice = payload.get("voice_summary")
    if isinstance(voice, dict):
        return str(voice.get("narration_text") or "")
    if isinstance(voice, str):
        return voice
    return ""


def _visual(payload: dict[str, Any]) -> dict[str, Any]:
    visual = payload.get("visual_state_model") or {}
    return visual if isinstance(visual, dict) else {}


def _payloads(result: dict[str, Any]) -> dict[str, Any]:
    payloads = result.get("payloads")
    return payloads if isinstance(payloads, dict) else result


async def _push_audit(decision_id: str, session_id: str | None) -> None:
    if not decision_id:
        return
    client = CoreEngineClient()
    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            response = await http.post(
                f"{client.base_url}/api/v1/decisions/audit",
                json={"decision_id": decision_id, "session_id": session_id},
            )
            response.raise_for_status()
            body = response.json()
    except Exception:  # noqa: BLE001 — the spoken challenge already returned
        return
    visual = body.get("visual_state_model") if isinstance(body, dict) else None
    if isinstance(visual, dict):
        await ticker.broadcast(
            "execute_decision",
            "COMPLETED",
            {"decision_id": decision_id},
            visual=visual,
            session_id=session_id,
        )


async def dispatch_mcp_tool_call(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Proxy one MCP tool to core_engine and emit ticker events without waiting on audit cards."""
    args = _engine_parameters(arguments or {})
    if tool_name == "register_display_pairing":
        code = str(args.get("pairing_code") or "")
        session_id = str(args.get("session_id") or "")
        bound = ticker.bind(code, session_id)
        return {"voice_summary": "Display paired." if bound else "Pairing code was not recognized.", "ok": bound}

    started = time.perf_counter()
    session_id = str(args.get("session_id") or "") or None
    await ticker.broadcast(tool_name, "EXECUTING", args, session_id=session_id)
    try:
        result = await CoreEngineClient().orchestrate(tool_name, args)
    except Exception as exc:  # noqa: BLE001 — surface a JSON-RPC friendly engine failure
        elapsed = (time.perf_counter() - started) * 1000
        error = {"error": f"Engine dispatch failed: {exc}"}
        await ticker.broadcast(tool_name, "FAILED", error, elapsed, session_id=session_id)
        return error
    elapsed = (time.perf_counter() - started) * 1000
    payloads = _payloads(result)
    visual = _visual(payloads)
    await ticker.broadcast(tool_name, "COMPLETED", args, elapsed, visual=visual or None, session_id=session_id)
    if visual.get("deferred_audit"):
        decision_id = str(visual.get("decision_id") or args.get("decision_id") or "")
        asyncio.create_task(_push_audit(decision_id, session_id))
    return result


async def _mcp_text(tool_name: str, arguments: dict[str, Any]) -> str:
    result = await dispatch_mcp_tool_call(tool_name, arguments)
    payloads = _payloads(result)
    visual = _visual(payloads)
    return json.dumps(
        {
            "voice_summary": _narration(payloads) or result.get("error"),
            "visual_state_model": visual,
            "view_id": visual.get("view_id"),
        },
        default=str,
    )


@mcp.tool(description=_desc("get_executive_brief"))
async def get_executive_brief(session_id: str, window: str = "Q3-2026") -> str:
    return await _mcp_text("get_executive_brief", {"session_id": session_id, "window": window})


@mcp.tool(description=_desc("explain_metric_change"))
async def explain_metric_change(
    metric_name: str,
    window: str,
    session_id: str,
    dimension: str = "Region B",
) -> str:
    return await _mcp_text(
        "explain_metric_change",
        {
            "metric_name": metric_name,
            "window": window,
            "dimension": dimension,
            "session_id": session_id,
        },
    )


@mcp.tool(description=_desc("get_pending_decisions"))
async def get_pending_decisions(session_id: str, limit: int = 8) -> str:
    return await _mcp_text("get_pending_decisions", {"session_id": session_id, "limit": limit})


@mcp.tool(description=_desc("execute_decision"))
async def execute_decision(decision_id: str, choice: str, session_id: str, comment: str = "") -> str:
    return await _mcp_text(
        "execute_decision",
        {"decision_id": decision_id, "choice": choice, "comment": comment, "session_id": session_id},
    )


@mcp.tool(description=_desc("start_workflow"))
async def start_workflow(workflow_name: str, session_id: str, context: dict[str, Any] | None = None) -> str:
    return await _mcp_text(
        "start_workflow",
        {"workflow_name": workflow_name, "session_id": session_id, "context": context or {}},
    )


@mcp.tool(description=_desc("get_workflow_status"))
async def get_workflow_status(workflow_name: str, session_id: str) -> str:
    return await _mcp_text("get_workflow_status", {"workflow_name": workflow_name, "session_id": session_id})


@mcp.tool(description=_desc("get_recent_events"))
async def get_recent_events(session_id: str, limit: int = 5) -> str:
    return await _mcp_text("get_recent_events", {"limit": limit, "session_id": session_id})


@mcp.tool(description=_desc("register_display_pairing"))
async def register_display_pairing(pairing_code: str, session_id: str) -> str:
    result = await dispatch_mcp_tool_call(
        "register_display_pairing",
        {"pairing_code": pairing_code, "session_id": session_id},
    )
    return json.dumps(result, default=str)
