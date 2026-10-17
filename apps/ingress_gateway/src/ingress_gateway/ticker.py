"""Live MCP tool telemetry for the judge SSE ticker and Fire TV widget."""

from __future__ import annotations

import asyncio
import json
import secrets
from collections import deque
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

_MAX_EVENTS = 50
_PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TelemetryTicker:
    """Broadcaster for live MCP tool execution events via Server-Sent Events."""

    def __init__(self) -> None:
        self._subscribers: dict[str | None, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._recent: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
        self.pairings: dict[str, str] = {}
        self.session_to_code: dict[str, str] = {}

    def issue_code(self) -> str:
        while True:
            code = "".join(secrets.choice(_PAIRING_ALPHABET) for _ in range(4))
            if code not in self.pairings:
                self.pairings[code] = ""
                return code

    def bind(self, pairing_code: str, session_id: str) -> bool:
        code = pairing_code.strip().upper()
        if code not in self.pairings or not session_id.strip():
            return False
        previous = self.session_to_code.get(session_id)
        if previous and previous != code:
            self.pairings.pop(previous, None)
        self.pairings[code] = session_id
        self.session_to_code[session_id] = code
        return True

    async def subscribe(self, request: Request | None = None, pairing_id: str | None = None) -> AsyncIterator[str]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        key = pairing_id.strip().upper() if pairing_id else None
        self._subscribers.setdefault(key, set()).add(queue)
        try:
            snapshot = {"type": "snapshot", "events": list(self._recent)}
            yield f"data: {json.dumps(snapshot)}\n\n"
            while True:
                if request is not None and await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    payload = json.dumps(event, default=str)
                    yield f"event: ticker\ndata: {payload}\n\n"
                except TimeoutError:
                    yield ":\n\n"
        finally:
            subscribers = self._subscribers.get(key)
            if subscribers is not None:
                subscribers.discard(queue)

    async def broadcast(
        self,
        tool_name: str,
        status: str,
        args: dict[str, Any] | None = None,
        latency_ms: float = 0.0,
        *,
        visual: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        arguments = args or {}
        stamp = _utc_stamp()
        event = {
            "timestamp": stamp,
            "ts": stamp,
            "tool_name": tool_name,
            "status": status,
            "args": arguments,
            "detail": _detail(status, arguments, latency_ms),
            "latency_ms": round(latency_ms, 2),
        }
        if visual:
            event["visual_state_model"] = visual
        code = self.session_to_code.get(session_id or "")
        event["pairing_id"] = code
        self._recent.appendleft(event)
        targets: list[str | None] = [code] if code else [None]
        for key in targets:
            for queue in list(self._subscribers.get(key, ())):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    continue
        return event


def _detail(_status: str, args: dict[str, Any], latency_ms: float) -> str:
    hint = args.get("error") or args.get("metric") or args.get("decision_id") or args.get("workflow_type")
    parts = [str(hint)] if hint else []
    if latency_ms:
        parts.append(f"{round(latency_ms, 2)}ms")
    return " · ".join(parts)


ticker = TelemetryTicker()


async def ticker_stream(request: Request, pairing_id: str | None = None) -> StreamingResponse:
    return StreamingResponse(
        ticker.subscribe(request, pairing_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
