"""Wipe and load the 4-scene AcroCorp Global Technologies scenario."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, delete

from core_data_layer.database import engine as default_engine
from core_data_layer.models import (
    KPI,
    DecisionAuditLog,
    DecisionItem,
    MetricDriver,
    OperationalEvent,
    WorkflowInstance,
    WorkflowStep,
    utcnow,
)

ORG_ID = "org_acme_corp"


def seed_data(bind: Engine | None = None) -> None:
    from core_data_layer import models as _models  # noqa: F401

    target = bind or default_engine
    SQLModel.metadata.drop_all(target)
    SQLModel.metadata.create_all(target)
    with Session(target) as session:
        for model in (
            DecisionAuditLog,
            MetricDriver,
            WorkflowStep,
            KPI,
            DecisionItem,
            WorkflowInstance,
            OperationalEvent,
        ):
            session.exec(delete(model))
        session.commit()

        now = utcnow()

        # Scene A: Global Executive Metrics (AcroCorp Global)
        session.add_all(
            [
                KPI(
                    id="kpi_margin_reg_b",
                    org_id=ORG_ID,
                    metric_key="margin",
                    metric_name="Margin %",
                    dimension="Region B",
                    current_value=Decimal("18.3000"),
                    target_value=Decimal("22.5000"),
                    unit="%",
                    period="Q3-2026",
                    trend="DOWN",
                ),
                KPI(
                    id="kpi_revenue_q3",
                    org_id=ORG_ID,
                    metric_key="revenue",
                    metric_name="Q3 Revenue",
                    dimension="Global",
                    current_value=Decimal("1240.5000"),
                    target_value=Decimal("1300.0000"),
                    unit="M USD",
                    period="Q3-2026",
                    trend="DOWN",
                ),
                KPI(
                    id="kpi_win_rate",
                    org_id=ORG_ID,
                    metric_key="win_rate",
                    metric_name="Enterprise Win Rate",
                    dimension="Global",
                    current_value=Decimal("64.2000"),
                    target_value=Decimal("60.0000"),
                    unit="%",
                    period="Q3-2026",
                    trend="UP",
                ),
                KPI(
                    id="kpi_csat",
                    org_id=ORG_ID,
                    metric_key="csat",
                    metric_name="Executive CSAT",
                    dimension="Global",
                    current_value=Decimal("92.4000"),
                    target_value=Decimal("90.0000"),
                    unit="%",
                    period="Q3-2026",
                    trend="STABLE",
                ),
                KPI(
                    id="kpi_delivery_otd",
                    org_id=ORG_ID,
                    metric_key="delivery_otd",
                    metric_name="On-Time Delivery",
                    dimension="Supply Chain",
                    current_value=Decimal("88.1000"),
                    target_value=Decimal("95.0000"),
                    unit="%",
                    period="Q3-2026",
                    trend="DOWN",
                ),
            ]
        )

        session.add_all(
            [
                MetricDriver(
                    id="drv_001",
                    kpi_id="kpi_margin_reg_b",
                    driver_name="Supplier X Raw Material Price Bump",
                    impact_delta=Decimal("-3.1000"),
                    impact_summary="Raw material cost increase on Component X in Plant 3",
                    associated_entity_id="supp_vendor_x",
                ),
                MetricDriver(
                    id="drv_002",
                    kpi_id="kpi_margin_reg_b",
                    driver_name="Freight Logistics Gate 4 Delay",
                    impact_delta=Decimal("-1.1000"),
                    impact_summary="Emergency rerouting freight surcharges at Gate 4",
                    associated_entity_id="wh_gate_4",
                ),
            ]
        )

        # Scene B: High-Stakes Executive Decisions Room
        session.add_all(
            [
                DecisionItem(
                    id="dec_001",
                    org_id=ORG_ID,
                    title="Vendor A Cloud Infrastructure SLA Amendment",
                    category="CONTRACT_AMENDMENT",
                    amount=Decimal("12000.00"),
                    risk_level="LOW",
                    policy_flag="Within delegated authority",
                    status="AUTO_APPROVED",
                    recommended_choice="APPROVE",
                    context_summary="Adjusts uptime SLA guarantee to 99.99% with no cost increase.",
                    risk_analysis_json=json.dumps(
                        {"financial_risk": "NEGLIGIBLE", "legal_compliance": "VERIFIED"}
                    ),
                ),
                DecisionItem(
                    id="dec_002",
                    org_id=ORG_ID,
                    title="Enterprise AI Workstation Software License Renewal",
                    category="DISCOUNT_REQUEST",
                    amount=Decimal("4500.00"),
                    risk_level="LOW",
                    policy_flag="Pre-approved IT operating expense",
                    status="AUTO_APPROVED",
                    recommended_choice="APPROVE",
                    context_summary="Annual multi-seat software license renewal under delegated authority.",
                    risk_analysis_json=json.dumps(
                        {"financial_risk": "LOW", "budget_status": "APPROVED_CAPEX"}
                    ),
                ),
                DecisionItem(
                    id="dec_003",
                    org_id=ORG_ID,
                    title="Master Services Agreement Liability Cap Override",
                    category="POLICY_OVERRIDE",
                    amount=Decimal("450000.00"),
                    risk_level="MEDIUM",
                    policy_flag="Liability cap override exceeds the $250k playbook threshold",
                    liability_override_usd=Decimal("450000.00"),
                    status="PENDING",
                    recommended_choice="REVIEW",
                    context_summary=(
                        "Requires executive sign-off for liability threshold increase "
                        "for Global Logistics Partner."
                    ),
                    risk_analysis_json=json.dumps(
                        {
                            "financial_risk": "MODERATE",
                            "legal_flag": "Requires Legal Counsel Secondary Review",
                        }
                    ),
                ),
                DecisionItem(
                    id="dec_004",
                    org_id=ORG_ID,
                    title="Spot Market Emergency Component Sourcing",
                    category="PROCUREMENT_OVERRIDE",
                    amount=Decimal("1200000.00"),
                    risk_level="HIGH",
                    policy_flag="30% Unit Cost Premium Surcharge",
                    status="PENDING",
                    recommended_choice="ESCALATE",
                    context_summary=(
                        "Emergency spot purchase of 50,000 Component X units to prevent Plant 3 shutdown."
                    ),
                    margin_impact_pts=Decimal("-0.8000"),
                    downtime_daily_usd=Decimal("350000.00"),
                    downtime_days=4,
                    risk_analysis_json=json.dumps(
                        {
                            "financial_risk": "HIGH",
                            "margin_impact": "-0.8 pts",
                            "downtime_risk": "350k USD per day over 4 days (1.4M total)",
                            "urgency": "CRITICAL",
                        }
                    ),
                ),
            ]
        )

        # Scene C: Multi-step process workflows
        session.add(
            WorkflowInstance(
                id="wf_rfq_12345",
                org_id=ORG_ID,
                workflow_type="RFQ_RESPONSE",
                title="RFQ Response #12345 — Global Logistics Contract",
                current_step_number=3,
                total_steps=5,
                status="IN_PROGRESS",
                target_completion_date=now + timedelta(days=2),
            )
        )
        session.add_all(
            [
                WorkflowStep(
                    id="st_101",
                    workflow_id="wf_rfq_12345",
                    step_number=1,
                    title="Ingest RFQ Document & Technical Specifications",
                    assigned_owner="Automated Ingress Engine",
                    status="COMPLETED",
                ),
                WorkflowStep(
                    id="st_102",
                    workflow_id="wf_rfq_12345",
                    step_number=2,
                    title="Extract SLA & Legal Requirements",
                    assigned_owner="AI Legal Parser",
                    status="COMPLETED",
                ),
                WorkflowStep(
                    id="st_103",
                    workflow_id="wf_rfq_12345",
                    step_number=3,
                    title="Draft Multi-Tier Pricing Quote",
                    assigned_owner="Sales Operations",
                    status="IN_PROGRESS",
                ),
                WorkflowStep(
                    id="st_104",
                    workflow_id="wf_rfq_12345",
                    step_number=4,
                    title="Margin & Risk Legal Review",
                    assigned_owner="Finance Team",
                    status="NOT_STARTED",
                ),
                WorkflowStep(
                    id="st_105",
                    workflow_id="wf_rfq_12345",
                    step_number=5,
                    title="VP Sales Executive Sign-off",
                    assigned_owner="VP Commercial",
                    status="NOT_STARTED",
                ),
            ]
        )

        session.add(
            WorkflowInstance(
                id="wf_close_q3",
                org_id=ORG_ID,
                workflow_type="MONTH_END_CLOSE",
                title="Q3-2026 Month-End Executive Financial Close",
                current_step_number=3,
                total_steps=4,
                status="BLOCKED",
                target_completion_date=now + timedelta(days=1),
            )
        )
        session.add_all(
            [
                WorkflowStep(
                    id="st_201",
                    workflow_id="wf_close_q3",
                    step_number=1,
                    title="Regional Sub-Ledger Reconciliation",
                    assigned_owner="Accounting Bot",
                    status="COMPLETED",
                ),
                WorkflowStep(
                    id="st_202",
                    workflow_id="wf_close_q3",
                    step_number=2,
                    title="Intercompany Tax & Elimination Checks",
                    assigned_owner="Global Tax AI",
                    status="COMPLETED",
                ),
                WorkflowStep(
                    id="st_203",
                    workflow_id="wf_close_q3",
                    step_number=3,
                    title="Gate 4 Physical Inventory Audit",
                    assigned_owner="Audit Lead",
                    status="BLOCKED",
                    blocker_reason="Gate 4 physical audit blocked by freight backlog",
                ),
                WorkflowStep(
                    id="st_204",
                    workflow_id="wf_close_q3",
                    step_number=4,
                    title="Executive P&L Statement Consolidation",
                    assigned_owner="CFO Office",
                    status="NOT_STARTED",
                ),
            ]
        )

        # Scene D: Operational security & camera feeds (Ring / IoT)
        session.add(
            OperationalEvent(
                id="evt_ring_gate4",
                org_id=ORG_ID,
                source="ring_site_gateway",
                event_type="freight_backlog",
                location="Warehouse 4 — Gate 4",
                description=(
                    "Ring camera at Gate 4 shows a freight truck backlog blocking the physical inventory audit."
                ),
                priority="HIGH",
                is_read=False,
                image_url=(
                    "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d"
                    "?w=800&auto=format&fit=crop"
                ),
                occurred_at=now - timedelta(minutes=12),
            )
        )

        session.commit()
        print("Successfully seeded ExecuTV core database with rich 4-scene corporate scenario dataset!")


def main() -> None:
    seed_data()


if __name__ == "__main__":
    main()
