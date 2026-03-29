"""
Shared production-site estimates for web dashboards and world telemetry.

Supports MiningSite and FloraSite (shared char.db.owned_sites control surface).
Cycle / stored CR use get_commodity_bid vs get_flora_commodity_bid by site kind.
"""

from __future__ import annotations

from typing import Any

from world.time import FLORA_DELIVERY_PERIOD, MINING_DELIVERY_PERIOD

RESOURCE_KIND_MINING = "mining_site"
RESOURCE_KIND_FLORA = "flora_site"


def site_to_dashboard_row(site) -> tuple[dict[str, Any], int, int] | None:
    """
    Returns (row, cycle_value_cr, stored_value_cr) or None if unusable.
    Supports MiningSite and FloraSite (shared owned_sites dashboard).
    """
    from typeclasses.flora import get_flora_commodity_bid
    from typeclasses.mining import (
        WEAR_OUTPUT_PENALTY,
        _resource_rarity_tier,
        _volume_tier,
        get_commodity_bid,
        rig_output_modifiers,
    )

    if not site or not getattr(site, "db", None):
        return None

    is_flora = bool(getattr(site.db, "is_flora_site", False))

    def raw_bid(resource_key: str, sloc) -> int:
        if is_flora:
            return get_flora_commodity_bid(resource_key, location=sloc)
        return get_commodity_bid(resource_key, location=sloc)

    installed = [r for r in (site.db.rigs or []) if r]
    operational = [r for r in installed if r.db.is_operational]
    active_rig = (
        min(operational, key=lambda r: float(getattr(r.db, "wear", 0) or 0))
        if operational
        else None
    )

    rigs_payload = [
        {
            "key": r.key,
            "wear": int(round(float(getattr(r.db, "wear", 0) or 0) * 100)),
            "operational": bool(getattr(r.db, "is_operational", False)),
        }
        for r in installed
    ]

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
        stored_value_cr += tons * raw_bid(k, sloc)

    base_tons = float(deposit.get("base_output_tons", 0))
    estimated_value = 0.0
    estimated_tons = 0.0
    cycle_value_cr = 0.0

    if site.is_active and active_rig:
        rig_rating = float(active_rig.db.rig_rating or 0)
        wear_mod = 1.0 - (
            float(getattr(active_rig.db, "wear", 0) or 0) * WEAR_OUTPUT_PENALTY
        )
        mode_mod, power_mod = rig_output_modifiers(active_rig)
        total = (
            base_tons
            * richness
            * rig_rating
            * mode_mod
            * power_mod
            * wear_mod
        )
        estimated_tons = total
        for k, frac in raw_comp.items():
            val = total * float(frac) * raw_bid(k, sloc)
            estimated_value += val
            cycle_value_cr += val
    else:
        estimated_tons = base_tons * richness
        for k, frac in raw_comp.items():
            estimated_value += estimated_tons * float(frac) * raw_bid(k, sloc)

    volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
    rarity_tier, rarity_tier_cls = _resource_rarity_tier(raw_comp)

    lic = site.db.license_level
    tax = site.db.tax_rate
    haz = site.db.hazard_level

    delivery_period = int(FLORA_DELIVERY_PERIOD if is_flora else MINING_DELIVERY_PERIOD)
    accrual_cr = int(round(cycle_value_cr))

    row = {
        "id": site.id,
        "key": site.key,
        "kind": RESOURCE_KIND_FLORA if is_flora else RESOURCE_KIND_MINING,
        "siteKind": "flora" if is_flora else "mining",
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
        "rigs": rigs_payload,
        "rig": active_rig.key if active_rig else None,
        "rigWear": (
            int(round(float(getattr(active_rig.db, "wear", 0) or 0) * 100))
            if active_rig
            else None
        ),
        "rigOperational": active_rig.db.is_operational if active_rig else False,
        "storageUsed": round(used, 1),
        "storageCapacity": cap,
        "inventory": inv,
        "licenseLevel": int(lic if lic is not None else 0),
        "taxRate": float(tax if tax is not None else 0.0),
        "hazardLevel": float(haz if haz is not None else 0.0),
        "deliveryPeriodSeconds": delivery_period,
        "accrualValuePerCycle": accrual_cr,
    }
    return row, int(round(cycle_value_cr)), int(round(stored_value_cr))


def owned_production_sites_for_dashboard(char):
    """
    Read model: all char.db.owned_sites suitable for dashboard / control-surface.

    Returns (rows, cycle_value_cr_total, stored_value_cr_total).
    """
    from evennia.utils import logger

    rows: list[dict[str, Any]] = []
    cycle_total = 0.0
    stored_total = 0.0
    for site in char.db.owned_sites or []:
        try:
            packed = site_to_dashboard_row(site)
        except Exception as exc:
            logger.log_err(
                f"[owned_production_sites_for_dashboard] site_to_dashboard_row failed "
                f"site={getattr(site, 'id', '?')} key={getattr(site, 'key', '?')}: {exc}"
            )
            continue
        if not packed:
            continue
        row, cycle_cr, stored_cr = packed
        rows.append(row)
        cycle_total += cycle_cr
        stored_total += stored_cr
    return rows, int(round(cycle_total)), int(round(stored_total))
