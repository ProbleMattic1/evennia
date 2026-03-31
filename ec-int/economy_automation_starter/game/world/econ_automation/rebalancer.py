from __future__ import annotations

from dataclasses import dataclass

from .constants import VALID_PHASES


@dataclass(frozen=True)
class RebalanceDecision:
    next_phase: str
    reason: str
    global_price_multiplier: float
    global_upkeep_multiplier: float
    global_payout_multiplier: float



def decide_rebalance(
    *,
    current_phase: str,
    inflation_pressure: float = 0.0,
    treasury_health: float = 0.0,
    passive_payout_pressure: float = 0.0,
) -> RebalanceDecision:
    """
    Very small deterministic policy starter.

    Inputs should be normalized roughly around 0.0 to 1.0 where higher means more pressure.
    This keeps the initial controller understandable and safe.
    """
    phase = current_phase if current_phase in VALID_PHASES else "stable"

    if inflation_pressure >= 0.80 or passive_payout_pressure >= 0.85:
        return RebalanceDecision(
            next_phase="scarcity",
            reason="high inflation or passive payout pressure",
            global_price_multiplier=1.08,
            global_upkeep_multiplier=1.06,
            global_payout_multiplier=0.96,
        )

    if treasury_health < 0.20 and passive_payout_pressure > 0.60:
        return RebalanceDecision(
            next_phase="recession",
            reason="weak treasury with elevated passive payouts",
            global_price_multiplier=0.97,
            global_upkeep_multiplier=1.02,
            global_payout_multiplier=0.94,
        )

    if inflation_pressure < 0.25 and treasury_health > 0.60:
        return RebalanceDecision(
            next_phase="boom",
            reason="healthy treasury and low inflation pressure",
            global_price_multiplier=1.03,
            global_upkeep_multiplier=1.01,
            global_payout_multiplier=1.03,
        )

    return RebalanceDecision(
        next_phase=phase if phase in VALID_PHASES else "stable",
        reason="hold stable policy",
        global_price_multiplier=1.00,
        global_upkeep_multiplier=1.00,
        global_payout_multiplier=1.00,
    )
