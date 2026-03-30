"""
Property / realty predicates.

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def _holdings_for_character(character):
    from evennia import search_tag
    from typeclasses.property_holdings import PROPERTY_HOLDING_CATEGORY, PROPERTY_HOLDING_TAG
    candidates = search_tag(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY)
    return [h for h in candidates if getattr(h.db, "title_owner", None) == character]


def _deeds_carried(character):
    from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
    return [
        obj for obj in character.contents
        if obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
    ]


def property_operation_touch(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """At least one property operation started or touched today."""
    return int(handler.telemetry.get("property_ops_today") or 0) >= 1


def visit_parcel_shell(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character is currently inside a property shell they own (or any shell if
    predicateParams.require_owner is false).
    predicateParams: {"require_owner": true}
    """
    params = _params(template)
    require_owner = bool(params.get("require_owner", True))
    character = handler.obj
    loc = character.location
    if not loc:
        return False
    # Check if location is a place_state root room of one of character's holdings
    holdings = _holdings_for_character(character) if require_owner else []
    if require_owner:
        for h in holdings:
            place = h.db.place_state or {}
            root_id = place.get("root_room_id")
            if root_id and int(root_id) == loc.id:
                return True
        return False
    else:
        # Any property shell: tag-based detection
        return loc.tags.has("property_shell", category="realty")


def deed_on_person(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """Character currently carries at least one property claim deed."""
    return len(_deeds_carried(handler.obj)) >= 1


def deed_market_action(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least N deed market actions (buy/list/sell) this week.
    predicateParams: {"min_actions": 1}
    """
    params = _params(template)
    n = int(params.get("min_actions") or 1)
    from world.time import window_key_for_cadence
    week_key = window_key_for_cadence("weekly")
    by_window = handler.telemetry.get("deed_actions_by_window") or {}
    return int(by_window.get(week_key) or 0) >= n


def primary_deed_purchase(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Purchased a deed from the primary market this week (checked via economy tx type).
    """
    from typeclasses.economy import get_economy
    from world.time import window_key_for_cadence
    econ = get_economy(create_missing=False)
    if econ is None:
        return False
    week_key = window_key_for_cadence("weekly")
    player_account = econ.get_character_account(handler.obj)
    for tx in econ.db.transactions or []:
        if (
            tx.get("from_account") == player_account
            and tx.get("type") in ("primary_property_sale", "primary_deed_sale")
            and (tx.get("timestamp") or "").startswith(week_key[:7])
        ):
            return True
    return False


def portfolio_two_zones(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character owns holdings in ≥ 2 distinct zones (residential/commercial/industrial).
    predicateParams: {"min_zones": 2}
    """
    params = _params(template)
    n = int(params.get("min_zones") or 2)
    holdings = _holdings_for_character(handler.obj)
    zones = {str(h.db.zone or "").lower() for h in holdings if h.db.zone}
    return len(zones) >= n


def two_operation_kinds(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character has holdings with ≥ 2 distinct operation kinds running.
    predicateParams: {"min_kinds": 2}
    """
    params = _params(template)
    n = int(params.get("min_kinds") or 2)
    holdings = _holdings_for_character(handler.obj)
    kinds = {
        (h.db.operation or {}).get("kind")
        for h in holdings
        if (h.db.operation or {}).get("kind") and not (h.db.operation or {}).get("paused")
    }
    return len(kinds) >= n


def development_not_idle(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """At least one holding has development_state != 'idle'."""
    holdings = _holdings_for_character(handler.obj)
    return any(
        str(h.db.development_state or "idle").lower() != "idle"
        for h in holdings
    )


def operation_level(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least one holding has operation.level >= L.
    predicateParams: {"min_level": 1}
    """
    params = _params(template)
    min_level = int(params.get("min_level") or 1)
    holdings = _holdings_for_character(handler.obj)
    return any(
        int((h.db.operation or {}).get("level") or 0) >= min_level
        for h in holdings
    )


def access_control_change(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least one holding has at least one manager or tenant assigned.
    (Proxy: non-empty access list means a change was made at some point.)
    predicateParams: {}
    """
    holdings = _holdings_for_character(handler.obj)
    for h in holdings:
        acc = h.db.access or {}
        if acc.get("managers") or acc.get("tenants"):
            return True
    return False


def claim_to_skyline(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least one holding has operation running AND at least one structure installed.
    predicateParams: {"min_structures": 1}
    """
    params = _params(template)
    min_str = int(params.get("min_structures") or 1)
    holdings = _holdings_for_character(handler.obj)
    for h in holdings:
        op = h.db.operation or {}
        if not op.get("kind") or op.get("paused"):
            continue
        if len(h.structures()) >= min_str:
            return True
    return False


def multi_holding_managers(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character is a manager on ≥ N distinct holdings (including their own or others').
    predicateParams: {"min_holdings": 2}
    """
    from evennia import search_tag
    from typeclasses.property_holdings import PROPERTY_HOLDING_CATEGORY, PROPERTY_HOLDING_TAG
    params = _params(template)
    n = int(params.get("min_holdings") or 2)
    char_id = handler.obj.id
    all_holdings = search_tag(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY)
    count = 0
    for h in all_holdings:
        acc = h.db.access or {}
        managers = acc.get("managers") or []
        # managers stored as dbids or character refs
        for m in managers:
            mid = m.id if hasattr(m, "id") else (int(m) if m else None)
            if mid == char_id:
                count += 1
                break
    return count >= n


def property_operation_streak(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least one holding has had a non-paused operation running all week AND accrued
    at least min_accrued credits this week.
    predicateParams: {"min_accrued": 0}
    """
    params = _params(template)
    min_accrued = int(params.get("min_accrued") or 0)
    holdings = _holdings_for_character(handler.obj)
    for h in holdings:
        op = h.db.operation or {}
        if op.get("paused") or not op.get("kind"):
            continue
        ledger = h.db.ledger or {}
        accrued = int(ledger.get("credits_accrued") or 0)
        if accrued >= min_accrued:
            return True
    return False


def anniversary_deed(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character has held a deed continuously for ≥ 365 days.
    Evaluated against claim.db.created_at or holding bind time if stored.
    predicateParams: {"min_days": 365}
    """
    from world.time import parse_iso, utc_now
    params = _params(template)
    min_days = int(params.get("min_days") or 365)
    from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
    deeds = _deeds_carried(handler.obj)
    now = utc_now()
    for deed in deeds:
        created_raw = getattr(deed.db, "created_at", None) or getattr(deed.db, "date_created", None)
        if not created_raw:
            # Fallback: check db_date_created attribute on the database object
            created_raw = getattr(deed, "db_date_created", None)
        if not created_raw:
            continue
        created = parse_iso(str(created_raw)) if isinstance(created_raw, str) else created_raw
        if created and (now - created).days >= min_days:
            return True
    return False
