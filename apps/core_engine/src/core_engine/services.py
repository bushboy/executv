"""Orchestration service: repositories in, DualPayloadFormatter out."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlmodel import Session

from core_data_layer.models import DEFAULT_ORG_ID, OperationalEvent
from core_data_layer.repositories import (
    BriefingRepository,
    DecisionRepository,
    EventRepository,
    WorkflowRepository,
)

from core_engine.formatter import DualPayloadFormatter
from core_engine.policy import evaluate, low_voice

_SOURCE_MAP = {
    "ring": "ring_site_gateway",
    "ring_site_gateway": "ring_site_gateway",
    "delivery": "ring_site_gateway",
    "bee": "bee_wearable",
    "bee_wearable": "bee_wearable",
}
_PRIORITY_MAP = {"high": "HIGH", "info": "MEDIUM", "medium": "MEDIUM", "low": "LOW"}


class OrchestrationService:
    def __init__(self, session: Session) -> None:
        self.briefing_repo = BriefingRepository(session)
        self.decision_repo = DecisionRepository(session)
        self.workflow_repo = WorkflowRepository(session)
        self.event_repo = EventRepository(session)

    def process_tool_request(
        self,
        tool_name: str,
        org_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = parameters or {}
        handlers = {
            "get_executive_brief": self._executive_brief,
            "explain_metric_change": self._explain_metric,
            "get_pending_decisions": self._pending_decisions,
            "execute_decision": self._execute_decision,
            "start_workflow": self._start_workflow,
            "get_workflow_status": self._workflow_status,
            "get_recent_events": self._recent_events,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return {"error": f"Tool '{tool_name}' is not supported by OrchestrationService."}
        return handler(org_id, params)

    def _executive_brief(self, org_id: str, _params: dict[str, Any]) -> dict[str, Any]:
        kpis = self.briefing_repo.get_kpis_for_org(org_id)
        events = self.event_repo.get_recent_events(org_id, limit=3)
        return DualPayloadFormatter.format_executive_brief(kpis, events)

    def _explain_metric(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        metric = str(params.get("metric") or params.get("metric_name") or "margin")
        dimension = str(params.get("dimension") or "Region B")
        period = str(params.get("period") or params.get("window") or "Q3-2026")
        kpi = self.briefing_repo.get_kpi_by_dimension(org_id, metric, dimension, period)
        if kpi is None:
            kpi = self.briefing_repo.find_kpi(metric, org_id=org_id)
        if kpi is None:
            return {"error": f"Metric {metric} for {dimension} not found."}
        drivers = self.briefing_repo.get_metric_drivers(kpi.id)
        return DualPayloadFormatter.format_metric_explanation(kpi, drivers)

    def _pending_decisions(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        risk = params.get("risk_level")
        decisions = self.decision_repo.get_pending_decisions(org_id, risk_level=risk)
        auto_approved = self.decision_repo.get_by_status(org_id, "AUTO_APPROVED")
        return DualPayloadFormatter.format_pending_decisions(decisions, auto_approved)

    def _region_margin(self, org_id: str):
        kpi = self.briefing_repo.get_kpi_by_dimension(org_id, "margin", "Region B", "Q3-2026")
        return kpi.current_value if kpi is not None else None

    def _execute_decision(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        session_id = str(params.get("session_id") or "").strip()
        if not session_id:
            return {"error": "session_id is required"}
        decision = self.decision_repo.find(params.get("decision_id"), params.get("decision_title"))
        if decision is None:
            return {"error": f"Decision {params.get('decision_id') or params.get('decision_title')} not found."}
        choice = str(params.get("choice") or params.get("action") or "approve")
        comment = str(params.get("comment") or params.get("user_response") or "")
        user_id = str(params.get("user_id") or "usr_exec_01")
        verdict = evaluate(decision, self._region_margin(org_id))
        gate = self.decision_repo.find_gate(session_id, decision.id)

        if verdict.auto_approve and (gate is None or gate.is_unlocked):
            executed = self.decision_repo.commit_decision(
                decision.id,
                user_id,
                "approve",
                "alexa_mcp",
                comment or low_voice(decision),
                session_id=session_id,
                risk_tier="LOW",
                gate_turn_count=0,
                existing_gate=None if gate is None or gate.is_unlocked else gate,
            )
            if executed is None:
                return {"error": f"Decision {decision.id} not found."}
            fresh_gate = self.decision_repo.find_gate(session_id, decision.id)
            if fresh_gate is not None and fresh_gate.gate_turn_count != 0:
                fresh_gate.gate_turn_count = 0
                self.decision_repo.session.add(fresh_gate)
                self.decision_repo.session.commit()
            return DualPayloadFormatter.format_decision_execution(executed, low_voice(executed))

        if gate is None or (gate.is_unlocked and decision.status == "PENDING"):
            prompt = verdict.challenge_prompt or "Confirm execution?"
            self.decision_repo.open_gate(
                decision_id=decision.id,
                session_id=session_id,
                user_id=user_id,
                risk_tier=verdict.tier,
                gate_turn_count=verdict.gate_turns,
                persona=verdict.persona,
                challenge_prompt=prompt,
                channel_source="alexa_mcp",
            )
            self.decision_repo.session.refresh(decision)
            return DualPayloadFormatter.format_gate(decision, voice_text=prompt, persona=verdict.persona)

        if not gate.is_unlocked:
            executed = self.decision_repo.commit_decision(
                decision.id,
                user_id,
                choice,
                "alexa_mcp",
                comment or choice,
                session_id=session_id,
                risk_tier=verdict.tier,
                gate_turn_count=gate.gate_turn_count,
                persona=verdict.persona,
                challenge_prompt=gate.challenge_prompt,
                user_response=comment or choice,
                existing_gate=gate,
            )
            if executed is None:
                return {"error": f"Decision {decision.id} not found."}
            voice = (
                f"{executed.title} is now {executed.status.lower()}."
            )
            return DualPayloadFormatter.format_decision_execution(executed, voice)

        return DualPayloadFormatter.format_decision_execution(decision)

    def _start_workflow(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("workflow_name") or params.get("workflow_id") or "").strip()
        if not name:
            return {"error": "workflow_name is required"}
        workflow = self.workflow_repo.start(name)
        if workflow is None:
            return {"error": f"Workflow {name} not found."}
        steps = self.workflow_repo.get_workflow_steps(workflow.id)
        return DualPayloadFormatter.format_workflow(workflow, steps, self._gate4_evidence(org_id))

    def _workflow_status(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("workflow_name") or params.get("workflow_id") or "month-end close").strip()
        workflow = self.workflow_repo.find(name, org_id=org_id)
        if workflow is None:
            return {"error": f"Workflow {name} not found."}
        steps = self.workflow_repo.get_workflow_steps(workflow.id)
        return DualPayloadFormatter.format_workflow(workflow, steps, self._gate4_evidence(org_id))

    def _gate4_evidence(self, org_id: str) -> str | None:
        for event in self.event_repo.get_recent_events(org_id, limit=5):
            blob = f"{event.location} {event.description}".lower()
            if "gate 4" in blob and "ring" in blob:
                return event.description
        return None

    def _recent_events(self, org_id: str, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit") or 5)
        events = self.event_repo.get_recent_events(org_id, limit=limit)
        kpis = self.briefing_repo.get_kpis_for_org(org_id)
        return DualPayloadFormatter.format_executive_brief(kpis, events)

    def ingest_operational_event(self, event_data: dict[str, Any]) -> OperationalEvent:
        title = str(event_data.get("title") or "")
        detail = str(event_data.get("detail") or "")
        description = str(event_data.get("description") or "").strip()
        if not description:
            description = f"{title}. {detail}".strip(". ") if title else "New operational event detected"
        category = str(event_data.get("category") or event_data.get("event_type") or "delivery_detected")
        if "deliver" in f"{title} {category}".lower():
            event_type = "delivery_detected"
        elif category.lower() in {"security", "alert"}:
            event_type = "security_alert"
        else:
            event_type = str(event_data.get("event_type") or category)
        source = str(event_data.get("source") or "ring_site_gateway")
        priority = str(event_data.get("priority") or _PRIORITY_MAP.get(str(event_data.get("severity") or "high").lower(), "HIGH"))
        event = OperationalEvent(
            id=str(event_data.get("id") or f"evt_{uuid4().hex[:12]}"),
            org_id=str(event_data.get("org_id") or DEFAULT_ORG_ID),
            source=_SOURCE_MAP.get(source.lower(), source),
            event_type=event_type,
            location=str(event_data.get("location") or event_data.get("site") or "Warehouse Gate"),
            description=description,
            priority=priority.upper() if priority.upper() in {"LOW", "MEDIUM", "HIGH"} else "HIGH",
            image_url=event_data.get("image_url"),
        )
        return self.event_repo.create_event(event)
