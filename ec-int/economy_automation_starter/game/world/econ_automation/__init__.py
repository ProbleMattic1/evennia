"""Economy automation support package for the Evennia game."""

from .pricing import (
    blended_daily_income,
    credits_from_days,
    price_band_for_days,
    suggested_days_for_category,
)
from .settlement import settle_passive_income_asset
from .bootstrap import bootstrap_economy_automation

__all__ = [
    "blended_daily_income",
    "credits_from_days",
    "price_band_for_days",
    "suggested_days_for_category",
    "settle_passive_income_asset",
    "bootstrap_economy_automation",
]
