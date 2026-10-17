"""Five golden questions. They pass with the model switched off."""

from decimal import Decimal
from pathlib import Path

from sqlmodel import select

from core_data_layer.models import DEFAULT_ORG_ID, KPI, DecisionItem, MetricDriver
from core_engine.llm import reason_from_utterance

ORG_ID = DEFAULT_ORG_ID
RETIRED_PHRASES = ("revenue up 8%", "$4.2M MTD", "discounts over 12%")

ROOT = Path(__file__).resolve().parents[1]


def _narration(payload: dict) -> str:
    voice = payload["voice_summary"]["narration_text"]
    assert isinstance(voice, str)
    for phrase in RETIRED_PHRASES:
        assert phrase not in voice
    return voice


def _run(service, utterance: str, session_id: str = "golden"):
    reasoned = reason_from_utterance(utterance)
    assert reasoned.source == "seeded"
    arguments = {**reasoned.tool_arguments, "session_id": session_id}
    payload = service.process_tool_request(reasoned.tool, ORG_ID, arguments)
    assert "error" not in payload
    return reasoned, payload


def test_seed_math_and_retired_phrases_are_gone(session):
    seed_text = (ROOT / "packages/core_data_layer/src/core_data_layer/seed.py").read_text(encoding="utf-8")
    for phrase in RETIRED_PHRASES:
        assert phrase not in seed_text
    for token in ("18.3000", "-3.1000", "-1.1000", "1240.5000"):
        assert token in seed_text
    margin = session.exec(select(KPI).where(KPI.metric_key == "margin")).one()
    assert margin.current_value == Decimal("18.3000")
    assert margin.target_value == Decimal("22.5000")
    drivers = session.exec(select(MetricDriver).where(MetricDriver.kpi_id == margin.id)).all()
    assert len(drivers) == 2
    impacts = sorted(driver.impact_delta for driver in drivers)
    assert impacts == [Decimal("-3.1000"), Decimal("-1.1000")]
    spot = session.get(DecisionItem, "dec_004")
    assert spot is not None
    assert spot.margin_impact_pts == Decimal("-0.8000")
    assert spot.downtime_daily_usd == Decimal("350000.00")
    assert spot.downtime_days == 4
    assert spot.downtime_daily_usd * spot.downtime_days == Decimal("1400000.00")
    schema = (ROOT / "apps/core_engine/src/core_engine/schemas.py").read_text(encoding="utf-8")
    ring_script = (ROOT / "scripts/seed_ring_events.py").read_text(encoding="utf-8")
    assert "Gate B" not in schema
    assert "drv_003" not in seed_text
    assert "Gate 4" in ring_script
    assert "Warehouse Dock" not in ring_script


def test_give_me_todays_brief(service):
    _, payload = _run(service, "Give me today's brief.")
    voice = _narration(payload)
    assert "$1.24B" in voice
    assert "$1.30B" in voice
    assert "4.6%" in voice
    assert "18.3%" in voice
    assert "20.0%" in voice
    assert "Gate 4" in voice


def test_why_is_margin_down(service):
    _, payload = _run(service, "Why is margin down in Region B?")
    voice = _narration(payload)
    assert "-3.1" in voice
    assert "-1.1" in voice
    assert "Supplier X" in voice
    assert "Gate 4" in voice
    assert "-0.4" not in voice
    components = payload["visual_state_model"]["components"]
    drivers = next(item for item in components if item["type"] == "DRIVER_BREAKDOWN_LIST")
    assert len(drivers["items"]) == 2


def test_what_decisions_need_me(service):
    _, payload = _run(service, "What decisions need me?")
    voice = _narration(payload)
    assert "$1.2M" in voice
    assert "$450k" in voice
    assert "Auto-approved" in voice
    assert "$12k" in voice
    assert "$4.5k" in voice
    items = payload["visual_state_model"]["components"][0]["items"]
    pending = [item for item in items if item["status"] == "PENDING"]
    assert {item["id"] for item in pending} == {"dec_003", "dec_004"}


def test_approve_the_spot_purchase_opens_the_gate(service, session):
    _, payload = _run(service, "Approve the spot purchase.", session_id="golden-spot")
    voice = _narration(payload)
    assert voice.startswith("CFO Flag:")
    assert "$1.2M" in voice
    spot = session.get(DecisionItem, "dec_004")
    assert spot is not None
    session.refresh(spot)
    assert spot.status == "PENDING"
    assert payload["visual_state_model"].get("layout") != "audit"


def test_why_is_the_month_end_close_blocked(service):
    _, payload = _run(service, "Why is the month-end close blocked?")
    voice = _narration(payload)
    assert "Gate 4" in voice
    assert "physical audit" in voice.lower() or "Physical" in voice
    assert "Ring" in voice
