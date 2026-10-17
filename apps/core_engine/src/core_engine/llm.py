"""Bedrock Converse intent extraction with a seeded fallback for offline judging."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from core_engine.config import get_settings
from core_engine.policy import PLAYBOOK_PROMPT

CORE_EXECUTIVE_TOOLS = (
    "get_executive_brief",
    "explain_metric_change",
    "get_pending_decisions",
    "execute_decision",
    "start_workflow",
    "get_workflow_status",
    "get_recent_events",
)

_SYSTEM = f"""You are the ExecuTV reasoning engine for an Alexa+ / Fire TV executive workstation.
{PLAYBOOK_PROMPT}
Map the executive's utterance to exactly one MCP tool from this list:
- get_executive_brief
- explain_metric_change (args: metric_name, dimension?, window?)
- get_pending_decisions
- execute_decision (args: decision_id or decision_title, choice=approve|reject)
- start_workflow (args: workflow_name)
- get_workflow_status (args: workflow_name)
- get_recent_events (args: limit?)
Return JSON only:
{{"tool": "...", "tool_arguments": {{}}, "intent": "...", "voice_summary": "one spoken sentence"}}
voice_summary must be couch-friendly, under 40 words, no markdown.
The risk tier is already decided in code. Do not invent a different tier.
"""


class ReasonResponse(BaseModel):
    intent: str
    tool: str
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    voice_summary: str
    source: Literal["bedrock", "seeded"]


def _fallback(utterance: str) -> ReasonResponse:
    text = utterance.lower()
    if any(word in text for word in ("spot", "spot purchase", "procurement")) and any(
        word in text for word in ("approve", "confirm", "yes", "decline", "reject")
    ):
        action = "reject" if any(word in text for word in ("reject", "decline", "no-go", "no go")) else "approve"
        return ReasonResponse(
            intent="execute_decision",
            tool="execute_decision",
            tool_arguments={"choice": action, "decision_title": "spot procurement", "decision_id": "dec_004"},
            voice_summary="I'll take the emergency spot procurement through the challenge gate.",
            source="seeded",
        )
    if any(word in text for word in ("month-end", "month end", "close blocked", "physical audit")):
        return ReasonResponse(
            intent="get_workflow_status",
            tool="get_workflow_status",
            tool_arguments={"workflow_name": "month-end close"},
            voice_summary="I'll check why the month-end close is blocked.",
            source="seeded",
        )
    if any(word in text for word in ("approve", "reject", "execute decision", "sign off")):
        action = "reject" if "reject" in text or "no-go" in text or "no go" in text else "approve"
        return ReasonResponse(
            intent="execute_decision",
            tool="execute_decision",
            tool_arguments={"choice": action, "decision_title": utterance},
            voice_summary=f"I'll {action} the outstanding decision and update the Fire TV surface.",
            source="seeded",
        )
    if any(word in text for word in ("workflow", "rfq", "12345", "kick off", "start the", "run playbook")):
        return ReasonResponse(
            intent="start_workflow",
            tool="start_workflow",
            tool_arguments={"workflow_name": "RFQ Response"},
            voice_summary="I'll pull up RFQ response 12345 on the television.",
            source="seeded",
        )
    if any(word in text for word in ("ring", "alert", "delivery", "dock", "event", "what's happening", "whats happening")):
        return ReasonResponse(
            intent="get_recent_events",
            tool="get_recent_events",
            tool_arguments={"limit": 5},
            voice_summary="I'll pull the latest site and delivery alerts onto the television.",
            source="seeded",
        )
    if any(word in text for word in ("decision", "pending", "need me", "go/no-go", "go no go")):
        return ReasonResponse(
            intent="get_pending_decisions",
            tool="get_pending_decisions",
            tool_arguments={},
            voice_summary="Here are the decisions still waiting on you.",
            source="seeded",
        )
    if any(word in text for word in ("margin", "region b", "supplier", "metric", "why did", "what changed")):
        return ReasonResponse(
            intent="explain_metric_change",
            tool="explain_metric_change",
            tool_arguments={"metric_name": "margin", "dimension": "Region B", "window": "Q3-2026"},
            voice_summary="I'll explain the Region B margin move from the seed drivers.",
            source="seeded",
        )
    return ReasonResponse(
        intent="get_executive_brief",
        tool="get_executive_brief",
        tool_arguments={},
        voice_summary="Here's your executive brief, with the board agenda on the television.",
        source="seeded",
    )


def _parse_model_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(0)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Bedrock did not return a JSON object")
    return data


def converse_text(system: str, user: str) -> str:
    """Call Bedrock Converse. Raises on timeout, access errors, or missing credentials."""
    import boto3
    from botocore.config import Config

    settings = get_settings()
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.bedrock_region,
        config=Config(
            connect_timeout=3,
            read_timeout=settings.bedrock_timeout_seconds,
            retries={"max_attempts": 1},
        ),
    )
    response = client.converse(
        modelId=settings.bedrock_model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.1},
    )
    parts = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise RuntimeError("Bedrock returned an empty completion")
    return text


def reason_from_utterance(utterance: str) -> ReasonResponse:
    """Extract MCP tool + arguments and a spoken voice_summary."""
    fallback = _fallback(utterance)
    settings = get_settings()
    if settings.llm_provider != "bedrock":
        return fallback

    try:
        data = _parse_model_json(converse_text(_SYSTEM, f"Utterance:\n{utterance}"))
        tool = str(data.get("tool") or fallback.tool)
        if tool not in CORE_EXECUTIVE_TOOLS:
            tool = fallback.tool
        arguments = data.get("tool_arguments") or {}
        if not isinstance(arguments, dict):
            arguments = fallback.tool_arguments
        voice_summary = str(data.get("voice_summary") or fallback.voice_summary)
        intent = str(data.get("intent") or tool)
        return ReasonResponse(
            intent=intent,
            tool=tool,
            tool_arguments=arguments,
            voice_summary=voice_summary,
            source="bedrock",
        )
    except Exception:  # noqa: BLE001 — always degrade to seeded reasoning
        return fallback


def narrate_audit(decision_context: str) -> str | None:
    """Optional Bedrock wording for the audit card. None means use the seeded card."""
    settings = get_settings()
    if settings.llm_provider != "bedrock":
        return None
    try:
        return converse_text(
            f"You write one sentence for an executive audit card. {PLAYBOOK_PROMPT}",
            decision_context,
        )
    except Exception:  # noqa: BLE001
        return None
