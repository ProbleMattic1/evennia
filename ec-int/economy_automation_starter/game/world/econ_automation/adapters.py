from __future__ import annotations

from .pricing import quote_category_price



def _phase_from_controller(controller) -> str:
    if not controller:
        return "stable"
    return getattr(controller.db, "phase", None) or "stable"



def _global_price_multiplier(controller) -> float:
    if not controller:
        return 1.0
    return float(getattr(controller.db, "global_price_multiplier", 1.0) or 1.0)



def price_shop_template(obj, controller=None, *, category: str = "consumable", region_multiplier: float = 1.0) -> int:
    quote = quote_category_price(
        category,
        region_multiplier=region_multiplier,
        phase=_phase_from_controller(controller),
        global_multiplier=_global_price_multiplier(controller),
    )
    return quote.final_price



def price_property_listing(obj, controller=None, *, category: str = "property_apartment", region_multiplier: float = 1.0) -> int:
    quote = quote_category_price(
        category,
        region_multiplier=region_multiplier,
        phase=_phase_from_controller(controller),
        global_multiplier=_global_price_multiplier(controller),
    )
    return quote.final_price



def price_claim_listing(obj, controller=None, *, category: str = "claim_small", region_multiplier: float = 1.0) -> int:
    quote = quote_category_price(
        category,
        region_multiplier=region_multiplier,
        phase=_phase_from_controller(controller),
        global_multiplier=_global_price_multiplier(controller),
    )
    return quote.final_price



def price_vehicle_listing(obj, controller=None, *, category: str = "vehicle_personal", region_multiplier: float = 1.0) -> int:
    quote = quote_category_price(
        category,
        region_multiplier=region_multiplier,
        phase=_phase_from_controller(controller),
        global_multiplier=_global_price_multiplier(controller),
    )
    return quote.final_price
