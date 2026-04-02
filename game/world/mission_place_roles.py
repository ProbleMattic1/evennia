"""
Canonical room keys for mission/quest visit targets, grouped by abstract role id.

JSON may use ``roomTagsAny`` on visit_room objectives and room triggers; loaders
expand roles into ``roomKeysAny``. Tags on rooms support discovery and future scripts.
"""

from __future__ import annotations

MISSION_PLACE_CATEGORY = "mission_place"

ROOM_ROLE_KEYS: dict[str, tuple[str, ...]] = {
    "dock_public": (
        "Meridian Civil Shipyard",
        "Frontier Meridian Civil Shipyard",
    ),
    "dock_dispatch": (
        "NanoMegaPlex Industrial Subdeck",
        "Frontier Industrial Subdeck",
    ),
    "station_liaison_contact": (
        "NanoMegaPlex Promenade",
        "Frontier Promenade",
    ),
}


def known_place_role_ids() -> frozenset[str]:
    return frozenset(ROOM_ROLE_KEYS.keys())


def expand_place_roles(role_ids: list[str]) -> list[str]:
    out: list[str] = []
    for rid in role_ids:
        r = str(rid or "").strip()
        if not r:
            continue
        keys = ROOM_ROLE_KEYS.get(r)
        if keys is None:
            raise ValueError(f"unknown mission place role {r!r}")
        out.extend(keys)
    return out


def merge_visit_room_keys(*, explicit_keys: list[str], role_ids: list[str]) -> list[str]:
    merged = [str(k).strip() for k in explicit_keys if str(k).strip()]
    merged.extend(expand_place_roles(role_ids))
    seen: set[str] = set()
    deduped: list[str] = []
    for k in merged:
        if k not in seen:
            seen.add(k)
            deduped.append(k)
    return deduped


def dock_public_room_keys() -> frozenset[str]:
    return frozenset(ROOM_ROLE_KEYS["dock_public"])


def tag_rooms_for_roles_from_registry() -> None:
    """Idempotent: tag rooms listed in ROOM_ROLE_KEYS."""
    from evennia import search_object

    for role_id, keys in ROOM_ROLE_KEYS.items():
        for key in keys:
            found = search_object(key)
            if not found:
                continue
            found[0].tags.add(role_id, category=MISSION_PLACE_CATEGORY)
