"""SQLModel tables for KPIs, metric drivers, decisions, workflows, and operational events."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Column, DateTime, Numeric, Text
from sqlmodel import Field, Relationship, SQLModel

DEFAULT_ORG_ID = "org_acme_corp"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _numeric(precision: int, scale: int, *, nullable: bool = False) -> Column:
    return Column(Numeric(precision, scale), nullable=nullable)


class KPI(SQLModel, table=True):
    __tablename__ = "kpis"

    id: str = Field(primary_key=True)
    org_id: str = Field(index=True)
    metric_key: str = Field(index=True)
    metric_name: str
    dimension: str = Field(index=True)
    current_value: Decimal = Field(sa_column=_numeric(12, 4))
    target_value: Decimal = Field(sa_column=_numeric(12, 4))
    unit: str = Field(default="%")
    period: str = Field(index=True)
    trend: str = Field(default="STABLE")
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    drivers: List["MetricDriver"] = Relationship(back_populates="kpi")


class MetricDriver(SQLModel, table=True):
    __tablename__ = "metric_drivers"

    id: str = Field(primary_key=True)
    kpi_id: str = Field(foreign_key="kpis.id", index=True)
    driver_name: str
    impact_delta: Decimal = Field(sa_column=_numeric(8, 4))
    impact_summary: str = Field(sa_column=Column(Text, nullable=False))
    associated_entity_id: Optional[str] = None
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    kpi: Optional[KPI] = Relationship(back_populates="drivers")


class DecisionItem(SQLModel, table=True):
    __tablename__ = "decision_items"

    id: str = Field(primary_key=True)
    org_id: str = Field(index=True)
    title: str
    category: str
    amount: Optional[Decimal] = Field(default=None, sa_column=_numeric(14, 2, nullable=True))
    currency: str = Field(default="USD")
    risk_level: str = Field(index=True)
    policy_flag: Optional[str] = None
    status: str = Field(default="PENDING", index=True)
    recommended_choice: Optional[str] = Field(default="APPROVE")
    context_summary: str = Field(sa_column=Column(Text, nullable=False))
    risk_analysis_json: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    margin_impact_pts: Optional[Decimal] = Field(default=None, sa_column=_numeric(8, 4, nullable=True))
    downtime_daily_usd: Optional[Decimal] = Field(default=None, sa_column=_numeric(14, 2, nullable=True))
    downtime_days: Optional[int] = None
    liability_override_usd: Optional[Decimal] = Field(default=None, sa_column=_numeric(14, 2, nullable=True))
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    audit_logs: List["DecisionAuditLog"] = Relationship(back_populates="decision")


class DecisionAuditLog(SQLModel, table=True):
    __tablename__ = "decision_audit_logs"

    id: str = Field(primary_key=True)
    decision_id: str = Field(foreign_key="decision_items.id", index=True)
    user_id: str
    action_taken: str
    channel_source: str
    comment: Optional[str] = None
    session_id: Optional[str] = Field(default=None, index=True)
    risk_tier: Optional[str] = None
    gate_turn_count: int = Field(default=0)
    persona: Optional[str] = None
    challenge_prompt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    user_response: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    is_unlocked: bool = Field(default=False)
    executed_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    decision: Optional[DecisionItem] = Relationship(back_populates="audit_logs")


class WorkflowInstance(SQLModel, table=True):
    __tablename__ = "workflow_instances"

    id: str = Field(primary_key=True)
    org_id: str = Field(index=True)
    workflow_type: str
    title: str
    current_step_number: int = Field(default=1)
    total_steps: int
    status: str = Field(default="IN_PROGRESS", index=True)
    target_completion_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    steps: List["WorkflowStep"] = Relationship(back_populates="workflow")


class WorkflowStep(SQLModel, table=True):
    __tablename__ = "workflow_steps"

    id: str = Field(primary_key=True)
    workflow_id: str = Field(foreign_key="workflow_instances.id", index=True)
    step_number: int = Field(index=True)
    title: str
    assigned_owner: str
    status: str = Field(default="NOT_STARTED")
    blocker_reason: Optional[str] = None
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    workflow: Optional[WorkflowInstance] = Relationship(back_populates="steps")


class OperationalEvent(SQLModel, table=True):
    __tablename__ = "operational_events"

    id: str = Field(primary_key=True)
    org_id: str = Field(index=True)
    source: str
    event_type: str
    location: str
    description: str = Field(sa_column=Column(Text, nullable=False))
    priority: str = Field(default="MEDIUM", index=True)
    is_read: bool = Field(default=False, index=True)
    image_url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    occurred_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
