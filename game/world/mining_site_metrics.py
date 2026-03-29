"""
Shared mining-site estimates for web dashboards and world telemetry.
Aligned with control_surface mine rows; cycle CR = active site + operational rig only.
"""

from __future__ import annotations

from typing import Any


def site_to_dashboard_row(site) -> tuple[dict[str, Any], int, int] | None:
    """
    Returns (row, cycle_value_cr, stored_value_cr) or None if unusable.
    """
    from typeclasses.mining import (
        MODE_OUTPUT_MODIFIERS,
        POWER_OUTPUT_MODIFIERS,
        WEAR_OUTPUT_PENALTY,
        _resource_rarity_tier,
        _volume_tier,
        get_commodity_bid,
    )

    if not site or not getattr(site, "db", None):
        return None

    installed = [r for r in (site.db.rigs or []) if r]
    operational = [r for r in installed if r.db.is_operational]
    active_rig = min(operational, key=lambda r: r.db.wear) if operational else None

    storage = site.db.linked_storage
    deposit = site.db.deposit or {}
    richness = float(deposit.get("richness", 0))
    raw_comp = deposit.get("composition") or {}
    comp = {str(k): float(v) for k, v in raw_comp.items()}

    raw_inv = storage.db.inventory if storage else {}
    inv = {str(k): float(v) for k, v in raw_inv.items()}
    cap = float(storage.db.capacity_tons) if storage else 500.0
    used = sum(inv.values()) if inv else 0

    sloc = site.location
    stored_value_cr = 0.0
    for k, tons in inv.items():
        stored_value_cr += tons * get_commodity_bid(k, location=sloc)

    base_tons = float(deposit.get("base_output_tons", 0))
    estimated_value = 0.0
    estimated_tons = 0.0
    cycle_value_cr = 0.0

    if site.is_active and active_rig:
        rig_rating = float(active_rig.db.rig_rating)
        wear_mod = 1.0 - (float(active_rig.db.wear) * WEAR_OUTPUT_PENALTY)
        total = (
            base_tons
            * richness
            * rig_rating
            * MODE_OUTPUT_MODIFIERS[active_rig.db.mode]
            * POWER_OUTPUT_MODIFIERS[active_rig.db.power_level]
            * wear_mod
        )
        estimated_tons = total
        for k, frac in raw_comp.items():
            val = total * float(frac) * get_commodity_bid(k, location=sloc)
            estimated_value += val
            cycle_value_cr += val
    else:
        estimated_tons = base_tons * richness
        for k, frac in raw_comp.items():
            estimated_value += estimated_tons * float(frac) * get_commodity_bid(k, location=sloc)

    volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
    rarity_tier, rarity_tier_cls = _resource_rarity_tier(raw_comp)

    row = {
        "id": site.id,
        "key": site.key,
        "location": sloc.key if sloc else None,
        "active": site.is_active,
        "richness": richness,
        "volumeTier": volume_tier,
        "volumeTierCls": volume_tier_cls,
        "resourceRarityTier": rarity_tier,
        "resourceRarityTierCls": rarity_tier_cls,
        "baseOutputTons": base_tons,
        "estimatedOutputTons": round(estimated_tons, 1),
        "estimatedValuePerCycle": int(round(estimated_value)),
        "composition": comp,
        "nextCycleAt": site.db.next_cycle_at,
        "rig": active_rig.key if active_rig else None,
        "rigWear": int(active_rig.db.wear * 100) if active_rig else None,
        "rigOperational": active_rig.db.is_operational if active_rig else False,
        "storageUsed": round(used, 1),
        "storageCapacity": cap,
        "inventory": inv,
        "licenseLevel": int(site.db.license_level),
        "taxRate": float(site.db.tax_rate),
        "hazardLevel": float(site.db.hazard_level),
    }
    return row, int(round(cycle_value_cr)), int(round(stored_value_cr))
