from __future__ import annotations

from .adapters import price_property_listing, price_shop_template, price_vehicle_listing
from .constants import CATEGORY_DEFAULT_DAYS


def _automation_controller():
    from typeclasses.economy_automation import get_economy_automation_controller

    return get_economy_automation_controller(create_missing=False)


def _region_multiplier_for_room(econ, room) -> float:
    return float(econ.get_region_modifier(room) or 1.0)


def resolve_catalog_item_price(
    template,
    *,
    buyer,
    room,
    market_type: str = "normal",
    vendor=None,
):
    """
    If ``template.db.econ_automation_category`` is set to a known automation
    category, price via automation; otherwise ``EconomyEngine.get_final_price``.
    """
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    raw = getattr(getattr(template, "db", None), "econ_automation_category", None)
    cat = (str(raw).strip() if raw is not None else "") or None
    if cat and cat in CATEGORY_DEFAULT_DAYS:
        controller = _automation_controller()
        region = _region_multiplier_for_room(econ, room)
        return max(1, int(price_shop_template(template, controller, category=cat, region_multiplier=region)))
    return econ.get_final_price(
        template,
        buyer=buyer,
        location=room,
        market_type=market_type,
    )


def _vehicle_econ_automation_category(template) -> str:
    raw = getattr(getattr(template, "db", None), "econ_automation_category", None)
    if raw and str(raw).strip():
        c = str(raw).strip()
        if c in CATEGORY_DEFAULT_DAYS:
            return c
    economy = getattr(template.db, "economy", None) or {}
    band = (economy.get("economy_band") or "").lower()
    if any(x in band for x in ("capital", "dreadnought", "flagship", "titan")):
        return "ship_capital"
    if any(x in band for x in ("industrial", "heavy", "freighter", "bulk", "hauler")):
        return "ship_industrial"
    if any(x in band for x in ("personal", "light", "shuttle", "starter")):
        return "ship_light"
    tier = str(economy.get("acquisition_tier") or "").lower()
    if tier in ("iv", "4", "v", "5", "vi", "6", "elite", "endgame"):
        return "ship_capital"
    if tier in ("iii", "3"):
        return "ship_industrial"
    try:
        p = int(economy.get("total_price_cr") or economy.get("base_price_cr") or 0)
    except (TypeError, ValueError):
        p = 0
    if p >= 1_500_000:
        return "ship_capital"
    if p >= 350_000:
        return "ship_industrial"
    return "ship_light"


def resolve_vehicle_listing_price(template, *, room, buyer=None, vendor=None) -> int:
    """
    Automation price from inferred (or explicit) ship category, clamped to at
    least the catalog CSV price so list/buy/UI stay aligned and never undercut
    static sheet values.
    """
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    controller = _automation_controller()
    region = _region_multiplier_for_room(econ, room)
    cat = _vehicle_econ_automation_category(template)
    auto = int(price_vehicle_listing(template, controller, category=cat, region_multiplier=region))
    economy = getattr(template.db, "economy", None) or {}
    csv_raw = economy.get("total_price_cr") or economy.get("base_price_cr")
    try:
        csv_int = int(csv_raw) if csv_raw is not None else None
    except (TypeError, ValueError):
        csv_int = None
    if csv_int is None or csv_int <= 0:
        return max(1, auto)
    return max(1, max(auto, csv_int))


def _legacy_lot_listing_price(lot):
    from typeclasses.property_lots import TIER_LIST_PRICES, ZONE_MULTIPLIERS

    tier = int(lot.db.lot_tier or 1)
    zone = lot.db.zone or "residential"
    base = TIER_LIST_PRICES.get(tier, 5_000)
    mult = ZONE_MULTIPLIERS.get(zone, 1.00)
    return int(round(base * mult))


def resolve_property_lot_listing_price(lot) -> int:
    """
    Tier→property category mapping plus zone multiplier as automation
    ``region_multiplier``; unknown explicit category falls back to legacy
    tier×zone table.
    """
    from typeclasses.property_lots import ZONE_MULTIPLIERS

    raw = getattr(getattr(lot, "db", None), "econ_automation_category", None)
    cat = (str(raw).strip() if raw is not None else "") or None
    tier = int(lot.db.lot_tier or 1)
    zone = (lot.db.zone or "residential").lower()
    mult = float(ZONE_MULTIPLIERS.get(zone, 1.0))
    if not cat:
        if tier >= 3:
            cat = "property_house"
        elif tier == 2:
            cat = "property_apartment"
        else:
            cat = "property_pod"
    if cat not in CATEGORY_DEFAULT_DAYS:
        return _legacy_lot_listing_price(lot)
    controller = _automation_controller()
    return max(1, int(price_property_listing(lot, controller, category=cat, region_multiplier=mult)))


def claim_listing_base_price_cr(site) -> int:
    """
    Buyer-agnostic EV×hazard listing (no macro phase); used by claim market
    and phase scaling.
    """
    from typeclasses.mining import get_commodity_bid

    deposit = site.db.deposit or {}
    comp = deposit.get("composition") or {}
    richness = float(deposit.get("richness", 0) or 0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)
    hazard = float(site.db.hazard_level or 0)
    total_tons = base_tons * richness
    ev = 0.0
    for k, frac in comp.items():
        ev += total_tons * float(frac) * float(get_commodity_bid(k))
    hazard_factor = max(0.55, min(1.0, 1.0 - 0.35 * hazard))
    return int(max(500, round(ev * 4 * hazard_factor)))


def resolve_claim_listing_price_cr(site) -> int:
    """``claim_listing_base_price_cr`` × current automation phase price multiplier."""
    from .constants import PHASE_PRICE_MULTIPLIERS

    base = claim_listing_base_price_cr(site)
    controller = _automation_controller()
    phase = getattr(controller.db, "phase", "stable") if controller else "stable"
    scale = float(PHASE_PRICE_MULTIPLIERS.get(phase, 1.0))
    return int(max(500, round(base * scale)))
