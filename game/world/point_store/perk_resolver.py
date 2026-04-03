"""Aggregate equipped point-store perks (opaque; server-only).

Stacking: for each stat, take the *product* of that field over equipped perk ids that
exist in perk_defs. Missing defs are skipped. Invalid floats raise ValueError.

Semantics:
- Fee / tax / cost multipliers apply to the *charged* rate or amount (e.g. processing
  fee rate × product). Effective *rates* that must stay in [0, 1] as a fraction of gross
  are clamped after applying the product (see clamped_fee_rate).
- miningDepletionMult: multiply depletion_rate by this product (each factor ≤ 1 slows
  depletion).
- hazardRaidStealMult: multiply raid steal fraction by product (each ≤ 1 reduces theft).
- hazardGeoFloorMult: each factor in (0, 1]; P = product(P). Raise geological floor:
  effective_min = GEO_MIN + (1 - GEO_MIN) * (1 - P). P=1 → unchanged; smaller P →
  higher floor (less severe events).
"""

from __future__ import annotations

from typing import Any

from world.point_store.perk_defs_loader import get_perk_def


def _challenges(character):
    try:
        return character.challenges
    except Exception:
        return None


def _product_over_equipped(character, key: str) -> float:
    ch = _challenges(character)
    if ch is None:
        return 1.0
    m = 1.0
    for pid in ch.equipped_perk_ids():
        d = get_perk_def(pid)
        if not d:
            continue
        try:
            m *= float(d.get(key) or 1.0)
        except (TypeError, ValueError):
            raise ValueError(f"perk_defs {key} invalid for perk {pid!r}")
    return m


def mining_output_multiplier(character) -> float:
    """Product of miningOutputMult from equipped perks. Default 1.0."""
    return _product_over_equipped(character, "miningOutputMult")


def processing_fee_multiplier(character) -> float:
    return _product_over_equipped(character, "processingFeeMult")


def raw_sale_fee_multiplier(character) -> float:
    return _product_over_equipped(character, "rawSaleFeeMult")


def extraction_tax_multiplier(character) -> float:
    return _product_over_equipped(character, "extractionTaxMult")


def mining_depletion_multiplier(character) -> float:
    return _product_over_equipped(character, "miningDepletionMult")


def hazard_raid_steal_multiplier(character) -> float:
    return _product_over_equipped(character, "hazardRaidStealMult")


def hazard_geo_floor_params(character, geo_min: float, geo_max: float) -> tuple[float, float]:
    """
    Return (effective_min, geo_max) for geological hazard scaling.
    Rolls still use uniform[effective_min, geo_max].
    """
    p = hazard_geo_floor_multiplier_product(character)
    p = max(0.0, min(1.0, p))
    lo = float(geo_min)
    hi = float(geo_max)
    eff_min = lo + (1.0 - lo) * (1.0 - p)
    eff_min = max(lo, min(hi, eff_min))
    return eff_min, hi


def hazard_geo_floor_multiplier_product(character) -> float:
    """Product of hazardGeoFloorMult (each in (0,1]); used for floor blend."""
    return _product_over_equipped(character, "hazardGeoFloorMult")


def rig_wear_gain_multiplier(character) -> float:
    return _product_over_equipped(character, "rigWearGainMult")


def mission_credits_multiplier(character) -> float:
    return _product_over_equipped(character, "missionCreditsMult")


def challenge_points_multiplier(character) -> float:
    return _product_over_equipped(character, "challengePointsMult")


def challenge_credits_multiplier(character) -> float:
    return _product_over_equipped(character, "challengeCreditsMult")


def refining_batch_output_multiplier(character) -> float:
    return _product_over_equipped(character, "refiningBatchOutputMult")


def rig_repair_cost_multiplier(character) -> float:
    return _product_over_equipped(character, "rigRepairCostMult")


def property_incident_bonus_multiplier(character) -> float:
    return _product_over_equipped(character, "propertyIncidentBonusMult")


def mining_license_fee_multiplier(character) -> float:
    return _product_over_equipped(character, "miningLicenseFeeMult")


def clamped_fee_rate(base_rate: float, mult_product: float) -> float:
    """effective_rate = base_rate * mult_product, clamped to [0, 1]."""
    r = float(base_rate) * float(mult_product)
    return max(0.0, min(1.0, r))


def aggregate_modifiers(character) -> dict[str, Any]:
    """Diagnostic bundle for logging/tests; not for web clients."""
    return {
        "miningOutputMult": mining_output_multiplier(character),
        "processingFeeMult": processing_fee_multiplier(character),
        "rawSaleFeeMult": raw_sale_fee_multiplier(character),
        "extractionTaxMult": extraction_tax_multiplier(character),
        "miningDepletionMult": mining_depletion_multiplier(character),
        "hazardRaidStealMult": hazard_raid_steal_multiplier(character),
        "hazardGeoFloorMult": hazard_geo_floor_multiplier_product(character),
        "rigWearGainMult": rig_wear_gain_multiplier(character),
        "missionCreditsMult": mission_credits_multiplier(character),
        "challengePointsMult": challenge_points_multiplier(character),
        "challengeCreditsMult": challenge_credits_multiplier(character),
        "refiningBatchOutputMult": refining_batch_output_multiplier(character),
        "rigRepairCostMult": rig_repair_cost_multiplier(character),
        "propertyIncidentBonusMult": property_incident_bonus_multiplier(character),
        "miningLicenseFeeMult": mining_license_fee_multiplier(character),
        "equippedPerks": (
            list(character.challenges.equipped_perk_ids())
            if _challenges(character)
            else []
        ),
    }
