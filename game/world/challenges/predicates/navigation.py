"""
Navigation / venue predicates.

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def locator_zone_bingo(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Visited at least N distinct locator zones today.
    predicateParams: {"min_zones": 3}
    """
    params = _params(template)
    n = int(params.get("min_zones") or 3)
    zones = set(handler.telemetry.get("zones_today") or [])
    return len(zones) >= n


def arrival_zone_visit(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """Visited the 'arrival' zone today."""
    return "arrival" in set(handler.telemetry.get("zones_today") or [])


def venue_tour(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Visited all required room types in a venue today.
    predicateParams:
        "venue_id": str (optional; if omitted, any venue)
        "require_zones": ["core-hub", "core-services", "core-retail", "realty"]
    """
    from world.venues import VENUES
    from world.locator_zones import locator_zone_for_room
    params = _params(template)
    require_zones = list(params.get("require_zones") or ["core-hub", "core-services", "core-retail"])
    venue_id = str(params.get("venue_id") or "")
    zones_today = set(handler.telemetry.get("zones_today") or [])
    # If specific venue required, check that at least one zone from that venue appears.
    # Zone ids in locator_zones are not venue-scoped, so we check via room visits.
    rooms_today = set(handler.telemetry.get("rooms_today") or [])
    if not rooms_today and not zones_today:
        return False
    for zone in require_zones:
        if zone not in zones_today:
            return False
    return True


def visit_three_waypoints(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Visited all of the specified room keys today.
    predicateParams: {"room_ids": [int, int, int]}
    """
    params = _params(template)
    required_ids = [int(x) for x in list(params.get("room_ids") or [])]
    if not required_ids:
        return False
    rooms_today = set(handler.telemetry.get("rooms_today") or [])
    return all(rid in rooms_today for rid in required_ids)


def lot_riddle_room(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character is currently in (or visited today) a specific room.
    predicateParams: {"room_id": int}
    """
    params = _params(template)
    room_id = int(params.get("room_id") or 0)
    if not room_id:
        return False
    rooms_today = set(handler.telemetry.get("rooms_today") or [])
    return room_id in rooms_today


def title_odyssey_venues(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Visited at least one room in every configured venue.
    predicateParams: {"min_venues": null (all)}
    """
    from world.venues import VENUES
    params = _params(template)
    target_count = int(params.get("min_venues") or len(VENUES))
    visited = set(handler.telemetry.get("venues_ever") or [])
    all_ids = set(VENUES.keys())
    return len(visited & all_ids) >= target_count


def title_odyssey_locator_zones(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Visited all known locator zone ids at least once.
    predicateParams: {"min_zones": null (all)}
    """
    all_known = {
        "arrival", "core-hub", "core-services", "core-retail", "realty",
        "field-extraction", "industrial-colony", "killstar-annex",
        "meridian-shipping", "other",
    }
    params = _params(template)
    target_count = int(params.get("min_zones") or len(all_known))
    visited = set(handler.telemetry.get("locator_zones_ever") or [])
    return len(visited & all_known) >= target_count


def monday_inventory(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character has at least N items in inventory today (Monday theme).
    predicateParams: {"min_items": 1}
    """
    params = _params(template)
    n = int(params.get("min_items") or 1)
    from world.time import utc_now
    if utc_now().weekday() != 0:
        return True  # pass on non-Monday
    return len(list(handler.obj.contents)) >= n


def thursday_social(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Completed at least one trade/give interaction today (Thursday theme).
    Uses deed_actions as proxy; more accurate if dedicated give event is wired.
    predicateParams: {}
    """
    from world.time import utc_now
    if utc_now().weekday() != 3:
        return True
    from world.time import window_key_for_cadence
    week_key = window_key_for_cadence("weekly")
    by_window = handler.telemetry.get("deed_actions_by_window") or {}
    return int(by_window.get(week_key) or 0) >= 1


def cartography(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Discovered N new rooms (first-visited) this month.
    predicateParams: {"min_rooms": 5}
    """
    params = _params(template)
    n = int(params.get("min_rooms") or 5)
    # rooms_ever grows monotonically; monthly new rooms need a monthly baseline.
    # Stored as total ever; without per-month baseline this is approximate.
    return len(handler.telemetry.get("rooms_ever") or []) >= n
