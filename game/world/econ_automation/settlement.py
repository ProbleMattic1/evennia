from __future__ import annotations

from dataclasses import dataclass

from world.time import parse_iso, to_iso, utc_now

from .constants import (
    DEFAULT_GLOBAL_PAYOUT_MULTIPLIER,
    DEFAULT_GLOBAL_UPKEEP_MULTIPLIER,
    PHASE_PAYOUT_MULTIPLIERS,
    PHASE_UPKEEP_MULTIPLIERS,
    SECONDS_PER_DAY,
)


@dataclass(frozen=True)
class SettlementResult:
    elapsed_days: float
    gross: int
    upkeep: int
    net: int
    previous_stored: int
    new_stored: int
    settled_at_iso: str



def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def settle_passive_income_asset(
    obj,
    *,
    now=None,
    phase: str = "stable",
    global_payout_multiplier: float = DEFAULT_GLOBAL_PAYOUT_MULTIPLIER,
    global_upkeep_multiplier: float = DEFAULT_GLOBAL_UPKEEP_MULTIPLIER,
) -> SettlementResult:
    """
    Resolve passive earnings from elapsed wall-clock time.

    Required object db fields:
        - base_daily_profit
        - base_upkeep_daily
        - efficiency
        - stored_earnings
        - last_settled_iso

    Optional:
        - automation_enabled
        - max_unclaimed_earnings
        - payout_multiplier
        - upkeep_multiplier
    """
    if getattr(obj.db, "automation_enabled", True) is False:
        current_stored = _safe_int(getattr(obj.db, "stored_earnings", 0), 0)
        now_iso = to_iso(now or utc_now()) or ""
        return SettlementResult(
            elapsed_days=0.0,
            gross=0,
            upkeep=0,
            net=0,
            previous_stored=current_stored,
            new_stored=current_stored,
            settled_at_iso=now_iso,
        )

    now_dt = now or utc_now()
    last_iso = getattr(obj.db, "last_settled_iso", None)
    last_dt = parse_iso(last_iso) or now_dt

    elapsed_seconds = max(0.0, (now_dt - last_dt).total_seconds())
    elapsed_days = elapsed_seconds / SECONDS_PER_DAY

    base_daily_profit = _safe_float(getattr(obj.db, "base_daily_profit", 0.0), 0.0)
    base_upkeep_daily = _safe_float(getattr(obj.db, "base_upkeep_daily", 0.0), 0.0)
    efficiency = max(0.0, _safe_float(getattr(obj.db, "efficiency", 1.0), 1.0))

    local_payout_multiplier = max(0.0, _safe_float(getattr(obj.db, "payout_multiplier", 1.0), 1.0))
    local_upkeep_multiplier = max(0.0, _safe_float(getattr(obj.db, "upkeep_multiplier", 1.0), 1.0))

    phase_payout = _safe_float(PHASE_PAYOUT_MULTIPLIERS.get(phase, 1.0), 1.0)
    phase_upkeep = _safe_float(PHASE_UPKEEP_MULTIPLIERS.get(phase, 1.0), 1.0)

    gross = round(
        elapsed_days * base_daily_profit * efficiency * local_payout_multiplier * phase_payout * global_payout_multiplier
    )
    upkeep = round(
        elapsed_days * base_upkeep_daily * local_upkeep_multiplier * phase_upkeep * global_upkeep_multiplier
    )
    net = max(0, int(gross - upkeep))

    previous_stored = _safe_int(getattr(obj.db, "stored_earnings", 0), 0)
    new_stored = previous_stored + net

    max_unclaimed = getattr(obj.db, "max_unclaimed_earnings", None)
    if max_unclaimed is not None:
        new_stored = min(new_stored, _safe_int(max_unclaimed, new_stored))

    settled_at_iso = to_iso(now_dt) or ""
    obj.db.stored_earnings = new_stored
    obj.db.last_settled_iso = settled_at_iso

    return SettlementResult(
        elapsed_days=elapsed_days,
        gross=int(gross),
        upkeep=int(upkeep),
        net=int(net),
        previous_stored=previous_stored,
        new_stored=new_stored,
        settled_at_iso=settled_at_iso,
    )
