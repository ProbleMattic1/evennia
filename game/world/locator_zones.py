"""
Locator district ids for the Universal Locator (web UI).

Single source of truth: world.venues.VENUES. Non-venue pockets (Ashfall, Killstar)
use key patterns only where bootstrap does not set venue_id.
"""

from __future__ import annotations

from world.venues import VENUES


def all_venue_hub_keys() -> frozenset[str]:
    return frozenset(str(v["hub_key"]) for v in VENUES.values() if v.get("hub_key"))


def locator_zone_for_room(room, *, has_mining_site: bool) -> str:
    """
    Return a zone id string matching frontend LocatorZoneId.

    Precedence: venue-scoped keys → non-venue patterns → mining claims → other.
    """
    k = getattr(room, "key", None) or ""
    vid = getattr(getattr(room, "db", None), "venue_id", None)

    if vid and vid in VENUES:
        z = _zone_from_venue_room(vid, k)
        if z:
            return z

    if k == "Frontier Transit Shell":
        return "arrival"
    if k == "Ashfall Industrial Grid" or k.startswith("Ashfall Industrial Pad "):
        return "ashfall-industrial"
    if k == "Marcus Killstar Mining Annex" or k.startswith("Marcus Killstar Pad "):
        return "killstar-annex"

    if has_mining_site:
        return "field-extraction"
    return "other"


def _zone_from_venue_room(vid: str, k: str) -> str | None:
    v = VENUES[vid]
    arr = v.get("arrival_room_key")
    if arr and k == arr:
        return "arrival"
    if k == v["hub_key"]:
        return "core-hub"
    if k == v["bank"]["reserve_room_key"]:
        return "core-services"
    if k == v["processing"]["plant_room_key"]:
        return "core-services"
    for shop in v["shops"]:
        if shop["room_key"] == k:
            return "core-retail"
    r = v["realty"]
    if k == r["office_key"] or k == r["archive_room_key"]:
        return "realty-property"
    sy = v["shipyard"]
    if k == sy["showroom_key"] or k == sy["delivery_key"]:
        return "meridian-shipping"
    if k == v["advertising"]["room_key"]:
        return "nanomega-agency"
    ind = v["industrial"]
    if k == ind["staging_room_key"]:
        return "plex-industrial"
    prefix = str(ind["pad_room_prefix"])
    if k == prefix or k.startswith(prefix + " "):
        return "plex-industrial"
    return None
