from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    CATEGORY_DEFAULT_DAYS,
    CATEGORY_MULTIPLIERS,
    DEFAULT_BLENDED_DAILY_INCOME,
    DEFAULT_GLOBAL_PRICE_MULTIPLIER,
    PHASE_PRICE_MULTIPLIERS,
    PRICE_BAND_DEFAULTS,
)


@dataclass(frozen=True)
class PriceQuote:
    category: str
    target_days: float
    blended_daily_income: int
    category_multiplier: float
    region_multiplier: float
    phase_multiplier: float
    global_multiplier: float
    final_price: int


def blended_daily_income(custom_value: int | None = None) -> int:
    value = custom_value or DEFAULT_BLENDED_DAILY_INCOME
    return max(1, int(value))


def suggested_days_for_category(category: str, fallback: float = 1.0) -> float:
    return float(CATEGORY_DEFAULT_DAYS.get(category, fallback))


def category_multiplier(category: str) -> float:
    return float(CATEGORY_MULTIPLIERS.get(category, 1.0))


def price_band_for_days(days: float) -> str:
    days = float(max(0.0, days))
    for band, bounds in PRICE_BAND_DEFAULTS.items():
        if bounds["min_days"] <= days <= bounds["max_days"]:
            return band
    if days < PRICE_BAND_DEFAULTS["trivial"]["min_days"]:
        return "trivial"
    return "endgame"


def credits_from_days(
    days: float,
    *,
    category: str = "generic",
    region_multiplier: float = 1.0,
    phase: str = "stable",
    blended_income: int | None = None,
    global_multiplier: float = DEFAULT_GLOBAL_PRICE_MULTIPLIER,
) -> PriceQuote:
    target_days = max(0.0, float(days))
    income = blended_daily_income(blended_income)
    c_mult = category_multiplier(category)
    r_mult = max(0.01, float(region_multiplier or 1.0))
    p_mult = float(PHASE_PRICE_MULTIPLIERS.get(phase, 1.0))
    g_mult = max(0.01, float(global_multiplier or 1.0))

    final_price = round(target_days * income * c_mult * r_mult * p_mult * g_mult)
    final_price = max(1, int(final_price))

    return PriceQuote(
        category=category,
        target_days=target_days,
        blended_daily_income=income,
        category_multiplier=c_mult,
        region_multiplier=r_mult,
        phase_multiplier=p_mult,
        global_multiplier=g_mult,
        final_price=final_price,
    )


def quote_category_price(
    category: str,
    *,
    region_multiplier: float = 1.0,
    phase: str = "stable",
    blended_income: int | None = None,
    global_multiplier: float = DEFAULT_GLOBAL_PRICE_MULTIPLIER,
) -> PriceQuote:
    days = suggested_days_for_category(category)
    return credits_from_days(
        days,
        category=category,
        region_multiplier=region_multiplier,
        phase=phase,
        blended_income=blended_income,
        global_multiplier=global_multiplier,
    )
