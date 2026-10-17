"""OpenAPI request/response models for the Core Business Engine."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core_data_layer.models import DEFAULT_ORG_ID

TOOL_NAMES = (
    "get_executive_brief",
    "explain_metric_change",
    "get_pending_decisions",
    "execute_decision",
    "start_workflow",
    "get_workflow_status",
    "get_recent_events",
)
ToolName = Literal[
    "get_executive_brief",
    "explain_metric_change",
    "get_pending_decisions",
    "execute_decision",
    "start_workflow",
    "get_workflow_status",
    "get_recent_events",
]


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str = Field(examples=["core_engine"])


class VoiceSummary(BaseModel):
    narration_text: str = Field(description="Couch-friendly Alexa narration for this view.")
    suggested_followups: list[str] = Field(default_factory=list)


class VisualComponent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str = Field(
        description="KPI_GRID, ALERTS_TIMELINE, METRIC_CARD, DRIVER_BREAKDOWN_LIST, DECISION_CARD_LIST, or WORKFLOW_STEP_LIST."
    )
    title: str | None = None
    items: list[dict[str, Any]] | None = None


class VisualStateModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_id: str = Field(examples=["EXECUTIVE_BRIEF"])
    header_title: str
    badge_status: str
    components: list[VisualComponent] = Field(default_factory=list)
    highlight_target_id: str | None = None


class DualPayload(BaseModel):
    """Synchronized Alexa voice + Fire TV visual document."""

    voice_summary: VoiceSummary
    visual_state_model: VisualStateModel


class OrchestrationRequest(BaseModel):
    transaction_id: str = Field(examples=["tx_test_01"])
    tool_name: ToolName
    session_context: dict[str, Any] = Field(
        default_factory=dict,
        examples=[{"org_id": "org_acme_corp"}],
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        examples=[{"metric": "margin", "dimension": "Region B", "period": "Q3-2026"}],
    )


class OrchestrationResponse(BaseModel):
    transaction_id: str
    status: Literal["COMPLETED"] = "COMPLETED"
    payloads: DualPayload


class EventIngestRequest(BaseModel):
    """Ring / site operational event. Accepts either the domain schema or the mock-script fields."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    org_id: str | None = Field(default=None, examples=[DEFAULT_ORG_ID])
    source: str = Field(default="ring_site_gateway", examples=["ring"])
    event_type: str | None = Field(default=None, examples=["delivery_detected"])
    location: str | None = None
    description: str | None = None
    priority: str | None = Field(default=None, examples=["HIGH"])
    title: str | None = None
    detail: str | None = None
    severity: str | None = Field(default=None, examples=["high"])
    site: str | None = Field(default=None, examples=["Warehouse 4 — Gate 4"])
    category: str | None = None
    image_url: str | None = Field(default=None, examples=["https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d"])


class EventIngestResponse(BaseModel):
    status: Literal["INGESTED"] = "INGESTED"
    event_id: str


class ReasonRequest(BaseModel):
    utterance: str = Field(examples=["Why is margin down in Region B?"])
    org_id: str = DEFAULT_ORG_ID
    session_id: str | None = None
    execute: bool = True


class ReasonApiResponse(BaseModel):
    intent: str
    tool: str
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    voice_summary: str
    source: Literal["bedrock", "seeded"]
    payloads: DualPayload | None = None


OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness for the Core Business Engine."},
    {"name": "orchestration", "description": "Domain tools that emit a dual Alexa + Fire TV payload."},
    {"name": "briefings", "description": "Current executive workstation briefing."},
    {"name": "events", "description": "Ring / site operational event ingest."},
    {"name": "reasoning", "description": "Bedrock Converse or seeded utterance → tool mapping."},
    {"name": "admin", "description": "Token-protected scenario reset."},
]

ORCHESTRATE_DESCRIPTION = """
Run one executive domain tool and return synchronized **voice_summary** + **visual_state_model** payloads.

| tool_name | parameters |
| --- | --- |
| `get_executive_brief` | _(none)_ |
| `explain_metric_change` | `metric_name`, `dimension`, `window` |
| `get_pending_decisions` | `risk_level?`, `session_id` |
| `execute_decision` | `decision_id` or `decision_title`, `choice` (`approve`/`reject`), `session_id` |
| `start_workflow` | `workflow_name` |
| `get_workflow_status` | `workflow_name` |
| `get_recent_events` | `limit?` |
"""
