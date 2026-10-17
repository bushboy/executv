"""Deterministic playbook. Code chooses the tier; the model never does."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core_data_layer.models import DecisionItem

HIGH_AMOUNT = Decimal("1000000")
MEDIUM_AMOUNT = Decimal("200000")
LIABILITY_THRESHOLD = Decimal("250000")
MARGIN_FLOOR = Decimal("20.0")

CFO_CHALLENGE = (
    "CFO Flag: Approving $1.2M for emergency spot procurement exceeds your $200k delegated limit "
    "and impacts Q3 cash reserves. Have you confirmed that plant downtime costs would exceed $1.2M if declined?"
)
MSA_CONFIRM = (
    "This MSA override increases liability limits to $450k, exceeding the $250k threshold. Confirm execution?"
)


@dataclass(frozen=True)
class PolicyVerdict:
    tier: str
    gate_turns: int
    persona: str | None
    challenge_prompt: str | None
    auto_approve: bool
    requires_confirmation: bool


def _amount(decision: DecisionItem) -> Decimal:
    return decision.amount if decision.amount is not None else Decimal("0")


def _liability(decision: DecisionItem) -> Decimal:
    if decision.liability_override_usd is not None:
        return decision.liability_override_usd
    if decision.category == "POLICY_OVERRIDE" and decision.amount is not None:
        return decision.amount
    return Decimal("0")


def moves_margin_below_floor(decision: DecisionItem, region_margin: Decimal | None) -> bool:
    if region_margin is None or decision.margin_impact_pts is None:
        return False
    return (region_margin + decision.margin_impact_pts) < MARGIN_FLOOR


def compact_money(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    amount = Decimal(value)
    if amount >= Decimal("1000000"):
        scaled = amount / Decimal("1000000")
        text = f"{scaled:.1f}".rstrip("0").rstrip(".")
        return f"${text}M"
    if amount >= Decimal("1000"):
        scaled = amount / Decimal("1000")
        text = f"{scaled:.1f}".rstrip("0").rstrip(".")
        return f"${text}k"
    return f"${amount:.0f}"


def spoken_name(decision: DecisionItem) -> str:
    names = {
        "dec_001": "cloud SLA amendment",
        "dec_002": "software license renewal",
        "dec_003": "MSA override",
        "dec_004": "emergency spot procurement",
    }
    return names.get(decision.id, decision.title)


def low_voice(decision: DecisionItem) -> str:
    return f"Auto-approved {spoken_name(decision)} for {compact_money(decision.amount)} under delegated authority."


def evaluate(decision: DecisionItem, region_margin: Decimal | None = None) -> PolicyVerdict:
    amount = _amount(decision)
    liability = _liability(decision)
    below_floor = moves_margin_below_floor(decision, region_margin)
    if amount >= HIGH_AMOUNT or below_floor:
        persona = "Legal" if decision.category == "POLICY_OVERRIDE" else "CFO"
        prompt = MSA_CONFIRM if persona == "Legal" and amount < HIGH_AMOUNT else CFO_CHALLENGE
        if decision.id != "dec_004" and persona == "CFO":
            prompt = (
                f"CFO Flag: Approving {compact_money(amount)} exceeds your $200k delegated limit. "
                "Confirm that the downside of declining is larger than the spend?"
            )
        return PolicyVerdict(
            tier="HIGH",
            gate_turns=1,
            persona=persona,
            challenge_prompt=prompt,
            auto_approve=False,
            requires_confirmation=True,
        )
    if amount >= MEDIUM_AMOUNT or liability > LIABILITY_THRESHOLD:
        return PolicyVerdict(
            tier="MEDIUM",
            gate_turns=0,
            persona="Legal",
            challenge_prompt=MSA_CONFIRM
            if decision.id == "dec_003"
            else (
                f"This {spoken_name(decision)} is {compact_money(amount)}, "
                f"above the {compact_money(LIABILITY_THRESHOLD)} threshold. Confirm execution?"
            ),
            auto_approve=False,
            requires_confirmation=True,
        )
    return PolicyVerdict(
        tier="LOW",
        gate_turns=0,
        persona=None,
        challenge_prompt=None,
        auto_approve=True,
        requires_confirmation=False,
    )


def downtime_total(decision: DecisionItem) -> Decimal | None:
    if decision.downtime_daily_usd is None or not decision.downtime_days:
        return None
    return decision.downtime_daily_usd * Decimal(decision.downtime_days)


def riskiest_assumption(decision: DecisionItem) -> str:
    total = downtime_total(decision)
    if total is not None and decision.downtime_daily_usd is not None:
        daily = compact_money(decision.downtime_daily_usd)
        return (
            f"Assumes plant shutdown costs exceed {daily} per day over a "
            f"{decision.downtime_days}-day outage window ({compact_money(total)} total risk)"
        )
    return "Assumes the stated playbook thresholds still match the signed delegation."


PLAYBOOK_PROMPT = (
    "Playbook, already decided in code: margin floor 20.0%, "
    "liability threshold $250k, high-risk line $1M. "
    "Do not change the risk tier. Narrate only the numbers you are given."
)
