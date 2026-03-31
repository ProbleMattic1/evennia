"""
Challenge signal bus.

Call emit() from any hook site to feed the cadence-challenge system:

    from world.challenges.challenge_signals import emit
    emit(character, "vendor_sale", {"vendor_id": "tech-depot", "price": 250, "tax_amount": 0})

The function is deliberately cheap to call even when challenges are not loaded:
it catches all errors to never break the host system.
"""

from __future__ import annotations

from typing import Any

from evennia.utils import logger


def emit(character, event_name: str, payload: dict[str, Any] | None = None) -> None:
    """
    Emit a game event to the character's challenge handler.

    Always safe to call — swallows all errors, logs traces only.
    """
    if character is None:
        return
    try:
        handler = character.challenges  # lazy_property
        handler.on_event(event_name, payload or {})
        # Opportunistically evaluate affected cadences after high-frequency events
        if event_name in _DAILY_TRIGGERS:
            handler.evaluate_window("daily")
        elif event_name in _WEEKLY_TRIGGERS:
            handler.evaluate_window("weekly")
        # Save is handled inside on_event / evaluate_window paths
    except Exception:
        logger.log_trace(f"[challenges] emit error event={event_name!r} char={getattr(character, 'key', '?')}")


_DAILY_TRIGGERS = frozenset({
    "vendor_sale",
    "treasury_credit",
    "property_operation_started",
    "parcel_visited",
    "room_enter",
    "mine_deposit",
    "flora_deposit",
    "fauna_deposit",
    "hauler_tick",
    "miner_payout",
    "balance_snapshot",
    "space_engagement",
})

_WEEKLY_TRIGGERS = frozenset({
    "deed_purchased",
    "deed_listed",
    "deed_sold",
    "hauler_tick",
})
