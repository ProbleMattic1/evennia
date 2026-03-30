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


def pipeline_breakdown_for_character(char) -> tuple[int, int, int]:
    """
    Returns (stored_sites_bid_cr, accrual_this_slot_est_cr, total_cr).
    Same semantics as frontend estimatedPipelineTotalCr (sites storage + in-slot accrual).
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

    pm = _slot_progress(now, current_mining_delivery_slot_start_iso(), int(MINING_DELIVERY_PERIOD))
    pf = _slot_progress(now, current_flora_delivery_slot_start_iso(), int(FLORA_DELIVERY_PERIOD))

    accrual = (
        math.floor(pm * m_cap)
        + math.floor(pf * flora_cap)
        + math.floor(pf * fauna_cap)
    )
    st = int(stored_total)
    return st, accrual, st + accrual


def estimated_pipeline_total_cr_for_character(char) -> int:
    """
    Mirror frontend estimatedPipelineTotalCr: site bid storage only (no plant silo)
    + mining/flora/fauna in-slot accrual estimates.
    """
    _st, _ac, total = pipeline_breakdown_for_character(char)
    return total


def sum_player_pipeline_breakdown_cr() -> tuple[int, int, int, int]:
    """
    Returns (character_count, stored_sites_sum, accrual_this_slot_sum, total_sum).
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
    for obj in qs.iterator():
        if not obj.is_typeclass(Character, exact=False):
            continue
        if obj.key in skip:
            continue
        st, ac, tot = pipeline_breakdown_for_character(obj)
        stored_sum += st
        accrual_sum += ac
        total_sum += tot
        n += 1
    return n, stored_sum, accrual_sum, total_sum
