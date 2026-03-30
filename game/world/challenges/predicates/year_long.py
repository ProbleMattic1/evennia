"""
Year-long / almanac predicates.

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def almanac_twelve(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Completed at least N monthly challenges this calendar year.
    Derived from history entries with cadence == 'monthly' and windowKey starting with this year.
    predicateParams: {"min_monthly_completions": 12}
    """
    params = _params(template)
    n = int(params.get("min_monthly_completions") or 12)
    year_prefix = window_key[:4]  # e.g. "2026"
    history = handler._state.get("history") or []
    monthly_done = {
        row["windowKey"]
        for row in history
        if row.get("cadence") == "monthly"
        and str(row.get("windowKey") or "").startswith(year_prefix)
    }
    return len(monthly_done) >= n


def ledger_lifetime_milestone(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Lifetime credits moved through this character ≥ threshold.
    predicateParams: {"threshold": 1000000}
    """
    params = _params(template)
    threshold = int(params.get("threshold") or 1_000_000)
    return int(handler.telemetry.get("lifetime_credits_moved") or 0) >= threshold


def oath_constraint(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character opted into a voluntary constraint oath and has not violated it.
    Oath flag stored as db attribute "year_oath_<oath_id>".
    predicateParams: {"oath_id": "pacifist"}
    """
    params = _params(template)
    oath_id = str(params.get("oath_id") or "")
    if not oath_id:
        return False
    # Oath active flag — set by staff/command
    active = getattr(handler.obj.db, f"year_oath_{oath_id}", None)
    if not active:
        return False
    # Violated flag — set by game systems if oath was broken
    violated = getattr(handler.obj.db, f"year_oath_{oath_id}_violated", False)
    return not violated
