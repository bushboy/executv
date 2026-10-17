"""Playbook tiers and the session-keyed challenge gate, with the model off."""

from core_data_layer.models import DEFAULT_ORG_ID, DecisionItem
from core_engine.formatter import DualPayloadFormatter
from core_engine.policy import CFO_CHALLENGE, MSA_CONFIRM

ORG_ID = DEFAULT_ORG_ID


def _voice(payload: dict) -> str:
    return payload["voice_summary"]["narration_text"]


def test_low_decisions_auto_approve_with_zero_turns(service, session):
    for decision_id, snippet in (("dec_002", "$4.5k"), ("dec_001", "$12k")):
        payload = service.process_tool_request(
            "execute_decision",
            ORG_ID,
            {"decision_id": decision_id, "choice": "approve", "session_id": f"low-{decision_id}"},
        )
        voice = _voice(payload)
        assert "Auto-approved" in voice
        assert snippet in voice
        assert "delegated authority" in voice
        decision = session.get(DecisionItem, decision_id)
        assert decision is not None
        session.refresh(decision)
        assert decision.status == "APPROVED"
        gate = service.decision_repo.find_gate(f"low-{decision_id}", decision_id)
        assert gate is not None
        assert gate.gate_turn_count == 0
        assert gate.is_unlocked is True
        assert gate.risk_tier == "LOW"


def test_medium_msa_waits_for_confirmation(service, session):
    first = service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_003", "choice": "approve", "session_id": "msa-1"},
    )
    assert _voice(first) == MSA_CONFIRM
    decision = session.get(DecisionItem, "dec_003")
    assert decision is not None
    session.refresh(decision)
    assert decision.status == "PENDING"
    gate = service.decision_repo.find_gate("msa-1", "dec_003")
    assert gate is not None
    assert gate.gate_turn_count == 0
    assert gate.is_unlocked is False

    second = service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_003", "choice": "approve", "session_id": "msa-1", "comment": "confirm"},
    )
    session.refresh(decision)
    assert decision.status == "APPROVED"
    assert "approved" in _voice(second).lower()


def test_high_spot_buy_challenges_then_commits_on_the_same_session(service, session):
    first = service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_004", "choice": "approve", "session_id": "spot-a"},
    )
    assert _voice(first) == CFO_CHALLENGE
    assert first["visual_state_model"]["deferred_audit"] is True
    decision = session.get(DecisionItem, "dec_004")
    assert decision is not None
    session.refresh(decision)
    assert decision.status == "PENDING"

    second = service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {
            "decision_id": "dec_004",
            "choice": "approve",
            "session_id": "spot-a",
            "comment": "downtime would exceed the spend",
        },
    )
    session.refresh(decision)
    assert decision.status == "APPROVED"
    gate = service.decision_repo.find_gate("spot-a", "dec_004")
    assert gate is not None
    assert gate.is_unlocked is True
    assert gate.gate_turn_count == 1
    assert "downtime would exceed" in (gate.user_response or "")
    assert "approved" in _voice(second).lower()


def test_a_second_session_does_not_inherit_the_unlock(service, session):
    service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_004", "choice": "approve", "session_id": "spot-a"},
    )
    service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_004", "choice": "approve", "session_id": "spot-b"},
    )
    service.process_tool_request(
        "execute_decision",
        ORG_ID,
        {"decision_id": "dec_004", "choice": "approve", "session_id": "spot-a", "comment": "yes"},
    )
    other = service.decision_repo.find_gate("spot-b", "dec_004")
    assert other is not None
    assert other.is_unlocked is False
    decision = session.get(DecisionItem, "dec_004")
    assert decision is not None
    session.refresh(decision)
    assert decision.status == "APPROVED"


def test_seeded_audit_card_does_not_require_bedrock(session):
    decision = session.get(DecisionItem, "dec_004")
    assert decision is not None
    payload = DualPayloadFormatter.format_audit(decision)
    visual = payload["visual_state_model"]
    assert visual["layout"] == "audit"
    assert visual["highlighted_card_id"] == "riskiest_assumption"
    assert visual["view_id"] == "AUDIT_SCORECARD"
    assert "1.4M" in payload["voice_summary"]["narration_text"]
    personas = visual["components"][0]["items"]
    assert [item["persona"] for item in personas] == ["CFO", "Legal / Compliance", "Ops Lead"]
