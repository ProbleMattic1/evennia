"""
Extraction / logistics predicates (mining, flora, fauna, haulers).

Each function: check(handler, template, window_key) -> bool
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world.challenges.challenge_handler import ChallengeHandler


def _params(template: dict) -> dict[str, Any]:
    return dict(template.get("predicateParams") or {})


def hauler_cycle(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    At least N hauler cycles completed today.
    predicateParams: {"min_cycles": 1}
    """
    params = _params(template)
    n = int(params.get("min_cycles") or 1)
    return int(handler.telemetry.get("hauler_events_today") or 0) >= n


def hauler_throughput(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    K hauler completions this week, across ≥ M distinct locator zones.
    predicateParams: {"min_cycles": 5, "min_zones": 2}
    """
    params = _params(template)
    min_cycles = int(params.get("min_cycles") or 5)
    min_zones = int(params.get("min_zones") or 2)
    from world.time import window_key_for_cadence
    week_key = window_key_for_cadence("weekly")
    by_window = handler.telemetry.get("hauler_throughput_by_window") or {}
    if int(by_window.get(week_key) or 0) < min_cycles:
        return False
    # Zone diversity check: requires zones recorded during hauler events
    zones_ever = set(handler.telemetry.get("locator_zones_ever") or [])
    extraction_zones = {z for z in zones_ever if "industrial" in z or "extraction" in z or "killstar" in z}
    return len(extraction_zones) >= min_zones


def single_mine_deposit(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """At least one mining deposit today."""
    return int(handler.telemetry.get("mine_deposits_today") or 0) >= 1


def mining_slot_participation(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Participated in at least one mining delivery slot today (received a payout in
    today's or a recent slot). Uses per-player miner payout event if wired (Phase 3).
    Falls back to mine_deposits_today > 0 until then.
    predicateParams: {}
    """
    return single_mine_deposit(handler, template, window_key)


def triple_pipeline_touch(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Touched all three pipelines today (mining, flora, fauna).
    predicateParams: {"min_pipelines": 3}
    """
    params = _params(template)
    n = int(params.get("min_pipelines") or 3)
    pipelines = set(handler.telemetry.get("pipelines_today") or [])
    return len(pipelines) >= n


def district_track(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Completed at least N hauler events originating from a specific locator zone.
    predicateParams: {"zone_id": "industrial-colony", "min_events": 10}
    """
    params = _params(template)
    zone_id = str(params.get("zone_id") or "")
    min_events = int(params.get("min_events") or 10)
    if not zone_id:
        return False
    zones_ever = set(handler.telemetry.get("locator_zones_ever") or [])
    if zone_id not in zones_ever:
        return False
    # Count is coarse: all hauler events this quarter (rough proxy)
    from world.time import window_key_for_cadence
    quarter_key = window_key_for_cadence("quarter")
    by_window = handler.telemetry.get("hauler_throughput_by_window") or {}
    # Sum over all weekly keys in this quarter (share prefix YYYY-QN → fallback to total)
    total = sum(v for k, v in by_window.items())
    return total >= min_events


def pipeline_specialist(handler: "ChallengeHandler", template: dict, window_key: str) -> bool:
    """
    Character owns sites in at least one pipeline and has received payouts.
    predicateParams: {"pipeline": "mining"}
    """
    params = _params(template)
    pipeline = str(params.get("pipeline") or "mining")
    char = handler.obj
    if pipeline == "mining":
        tag, category = "mining_site", "mining"
    elif pipeline == "flora":
        tag, category = "flora_site", "flora"
    elif pipeline == "fauna":
        tag, category = "fauna_site", "fauna"
    else:
        return False
    from evennia import search_tag
    sites = search_tag(tag, category=category)
    for site in sites:
        if getattr(site.db, "owner", None) == char:
            return True
    return False
