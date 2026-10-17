"""ExecuTV Core Business Engine — FastAPI dual-payload orchestration API."""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from core_data_layer.database import get_session, init_db
from core_data_layer.models import DEFAULT_ORG_ID

from core_engine.config import get_settings
from core_engine.formatter import DualPayloadFormatter
from core_engine.llm import narrate_audit, reason_from_utterance
from core_engine.schemas import (
    OPENAPI_TAGS,
    ORCHESTRATE_DESCRIPTION,
    DualPayload,
    EventIngestRequest,
    EventIngestResponse,
    HealthResponse,
    OrchestrationRequest,
    OrchestrationResponse,
    ReasonApiResponse,
    ReasonRequest,
)
from core_engine.services import OrchestrationService


def _seed_if_empty() -> None:
    from sqlmodel import select

    from core_data_layer.database import engine
    from core_data_layer.models import KPI
    from core_data_layer.seed import seed_data

    with Session(engine) as session:
        if session.exec(select(KPI)).first() is None:
            seed_data()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _seed_if_empty()
    yield


app = FastAPI(
    title="ExecuTV Core Business Engine",
    version="1.0.0",
    description=(
        "Orchestration API and Dual-Payload Formatter for Alexa+ and Fire TV. "
        "Live docs: `/docs` (Swagger UI) and `/redoc`. Machine-readable spec: `/openapi.json`. "
        "Checked-in copy: `docs/openapi/core-engine.json`."
    ),
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    servers=[
        {"url": "http://localhost:8001", "description": "Local Core Business Engine"},
        {"url": "http://127.0.0.1:8001", "description": "Loopback Core Business Engine"},
    ],
)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _service(session: Session = Depends(get_session)) -> OrchestrationService:
    return OrchestrationService(session)


def _authorized(authorization: str | None) -> bool:
    token = get_settings().mcp_bearer_token
    if not token or not authorization:
        return False
    scheme, _, presented = authorization.partition(" ")
    if scheme.lower() != "bearer" or not presented.strip():
        return False
    return hmac.compare_digest(presented.strip(), token)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health", response_model=HealthResponse, tags=["health"], summary="Health check")
@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"], summary="Health check")
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="core_engine")


@app.post(
    "/api/v1/orchestrate",
    response_model=OrchestrationResponse,
    tags=["orchestration"],
    summary="Run a domain tool",
    description=ORCHESTRATE_DESCRIPTION,
    responses={400: {"description": "Unknown tool or missing domain record."}},
)
def orchestrate_domain_action(
    request: OrchestrationRequest,
    service: OrchestrationService = Depends(_service),
) -> OrchestrationResponse:
    org_id = str(request.session_context.get("org_id") or DEFAULT_ORG_ID)
    result = service.process_tool_request(request.tool_name, org_id, request.parameters)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return OrchestrationResponse(
        transaction_id=request.transaction_id,
        status="COMPLETED",
        payloads=DualPayload.model_validate(result),
    )


@app.get(
    "/v1/briefings/current",
    response_model=DualPayload,
    tags=["briefings"],
    summary="Current executive briefing",
)
@app.get(
    "/api/v1/briefings/current",
    response_model=DualPayload,
    tags=["briefings"],
    summary="Current executive briefing",
)
def get_current_briefing(
    org_id: str = Query(default=DEFAULT_ORG_ID, description="Organization to brief."),
    service: OrchestrationService = Depends(_service),
) -> DualPayload:
    return DualPayload.model_validate(service.process_tool_request("get_executive_brief", org_id, {}))


@app.post(
    "/api/v1/events/ingest",
    response_model=EventIngestResponse,
    tags=["events"],
    summary="Ingest a Ring / site operational event",
)
def ingest_event(
    event_payload: EventIngestRequest,
    service: OrchestrationService = Depends(_service),
) -> EventIngestResponse:
    created = service.ingest_operational_event(event_payload.model_dump(exclude_none=True))
    return EventIngestResponse(status="INGESTED", event_id=created.id)


@app.post(
    "/api/v1/reason",
    response_model=ReasonApiResponse,
    tags=["reasoning"],
    summary="Map an utterance to a tool (Bedrock or seeded fallback)",
    responses={400: {"description": "Resolved tool failed against domain data."}},
)
def reason_utterance(
    request: ReasonRequest,
    service: OrchestrationService = Depends(_service),
) -> dict[str, Any]:
    reasoned = reason_from_utterance(request.utterance)
    body: dict[str, Any] = {
        "intent": reasoned.intent,
        "tool": reasoned.tool,
        "tool_arguments": reasoned.tool_arguments,
        "voice_summary": reasoned.voice_summary,
        "source": reasoned.source,
    }
    if not request.execute:
        return body
    arguments = dict(reasoned.tool_arguments)
    arguments.setdefault("session_id", request.session_id or "tv-local")
    payloads = service.process_tool_request(reasoned.tool, request.org_id, arguments)
    if "error" in payloads:
        raise HTTPException(status_code=400, detail=payloads["error"])
    narration = (payloads.get("voice_summary") or {}).get("narration_text")
    if narration:
        body["voice_summary"] = narration
    body["payloads"] = payloads
    return body


class AuditRequest(BaseModel):
    decision_id: str
    session_id: str | None = None


@app.post("/api/v1/decisions/audit", tags=["orchestration"], summary="Build the async audit card")
def build_audit_card(
    request: AuditRequest,
    service: OrchestrationService = Depends(_service),
) -> dict[str, Any]:
    decision = service.decision_repo.get(request.decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    payload = DualPayloadFormatter.format_audit(decision)
    narration = narrate_audit(
        f"Decision {decision.title} amount {decision.amount}. "
        f"Margin impact {decision.margin_impact_pts}. "
        f"Downtime {decision.downtime_daily_usd} per day for {decision.downtime_days} days."
    )
    if narration:
        payload["voice_summary"]["narration_text"] = narration
        for component in payload["visual_state_model"]["components"]:
            if component.get("id") == "riskiest_assumption":
                items = component.get("items") or []
                if items:
                    items[0]["body"] = narration
    return payload


@app.post("/admin/reset-scenario", tags=["admin"], summary="Restore the AcroCorp seed")
def reset_scenario(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from core_data_layer.seed import seed_data

    seed_data()
    return {"status": "reset"}


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "core_engine.main:app",
        host=settings.core_engine_host,
        port=settings.core_engine_port,
        reload=True,
    )
