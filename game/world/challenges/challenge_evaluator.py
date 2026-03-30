"""
Challenge evaluator — coordinates telemetry events with predicate checks.

Two entry points:
  on_event(handler, event_name, payload) -> bool  (returns True if anything changed)
  evaluate_window(handler, cadence) -> list[str]  (returns newly-completed challenge ids)

Predicate dispatch is by template.predicateKey. Each predicate module exposes:
  check(handler, template, window_key) -> bool
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from evennia.utils import logger

from world.challenges.challenge_loader import challenges_for_cadence, get_challenge_template
from world.time import VALID_CADENCES, window_key_for_cadence

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler

# Map event names to telemetry updater methods on the handler.
# The handler method is called with the full payload; methods ignore what they don't need.
_EVENT_DISPATCH: dict[str, str] = {
    "room_enter": "_handle_room_enter",
    "vendor_sale": "_handle_vendor_sale",
    "treasury_credit": "_handle_treasury_credit",
    "property_operation_started": "_handle_property_op",
    "hauler_tick": "_handle_hauler_tick",
    "mine_deposit": "_handle_mine_deposit",
    "flora_deposit": "_handle_flora_deposit",
    "fauna_deposit": "_handle_fauna_deposit",
    "deed_purchased": "_handle_deed_purchased",
    "deed_listed": "_handle_deed_action",
    "deed_sold": "_handle_deed_sold",
    "miner_payout": "_handle_miner_payout",
    "parcel_visited": "_handle_property_op",
    "balance_snapshot": "_handle_balance_snapshot",
}


def on_event(handler: "ChallengeHandler", event_name: str, payload: dict[str, Any]) -> bool:
    """Update telemetry from an event. Returns True if any state changed."""
    fn_name = _EVENT_DISPATCH.get(event_name)
    if fn_name is None:
        return False
    fn = globals().get(fn_name)
    if fn is None:
        logger.log_warn(f"[challenges] no handler for event {event_name!r} (fn {fn_name})")
        return False
    try:
        fn(handler, payload)
        return True
    except Exception:
        logger.log_trace(f"[challenges] on_event {event_name!r} error")
        return False


def evaluate_window(handler: "ChallengeHandler", cadence: str) -> list[str]:
    """
    For every enabled challenge of this cadence, check if completed; mark it if so.
    Returns list of newly-completed challenge ids.
    """
    if cadence not in VALID_CADENCES:
        return []

    window_key = window_key_for_cadence(cadence)
    templates = challenges_for_cadence(cadence)
    newly_completed: list[str] = []

    for tmpl in templates:
        if not tmpl.get("enabled", True):
            continue
        cid = tmpl["id"]
        if handler.already_completed(cid, window_key):
            continue
        # Ensure active entry exists
        handler.get_or_create_active(cid, cadence, window_key)
        # Run predicate
        try:
            result = _run_predicate(handler, tmpl, window_key)
        except Exception:
            logger.log_trace(f"[challenges] predicate error for {cid}")
            result = False
        if result:
            if handler.mark_complete(cid, window_key):
                newly_completed.append(cid)
                logger.log_info(f"[challenges] {handler.obj.key} completed {cid} ({cadence}:{window_key})")

    return newly_completed


def _run_predicate(
    handler: "ChallengeHandler", tmpl: dict, window_key: str
) -> bool:
    predicate_key = tmpl.get("predicateKey") or ""
    if not predicate_key:
        return False

    # Split predicate_key into module.function (e.g. "economy.balance_net_positive")
    parts = predicate_key.split(".", 1)
    if len(parts) != 2:
        logger.log_warn(f"[challenges] bad predicateKey {predicate_key!r} — use 'domain.fn_name'")
        return False
    domain, fn_name = parts

    try:
        mod = importlib.import_module(f"world.challenges.predicates.{domain}")
    except ImportError:
        logger.log_warn(f"[challenges] predicate domain {domain!r} not found")
        return False

    fn = getattr(mod, fn_name, None)
    if fn is None:
        logger.log_warn(f"[challenges] predicate {fn_name!r} not in {domain}")
        return False

    return bool(fn(handler, tmpl, window_key))


# ---------------------------------------------------------------------------
# Telemetry event handlers (private, called by on_event)
# ---------------------------------------------------------------------------

def _handle_room_enter(handler: "ChallengeHandler", payload: dict) -> None:
    room_id = payload.get("room_id")
    zone_id = payload.get("zone_id")
    venue_id = payload.get("venue_id")
    if room_id:
        handler.record_room_visit(int(room_id), venue_id=venue_id)
    if zone_id:
        handler.record_zone_visit(str(zone_id))


def _handle_vendor_sale(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_vendor_sale(
        vendor_id=str(payload.get("vendor_id") or ""),
        price=int(payload.get("price") or 0),
        tax_amount=int(payload.get("tax_amount") or 0),
    )
    handler.add_lifetime_credits(int(payload.get("price") or 0))


def _handle_treasury_credit(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_treasury_touch()


def _handle_property_op(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_property_op()


def _handle_hauler_tick(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_hauler_event(mine_zone=payload.get("mine_zone"))


def _handle_mine_deposit(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_mine_deposit("mining")


def _handle_flora_deposit(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_mine_deposit("flora")


def _handle_fauna_deposit(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_mine_deposit("fauna")


def _handle_deed_action(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_deed_action()


def _handle_deed_purchased(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_deed_action()
    from world.time import to_iso, utc_now, window_key_for_cadence
    quarter_key = window_key_for_cadence("quarter")
    field = f"deed_buy_hold_sell_bought_{quarter_key}"
    if not handler.telemetry.get(field):
        handler.telemetry[field] = to_iso(utc_now())


def _handle_deed_sold(handler: "ChallengeHandler", payload: dict) -> None:
    handler.record_deed_action()
    from world.time import window_key_for_cadence
    quarter_key = window_key_for_cadence("quarter")
    handler.telemetry[f"deed_buy_hold_sell_sold_{quarter_key}"] = True


def _handle_miner_payout(handler: "ChallengeHandler", payload: dict) -> None:
    amount = int(payload.get("amount") or 0)
    handler.add_lifetime_credits(amount)


def _handle_balance_snapshot(handler: "ChallengeHandler", payload: dict) -> None:
    balance = int(payload.get("balance") or 0)
    handler.take_balance_snapshot(balance)
