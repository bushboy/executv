"""Data access for metric briefings, decisions, workflows, and operational events."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from core_data_layer.models import (
    DEFAULT_ORG_ID,
    KPI,
    DecisionAuditLog,
    DecisionItem,
    MetricDriver,
    OperationalEvent,
    WorkflowInstance,
    WorkflowStep,
    utcnow,
)


class BriefingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_kpis_for_org(self, org_id: str = DEFAULT_ORG_ID) -> list[KPI]:
        statement = (
            select(KPI)
            .where(KPI.org_id == org_id)
            .options(selectinload(KPI.drivers))
            .order_by(col(KPI.dimension))
        )
        return list(self.session.exec(statement).all())

    def get_kpi_by_dimension(
        self,
        org_id: str,
        metric_key: str,
        dimension: str,
        period: str,
    ) -> KPI | None:
        statement = (
            select(KPI)
            .where(KPI.org_id == org_id)
            .where(KPI.metric_key == metric_key)
            .where(KPI.dimension == dimension)
            .where(KPI.period == period)
            .options(selectinload(KPI.drivers))
        )
        return self.session.exec(statement).first()

    def find_kpi(self, metric_name: str, *, org_id: str = DEFAULT_ORG_ID) -> KPI | None:
        needle = metric_name.strip().lower()
        for kpi in self.get_kpis_for_org(org_id):
            haystack = f"{kpi.metric_key} {kpi.metric_name} {kpi.dimension}".lower()
            if needle in haystack or kpi.metric_key.lower() in needle:
                return kpi
        return self.session.exec(select(KPI).where(KPI.org_id == org_id)).first()

    def get_metric_drivers(self, kpi_id: str) -> list[MetricDriver]:
        statement = select(MetricDriver).where(MetricDriver.kpi_id == kpi_id)
        return list(self.session.exec(statement).all())


class DecisionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_pending_decisions(
        self,
        org_id: str = DEFAULT_ORG_ID,
        risk_level: str | None = None,
    ) -> list[DecisionItem]:
        statement = (
            select(DecisionItem)
            .where(DecisionItem.org_id == org_id)
            .where(DecisionItem.status == "PENDING")
            .order_by(col(DecisionItem.amount).desc())
        )
        if risk_level:
            statement = statement.where(DecisionItem.risk_level == risk_level.upper())
        return list(self.session.exec(statement).all())

    def get_by_status(self, org_id: str, status: str) -> list[DecisionItem]:
        statement = (
            select(DecisionItem)
            .where(DecisionItem.org_id == org_id)
            .where(DecisionItem.status == status)
            .order_by(col(DecisionItem.amount).desc())
        )
        return list(self.session.exec(statement).all())

    def get(self, decision_id: str) -> DecisionItem | None:
        return self.session.get(DecisionItem, decision_id)

    def find(self, decision_id: str | None = None, decision_title: str | None = None) -> DecisionItem | None:
        if decision_id:
            return self.get(decision_id)
        needle = (decision_title or "").lower()
        if not needle:
            return None
        statement = select(DecisionItem)
        for item in self.session.exec(statement).all():
            if needle in item.title.lower() or needle in item.id.lower():
                return item
        aliases = {
            "spot": "dec_004",
            "procurement": "dec_004",
            "msa": "dec_003",
            "liability": "dec_003",
            "sla": "dec_001",
            "license": "dec_002",
            "renewal": "dec_002",
        }
        for key, item_id in aliases.items():
            if key in needle:
                return self.get(item_id)
        return None

    def find_gate(self, session_id: str, decision_id: str) -> DecisionAuditLog | None:
        statement = (
            select(DecisionAuditLog)
            .where(DecisionAuditLog.session_id == session_id)
            .where(DecisionAuditLog.decision_id == decision_id)
            .order_by(col(DecisionAuditLog.executed_at).desc())
        )
        return self.session.exec(statement).first()

    def open_gate(
        self,
        *,
        decision_id: str,
        session_id: str,
        user_id: str,
        risk_tier: str,
        gate_turn_count: int,
        persona: str | None,
        challenge_prompt: str,
        channel_source: str,
    ) -> DecisionAuditLog:
        audit = DecisionAuditLog(
            id=f"audit_{decision_id}_{uuid4().hex[:10]}",
            decision_id=decision_id,
            user_id=user_id,
            action_taken="GATE_OPEN",
            channel_source=channel_source,
            session_id=session_id,
            risk_tier=risk_tier,
            gate_turn_count=gate_turn_count,
            persona=persona,
            challenge_prompt=challenge_prompt,
            is_unlocked=False,
        )
        self.session.add(audit)
        self.session.commit()
        self.session.refresh(audit)
        return audit

    def commit_decision(
        self,
        decision_id: str,
        user_id: str,
        choice: str,
        channel_source: str,
        comment: str | None = None,
        *,
        session_id: str | None = None,
        risk_tier: str | None = None,
        gate_turn_count: int = 0,
        persona: str | None = None,
        challenge_prompt: str | None = None,
        user_response: str | None = None,
        existing_gate: DecisionAuditLog | None = None,
    ) -> DecisionItem | None:
        decision = self.session.get(DecisionItem, decision_id)
        if decision is None:
            return None

        status_action = "APPROVED" if choice.strip().lower() in {"approve", "approved", "yes", "confirm"} else "REJECTED"
        decision.status = status_action
        decision.updated_at = utcnow()
        self.session.add(decision)

        if existing_gate is not None:
            existing_gate.action_taken = status_action
            existing_gate.comment = comment
            existing_gate.user_response = user_response or comment
            existing_gate.is_unlocked = True
            existing_gate.risk_tier = risk_tier or existing_gate.risk_tier
            self.session.add(existing_gate)
        else:
            audit = DecisionAuditLog(
                id=f"audit_{decision_id}_{uuid4().hex[:10]}",
                decision_id=decision_id,
                user_id=user_id,
                action_taken=status_action,
                channel_source=channel_source,
                comment=comment,
                session_id=session_id,
                risk_tier=risk_tier,
                gate_turn_count=gate_turn_count,
                persona=persona,
                challenge_prompt=challenge_prompt,
                user_response=user_response,
                is_unlocked=True,
            )
            self.session.add(audit)
        self.session.commit()
        self.session.refresh(decision)
        return decision

    def execute_decision(
        self,
        decision_id: str,
        user_id: str,
        choice: str,
        channel_source: str,
        comment: str | None = None,
    ) -> DecisionItem | None:
        return self.commit_decision(
            decision_id,
            user_id,
            choice,
            channel_source,
            comment,
        )


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_workflow_by_id(self, workflow_id: str) -> WorkflowInstance | None:
        statement = (
            select(WorkflowInstance)
            .where(WorkflowInstance.id == workflow_id)
            .options(selectinload(WorkflowInstance.steps))
        )
        return self.session.exec(statement).first()

    def find(self, workflow_name: str, *, org_id: str = DEFAULT_ORG_ID) -> WorkflowInstance | None:
        needle = workflow_name.strip().lower()
        statement = (
            select(WorkflowInstance)
            .where(WorkflowInstance.org_id == org_id)
            .options(selectinload(WorkflowInstance.steps))
        )
        if not needle:
            return None
        workflows = list(self.session.exec(statement).all())

        def _norm(value: str) -> str:
            return value.lower().replace("-", " ").replace("_", " ")

        normalized = _norm(needle)
        words = [word for word in normalized.split() if word]
        for workflow in workflows:
            blob = _norm(f"{workflow.id} {workflow.title} {workflow.workflow_type} {workflow.status}")
            if normalized in blob or (words and all(word in blob for word in words)):
                return workflow
        return None

    def get_workflow_steps(self, workflow_id: str) -> list[WorkflowStep]:
        statement = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(col(WorkflowStep.step_number))
        )
        return list(self.session.exec(statement).all())

    def start(self, workflow_name: str) -> WorkflowInstance | None:
        workflow = self.find(workflow_name)
        if workflow is None:
            return None
        if workflow.status in {"COMPLETED", "BLOCKED"}:
            return workflow
        workflow.status = "IN_PROGRESS"
        workflow.updated_at = utcnow()
        current = next(
            (step for step in sorted(workflow.steps, key=lambda item: item.step_number) if step.step_number == workflow.current_step_number),
            None,
        )
        if current is not None and current.status == "NOT_STARTED":
            current.status = "IN_PROGRESS"
            current.updated_at = utcnow()
            self.session.add(current)
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)
        return workflow


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_recent_events(self, org_id: str = DEFAULT_ORG_ID, limit: int = 5) -> list[OperationalEvent]:
        statement = (
            select(OperationalEvent)
            .where(OperationalEvent.org_id == org_id)
            .order_by(col(OperationalEvent.occurred_at).desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def create_event(self, event: OperationalEvent) -> OperationalEvent:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
