"""Dual-Payload Formatter: one voice summary + one Fire TV visual state model."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from core_data_layer.models import (
    KPI,
    DecisionItem,
    MetricDriver,
    OperationalEvent,
    WorkflowInstance,
    WorkflowStep,
)
from core_engine.policy import MARGIN_FLOOR


def _pct(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _money(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _kpi_display(value: Decimal | None, unit: str) -> str:
    if value is None:
        return "N/A"
    if unit == "%":
        return f"{value:.1f}%"
    if unit.upper().startswith("M USD") and value >= Decimal("1000"):
        return f"${(value / Decimal('1000')):.2f}B"
    return f"{value:,.1f} {unit}".strip()


def _risk_analysis(decision: DecisionItem) -> dict[str, Any] | None:
    raw = decision.risk_analysis_json
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _decision_item(item: DecisionItem) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "amount": _money(item.amount),
        "risk_level": item.risk_level,
        "status": item.status,
        "recommendation": item.recommended_choice,
        "context_summary": item.context_summary,
        "policy_flag": item.policy_flag,
    }
    analysis = _risk_analysis(item)
    if analysis:
        payload["risk_analysis"] = analysis
    return payload


def _high_alert(events: list[OperationalEvent]) -> OperationalEvent | None:
    for event in events:
        if event.priority.upper() == "HIGH":
            return event
    return events[0] if events else None


class DualPayloadFormatter:
    """Transforms domain records into synchronized Alexa narration and Fire TV UI state."""

    @staticmethod
    def envelope(
        *,
        narration_text: str,
        suggested_followups: list[str],
        view_id: str,
        header_title: str,
        badge_status: str,
        components: list[dict[str, Any]],
        highlight_target_id: str | None = None,
        extra_visual: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        visual: dict[str, Any] = {
            "view_id": view_id,
            "header_title": header_title,
            "badge_status": badge_status,
            "components": components,
        }
        if highlight_target_id:
            visual["highlight_target_id"] = highlight_target_id
        if extra_visual:
            visual.update(extra_visual)
        return {
            "voice_summary": {
                "narration_text": narration_text,
                "suggested_followups": suggested_followups,
            },
            "visual_state_model": visual,
        }

    @staticmethod
    def format_executive_brief(kpis: list[KPI], events: list[OperationalEvent]) -> dict[str, Any]:
        revenue = next((kpi for kpi in kpis if kpi.metric_key == "revenue"), None)
        margin = next((kpi for kpi in kpis if kpi.metric_key == "margin"), None)
        if revenue is not None and revenue.target_value:
            gap = (revenue.target_value - revenue.current_value) / revenue.target_value * Decimal("100")
            revenue_sentence = (
                f"Q3 revenue is {_kpi_display(revenue.current_value, revenue.unit)} versus "
                f"{_kpi_display(revenue.target_value, revenue.unit)} target, {gap:.1f}% under target."
            )
        else:
            revenue_sentence = "Q3 revenue is unavailable."
        if margin is not None:
            floor = f"{MARGIN_FLOOR:.1f}%"
            relation = "below" if margin.current_value < MARGIN_FLOOR else "above"
            margin_sentence = f" Region B margin is {_pct(margin.current_value)}, {relation} the {floor} floor."
        else:
            margin_sentence = ""
        alert = _high_alert(events)
        event_alert = f" {alert.description}" if alert else ""
        voice_text = f"{revenue_sentence}{margin_sentence}{event_alert}"
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=[
                "Why is margin down in Region B?",
                "Show me my pending decisions.",
                "Are there any warehouse alerts?",
            ],
            view_id="EXECUTIVE_BRIEF",
            header_title="Executive Workstation Briefing",
            badge_status="ATTENTION_REQUIRED" if events else "HEALTHY",
            extra_visual={"layout": "briefing", "highlighted_card_id": margin.id if margin is not None else None},
            highlight_target_id=margin.id if margin is not None else None,
            components=[
                {
                    "id": "kpi_grid",
                    "type": "KPI_GRID",
                    "items": [
                        {
                            "id": kpi.id,
                            "metric": kpi.metric_name,
                            "dimension": kpi.dimension,
                            "value": _kpi_display(kpi.current_value, kpi.unit),
                            "target": _kpi_display(kpi.target_value, kpi.unit),
                            "trend": kpi.trend,
                        }
                        for kpi in kpis
                    ],
                },
                {
                    "id": "live_alerts",
                    "type": "ALERTS_TIMELINE",
                    "items": [
                        {
                            "id": event.id,
                            "location": event.location,
                            "description": event.description,
                            "priority": event.priority,
                            "source": event.source,
                            "event_type": event.event_type,
                            "image_url": event.image_url,
                            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                        }
                        for event in events
                    ],
                },
            ],
        )

    @staticmethod
    def format_metric_explanation(kpi: KPI, drivers: list[MetricDriver]) -> dict[str, Any]:
        ordered = sorted(drivers, key=lambda item: abs(item.impact_delta), reverse=True)
        if ordered:
            driver_text = "; ".join(
                f"{driver.driver_name} {driver.impact_delta:+.1f} pts" for driver in ordered
            )
            voice_text = (
                f"{kpi.metric_name} in {kpi.dimension} is {_pct(kpi.current_value)} "
                f"against a {_pct(kpi.target_value)} target. Drivers: {driver_text}."
            )
        else:
            voice_text = f"{kpi.metric_name} in {kpi.dimension} is {_pct(kpi.current_value)}."
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=[
                "Do you want to review supplier contract decisions?",
                "Escalate this variance to operations.",
            ],
            view_id="ANALYSIS_DEEP_DIVE",
            header_title=f"{kpi.dimension} {kpi.metric_name} Variance",
            badge_status="CRITICAL_ATTENTION",
            highlight_target_id="card_primary_driver",
            extra_visual={"layout": "briefing", "highlighted_card_id": "card_primary_driver"},
            components=[
                {
                    "id": "kpi_summary_card",
                    "type": "METRIC_CARD",
                    "title": kpi.metric_name,
                    "value": _pct(kpi.current_value),
                    "target": _pct(kpi.target_value),
                    "trend": kpi.trend,
                },
                {
                    "id": "card_primary_driver",
                    "type": "DRIVER_BREAKDOWN_LIST",
                    "title": "Primary Variance Drivers",
                    "items": [
                        {
                            "id": driver.id,
                            "driver": driver.driver_name,
                            "impact": _pct(driver.impact_delta),
                            "summary": driver.impact_summary,
                        }
                        for driver in ordered
                    ],
                },
            ],
        )

    @staticmethod
    def format_pending_decisions(
        decisions: list[DecisionItem],
        auto_approved: list[DecisionItem] | None = None,
    ) -> dict[str, Any]:
        from core_engine.policy import compact_money, spoken_name

        approved = auto_approved or []
        if decisions:
            pending_bits = ", ".join(
                f"{item.title} at {compact_money(item.amount)} ({item.risk_level.lower()} risk)"
                for item in decisions
            )
            voice_text = f"Decisions that need you: {pending_bits}."
        else:
            voice_text = "No decisions are waiting on you."
        if approved:
            approved_bits = " and ".join(
                f"{spoken_name(item)} for {compact_money(item.amount)}" for item in approved
            )
            voice_text += f" Auto-approved under delegated authority: {approved_bits}."
        count = len(decisions)
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=["Approve all low-risk items.", "Show details for item 1."],
            view_id="DECISIONS_LIST",
            header_title="Pending Executive Approvals",
            badge_status="PENDING_ACTION" if count else "HEALTHY",
            extra_visual={"layout": "decision"},
            components=[
                {
                    "id": "decisions_list",
                    "type": "DECISION_CARD_LIST",
                    "items": [_decision_item(item) for item in [*decisions, *approved]],
                }
            ],
        )

    @staticmethod
    def format_decision_execution(
        executed_decision: DecisionItem,
        voice_text: str | None = None,
    ) -> dict[str, Any]:
        voice_text = voice_text or (
            f"Successfully updated {executed_decision.title} status to {executed_decision.status}."
        )
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=["Show remaining pending decisions."],
            view_id="DECISIONS_LIST",
            header_title="Decision Updated",
            badge_status="SUCCESS",
            highlight_target_id=executed_decision.id,
            extra_visual={
                "updated_item": {
                    "id": executed_decision.id,
                    "title": executed_decision.title,
                    "status": executed_decision.status,
                }
            },
            components=[
                {
                    "id": "decisions_list",
                    "type": "DECISION_CARD_LIST",
                    "items": [_decision_item(executed_decision)],
                }
            ],
        )

    @staticmethod
    def format_workflow(
        workflow: WorkflowInstance,
        steps: list[WorkflowStep] | None = None,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        ordered = sorted(steps or list(workflow.steps), key=lambda item: item.step_number)
        current = next((step for step in ordered if step.step_number == workflow.current_step_number), None)
        blocked = next((step for step in ordered if step.status == "BLOCKED"), None)
        voice_text = (
            f"{workflow.title} is {workflow.status.replace('_', ' ').lower()}, "
            f"step {workflow.current_step_number} of {workflow.total_steps}"
        )
        if blocked is not None:
            voice_text += f": {blocked.title}."
            if blocked.blocker_reason:
                voice_text += f" {blocked.blocker_reason}."
        elif current is not None:
            voice_text += f": {current.title}, owned by {current.assigned_owner}."
        else:
            voice_text += "."
        if evidence:
            voice_text += f" {evidence}"
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=["Show the executive brief.", "What is blocking pricing review?"],
            view_id="WORKFLOW_TRACKER",
            header_title=workflow.title,
            badge_status="IN_PROGRESS" if workflow.status == "IN_PROGRESS" else workflow.status,
            highlight_target_id=current.id if current else None,
            components=[
                {
                    "id": "workflow_steps",
                    "type": "WORKFLOW_STEP_LIST",
                    "items": [
                        {
                            "id": step.id,
                            "step_number": step.step_number,
                            "title": step.title,
                            "owner": step.assigned_owner,
                            "status": step.status,
                            "blocker_reason": step.blocker_reason,
                        }
                        for step in ordered
                    ],
                }
            ],
        )

    @staticmethod
    def format_gate(
        decision: DecisionItem,
        *,
        voice_text: str,
        persona: str | None,
    ) -> dict[str, Any]:
        return DualPayloadFormatter.envelope(
            narration_text=voice_text,
            suggested_followups=["Confirm the decision.", "Decline the decision."],
            view_id="DECISIONS_LIST",
            header_title="Challenge Gate",
            badge_status=decision.risk_level,
            highlight_target_id=decision.id,
            extra_visual={
                "layout": "decision",
                "highlighted_card_id": decision.id,
                "deferred_audit": decision.risk_level == "HIGH",
                "decision_id": decision.id,
            },
            components=[
                {
                    "id": "decisions_list",
                    "type": "DECISION_CARD_LIST",
                    "items": [_decision_item(decision)],
                },
                {
                    "id": "challenge_prompt",
                    "type": "CHALLENGE_PROMPT",
                    "title": persona or "Policy",
                    "items": [{"id": "challenge_prompt", "body": voice_text, "persona": persona or ""}],
                },
            ],
        )

    @staticmethod
    def format_audit(decision: DecisionItem) -> dict[str, Any]:
        from core_engine.policy import compact_money, downtime_total, riskiest_assumption

        assumption = riskiest_assumption(decision)
        total = downtime_total(decision)
        justifiable = total is not None and decision.amount is not None and total > decision.amount
        personas = [
            {
                "id": "persona_cfo",
                "persona": "CFO",
                "verdict": (
                    f"Spend {compact_money(decision.amount)} is justified against {compact_money(total)} downtime risk."
                    if justifiable and total is not None
                    else "Cash impact stays inside the delegated line."
                ),
            },
            {
                "id": "persona_legal",
                "persona": "Legal / Compliance",
                "verdict": "No contract override in this procurement. Liability cap is unchanged.",
            },
            {
                "id": "persona_ops",
                "persona": "Ops Lead",
                "verdict": "Plant shutdown is avoided only if the spot components arrive inside the outage window.",
            },
        ]
        protocol = [
            {"id": "day_1", "title": "Confirm the spot-component delivery slot with Supplier X."},
            {"id": "day_3", "title": "Clear the Gate 4 freight backlog and reopen the physical audit."},
            {"id": "day_7", "title": "Recheck Region B margin after the components are received."},
        ]
        return DualPayloadFormatter.envelope(
            narration_text=assumption,
            suggested_followups=["Confirm the spot purchase.", "Show the month-end close."],
            view_id="AUDIT_SCORECARD",
            header_title="Procurement Audit",
            badge_status="HIGH",
            highlight_target_id="riskiest_assumption",
            extra_visual={"layout": "audit", "highlighted_card_id": "riskiest_assumption", "deferred_audit": False},
            components=[
                {"id": "persona_badges", "type": "PERSONA_BADGE_GRID", "items": personas},
                {
                    "id": "riskiest_assumption",
                    "type": "RISKIEST_ASSUMPTION",
                    "title": "Riskiest assumption",
                    "items": [{"id": "riskiest_assumption", "body": assumption}],
                },
                {"id": "seven_day_protocol", "type": "PROTOCOL_CHECKLIST", "items": protocol},
            ],
        )
