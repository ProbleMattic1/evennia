"""
Long-window economy predicates (quarter / half-year).

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def economy_modifier_shift(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    The global economy modifier has shifted by at least delta from its default of 1.0.
    Good as a "participate during an event" marker when staff changes the global modifier.
    predicateParams: {"min_delta": 0.05}
    """
    from typeclasses.economy import get_economy
    params = _params(template)
    min_delta = float(params.get("min_delta") or 0.05)
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    current = float((econ.db.state or {}).get("global_modifier") or 1.0)
    return abs(current - 1.0) >= min_delta


def deed_buy_hold_sell(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Bought a deed, held it for at least min_hold_days, then listed or sold it.
    Tracks a simple state machine on character telemetry per window_key.
    predicateParams: {"min_hold_days": 1}
    """
    params = _params(template)
    min_hold_days = int(params.get("min_hold_days") or 1)
    from world.time import parse_iso, utc_now
    tel = handler.telemetry
    deed_buy_iso = tel.get(f"deed_buy_hold_sell_bought_{window_key}")
    deed_sold = bool(tel.get(f"deed_buy_hold_sell_sold_{window_key}"))
    if not deed_buy_iso or not deed_sold:
        return False
    bought_at = parse_iso(str(deed_buy_iso))
    if not bought_at:
        return False
    return (utc_now() - bought_at).days >= min_hold_days
