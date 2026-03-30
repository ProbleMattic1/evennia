"""
Economy / credits predicates.

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def balance_net_positive(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character balance is strictly greater than the snapshot taken at the start of today.
    predicateParams: {} (no extra params required)
    """
    tel = handler.telemetry
    snapshot = int(tel.get("balance_snapshot") or 0)
    from typeclasses.economy import get_economy
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    current = econ.get_character_balance(handler.obj)
    return current > snapshot


def balance_after_fee(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character paid at least one fee today AND still ends above yesterday's snapshot.
    Uses treasury_touches > 0 as proxy for fee paid.
    predicateParams: {} 
    """
    tel = handler.telemetry
    if int(tel.get("treasury_touches_today") or 0) < 1:
        return False
    return balance_net_positive(handler, template, window_key)


def treasury_touch(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least one transaction touched the treasury (tax or fee) today.
    predicateParams: {"min_touches": 1}
    """
    params = _params(template)
    min_touches = int(params.get("min_touches") or 1)
    tel = handler.telemetry
    return int(tel.get("treasury_touches_today") or 0) >= min_touches


def vendor_purchase(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least N vendor purchases today.
    predicateParams: {"min_purchases": 1}
    """
    params = _params(template)
    n = int(params.get("min_purchases") or 1)
    return int(handler.telemetry.get("vendor_sales_today") or 0) >= n


def vendor_spend_cap(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Spent ≤ K credits at vendors today (still made at least 1 purchase).
    predicateParams: {"max_credits": 1000}
    """
    params = _params(template)
    max_cr = int(params.get("max_credits") or 1000)
    tel = handler.telemetry
    if int(tel.get("vendor_sales_today") or 0) < 1:
        return False
    from typeclasses.economy import get_economy
    from world.time import window_key_for_cadence
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    today = window_key_for_cadence("daily")
    txs = econ.db.transactions or []
    player_account = econ.get_character_account(handler.obj)
    spent = sum(
        int(tx.get("amount") or 0)
        for tx in txs
        if (
            tx.get("from_account") == player_account
            and tx.get("type") == "vendor_sale"
            and (tx.get("timestamp") or "")[:10] == today
        )
    )
    return 0 < spent <= max_cr


def arbitrage_note(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Net positive today AND purchased from ≥2 distinct vendor_ids.
    predicateParams: {"min_vendors": 2}
    """
    params = _params(template)
    min_vendors = int(params.get("min_vendors") or 2)
    tel = handler.telemetry
    distinct = len(set(tel.get("vendor_ids_today") or []))
    return distinct >= min_vendors and balance_net_positive(handler, template, window_key)


def friday_risk(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Made a single vendor purchase of ≥ K credits today.
    predicateParams: {"min_single_purchase": 500}
    """
    params = _params(template)
    min_cr = int(params.get("min_single_purchase") or 500)
    from typeclasses.economy import get_economy
    from world.time import window_key_for_cadence
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    today = window_key_for_cadence("daily")
    player_account = econ.get_character_account(handler.obj)
    txs = econ.db.transactions or []
    for tx in txs:
        if (
            tx.get("from_account") == player_account
            and tx.get("type") == "vendor_sale"
            and (tx.get("timestamp") or "")[:10] == today
            and int(tx.get("amount") or 0) >= min_cr
        ):
            return True
    return False


def tax_contribution(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Cumulative tax paid this week/month ≥ threshold_credits.
    predicateParams: {"min_tax": 100}
    """
    params = _params(template)
    min_tax = int(params.get("min_tax") or 100)
    from typeclasses.economy import get_economy
    from world.time import window_key_for_cadence
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    player_account = econ.get_character_account(handler.obj)
    txs = econ.db.transactions or []
    # window key is e.g. "2026-W13" or "2026-03" — match by prefix of timestamp
    total_tax = 0
    for tx in txs:
        if tx.get("from_account") != player_account:
            continue
        ts = tx.get("timestamp") or ""
        extra = tx.get("extra") or {}
        tax_amt = int(extra.get("tax_amount") or 0)
        if tax_amt > 0 and ts.startswith(window_key[:7]):
            total_tax += tax_amt
    return total_tax >= min_tax


def ledger_lifetime_milestone(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Lifetime credits moved through this character ≥ threshold.
    predicateParams: {"threshold": 1000000}
    """
    params = _params(template)
    threshold = int(params.get("threshold") or 1_000_000)
    return int(handler.telemetry.get("lifetime_credits_moved") or 0) >= threshold
