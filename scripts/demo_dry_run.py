"""Run the five-question demo twice against an isolated seed. No model calls."""

from __future__ import annotations

from sqlmodel import Session, create_engine

from core_data_layer.models import DEFAULT_ORG_ID, DecisionItem
from core_data_layer.seed import seed_data
from core_engine.llm import reason_from_utterance
from core_engine.services import OrchestrationService

QUESTIONS = (
    "Give me today's brief.",
    "Why is margin down in Region B?",
    "What decisions need me?",
    "Approve the spot purchase.",
    "Why is the month-end close blocked?",
)


def _run_once(label: str) -> None:
    bind = create_engine("sqlite://", connect_args={"check_same_thread": False})
    seed_data(bind)
    with Session(bind) as session:
        service = OrchestrationService(session)
        for utterance in QUESTIONS:
            reasoned = reason_from_utterance(utterance)
            if reasoned.source != "seeded":
                raise SystemExit(f"{label}: {utterance} did not stay on the seeded reasoner")
            payload = service.process_tool_request(
                reasoned.tool,
                DEFAULT_ORG_ID,
                {**reasoned.tool_arguments, "session_id": f"{label}-session"},
            )
            if "error" in payload:
                raise SystemExit(f"{label}: {utterance} failed: {payload['error']}")
            voice = payload["voice_summary"]["narration_text"]
            print(f"[{label}] {utterance} -> {voice}")
        spot = session.get(DecisionItem, "dec_004")
        if spot is None or spot.status != "PENDING":
            raise SystemExit(f"{label}: spot purchase must stay pending after the challenge")
    print(f"{label}: ok")


def main() -> None:
    _run_once("run-1")
    _run_once("run-2")
    print("Two consecutive dry runs passed.")


if __name__ == "__main__":
    main()
