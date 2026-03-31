from __future__ import annotations

BASELINE_DAILY_INCOME = 2000
HUSTLE_DAILY_INCOME = 5000
DEFAULT_BLENDED_DAILY_INCOME = 3000

DEFAULT_GLOBAL_PRICE_MULTIPLIER = 1.0
DEFAULT_GLOBAL_UPKEEP_MULTIPLIER = 1.0
DEFAULT_GLOBAL_PAYOUT_MULTIPLIER = 1.0

DEFAULT_PHASE = "stable"
VALID_PHASES = frozenset({"boom", "stable", "scarcity", "recession"})

SECONDS_PER_DAY = 86400.0

PRICE_BAND_DEFAULTS = {
    "trivial": {"min_days": 0.05, "max_days": 0.25},
    "light": {"min_days": 0.50, "max_days": 1.00},
    "moderate": {"min_days": 2.00, "max_days": 5.00},
    "meaningful": {"min_days": 7.00, "max_days": 20.00},
    "major": {"min_days": 30.00, "max_days": 90.00},
    "elite": {"min_days": 120.00, "max_days": 240.00},
    "endgame": {"min_days": 300.00, "max_days": 600.00},
}

CATEGORY_DEFAULT_DAYS = {
    "food": 0.10,
    "consumable": 0.15,
    "tool_basic": 0.75,
    "gear_advanced": 3.0,
    "kiosk": 5.0,
    "automated_vendor": 8.0,
    "property_pod": 12.0,
    "property_apartment": 25.0,
    "property_house": 60.0,
    "claim_small": 14.0,
    "claim_medium": 40.0,
    "claim_large": 90.0,
    "vehicle_personal": 10.0,
    "ship_light": 45.0,
    "ship_industrial": 120.0,
    "ship_capital": 400.0,
}

CATEGORY_MULTIPLIERS = {
    "food": 1.00,
    "consumable": 1.00,
    "tool_basic": 1.00,
    "gear_advanced": 1.10,
    "kiosk": 1.00,
    "automated_vendor": 1.15,
    "property_pod": 1.00,
    "property_apartment": 1.05,
    "property_house": 1.12,
    "claim_small": 1.00,
    "claim_medium": 1.08,
    "claim_large": 1.18,
    "vehicle_personal": 1.00,
    "ship_light": 1.20,
    "ship_industrial": 1.35,
    "ship_capital": 1.80,
}

PHASE_PRICE_MULTIPLIERS = {
    "boom": 1.08,
    "stable": 1.00,
    "scarcity": 1.18,
    "recession": 0.94,
}

PHASE_PAYOUT_MULTIPLIERS = {
    "boom": 1.05,
    "stable": 1.00,
    "scarcity": 0.96,
    "recession": 0.92,
}

PHASE_UPKEEP_MULTIPLIERS = {
    "boom": 1.02,
    "stable": 1.00,
    "scarcity": 1.10,
    "recession": 0.98,
}
