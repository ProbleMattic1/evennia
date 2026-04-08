"""
Mining district keys — group sites for district scan and camp/base eligibility.

Keys are stable across restarts: derived from venue pool + site database id.
"""

from __future__ import annotations

from evennia import search_tag

# Pools large enough for variety; assignment is deterministic per site id.
_DISTRICT_POOLS: dict[str, list[str]] = {
    "nanomega_core": [f"nm-{i:02d}" for i in range(1, 51)],
    "frontier_outpost": [f"fr-{i:02d}" for i in range(1, 51)],
}

_DEFAULT_VENUE = "nanomega_core"


def assign_district_key(venue_id: str, site_id: int) -> str:
    """Return persistent district key for a new or migrated mining site."""
    vid = (venue_id or _DEFAULT_VENUE).strip() or _DEFAULT_VENUE
    pool = _DISTRICT_POOLS.get(vid) or _DISTRICT_POOLS[_DEFAULT_VENUE]
    if not pool:
        return f"{vid}-d00"
    idx = int(site_id) % len(pool)
    return pool[idx]


def backfill_mining_district_keys() -> int:
    """
    Set db.mining_district_key on mining sites that lack it. Idempotent.
    Returns count of sites updated.
    """
    from world.venue_resolve import venue_id_for_object

    sites = search_tag("mining_site", category="mining")
    n = 0
    for site in sites:
        if getattr(site.db, "mining_district_key", None):
            continue
        vid = venue_id_for_object(site) or _DEFAULT_VENUE
        site.db.mining_district_key = assign_district_key(vid, site.id)
        n += 1
    return n
