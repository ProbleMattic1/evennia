"""
Per-character and world-sum pipeline estimates (bid-valued site storage + in-slot accrual).

Mirrors frontend ``estimatedPipelineTotalCr`` / stream accruals in
``frontend/aurnom/lib/economy-dashboard-derive.ts``. Not wallet credits.
"""

from __future__ import annotations

import math

from world.mining_site_metrics import owned_production_sites_for_dashboard
from world.time import (
    FLORA_DELIVERY_PERIOD,
    MINING_DELIVERY_PERIOD,
    current_flora_delivery_slot_start_iso,
    current_mining_delivery_slot_start_iso,
    parse_iso,
    utc_now,
    utc_timestamp,
)


def _slot_progress(now, slot_start_iso: str, period_sec: int) -> float:
    """Mirror frontend deliverySlotProgress (0..1)."""
    if not slot_start_iso or period_sec <= 0:
        return 0.0
    start = parse_iso(slot_start_iso)
    if not start:
        return 0.0
    start_ms = utc_timestamp(start) * 1000.0
    end_ms = start_ms + period_sec * 1000.0
    denom = end_ms - start_ms
    if denom <= 0:
        return 0.0
    now_ms = utc_timestamp(now.astimezone(start.tzinfo)) * 1000.0
    t = (now_ms - start_ms) / denom
    return min(1.0, max(0.0, t))


def _implied_accrual_cr_per_sec(m_cap: int, flora_cap: int, fauna_cap: int) -> float:
    """Continuous-time rate: mining cap / mining period + (flora+fauna) cap / flora period."""
    m_period = float(int(MINING_DELIVERY_PERIOD))
    f_period = float(int(FLORA_DELIVERY_PERIOD))
    rate = 0.0
    if m_period > 0:
        rate += m_cap / m_period
    if f_period > 0:
        rate += (flora_cap + fauna_cap) / f_period
    return rate


def pipeline_breakdown_for_character(char) -> tuple[int, int, int, float]:
    """
    Returns (stored_sites_bid_cr, accrual_this_slot_est_cr, total_cr, implied_accrual_cr_per_sec).

    ``accrual_this_slot_est_cr`` is linear within the UTC slot (for snapshots that need grid progress).
    ``implied_accrual_cr_per_sec`` is wall-clock rate from cycle caps / delivery periods (not slot-bound).
    Same stored/total semantics as frontend estimatedPipelineTotalCr.
    """
    now = utc_now()
    resources, _cycle_total, stored_total = owned_production_sites_for_dashboard(char)

    m_cap = 0
    flora_cap = 0
    fauna_cap = 0
    for r in resources:
        sk = r.get("siteKind")
        ac = int(r.get("accrualValuePerCycle") or 0)
        if sk == "flora":
            flora_cap += ac
        elif sk == "fauna":
            fauna_cap += ac
        else:
            m_cap += ac

    implied = _implied_accrual_cr_per_sec(m_cap, flora_cap, fauna_cap)

    pm = _slot_progress(now, current_mining_delivery_slot_start_iso(), int(MINING_DELIVERY_PERIOD))
    pf = _slot_progress(now, current_flora_delivery_slot_start_iso(), int(FLORA_DELIVERY_PERIOD))

    accrual = (
        math.floor(pm * m_cap)
        + math.floor(pf * flora_cap)
        + math.floor(pf * fauna_cap)
    )
    st = int(stored_total)
    return st, accrual, st + accrual, implied


def estimated_pipeline_total_cr_for_character(char) -> int:
    """
    Mirror frontend estimatedPipelineTotalCr: site bid storage only (no plant silo)
    + mining/flora/fauna in-slot accrual estimates.
    """
    _st, _ac, total, _rate = pipeline_breakdown_for_character(char)
    return total


def sum_player_pipeline_breakdown_cr() -> tuple[int, int, int, int, float]:
    """
    Returns (character_count, stored_sites_sum, accrual_this_slot_sum, total_sum,
             implied_accrual_cr_per_sec_sum).

    Exclude NPC / service chars — reuse the same key filters as bootstrap_character_abilities.
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.characters import (
        Character,
        MARCUS_CHARACTER_KEY,
        NANOMEGA_ADVERTISING_CHARACTER_KEY,
        NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
        NANOMEGA_REALTY_CHARACTER_KEY,
    )

    skip = {
        MARCUS_CHARACTER_KEY,
        NANOMEGA_REALTY_CHARACTER_KEY,
        NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
        NANOMEGA_ADVERTISING_CHARACTER_KEY,
    }

    qs = ObjectDB.objects.filter(db_typeclass_path__icontains="characters.Character")
    n = 0
    stored_sum = 0
    accrual_sum = 0
    total_sum = 0
    implied_rate_sum = 0.0
    for obj in qs.iterator():
        if not obj.is_typeclass(Character, exact=False):
            continue
        if obj.key in skip:
            continue
        st, ac, tot, implied = pipeline_breakdown_for_character(obj)
        stored_sum += st
        accrual_sum += ac
        total_sum += tot
        implied_rate_sum += implied
        n += 1
    return n, stored_sum, accrual_sum, total_sum, implied_rate_sum
