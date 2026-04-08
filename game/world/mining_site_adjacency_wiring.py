"""
Corridor exits between mining deposit rooms (same venue).

Each new mine room is linked with one bidirectional strip pair to a single
peer mining room, so district scan (1-hop exit graph in
``world.mining_adjacent_scan``) can reach another deposit.

No backfill — wiring runs only from ``generate_mining_site``.

Peer choice prefers rooms with fewer existing ``strip-*`` exits to limit fan-in
as the site count grows.
"""

from __future__ import annotations

import random
from typing import Any

from evennia import search_tag

from world.bootstrap_mining import _get_or_create_exit
from world.mining_adjacent_scan import neighbor_rooms
from world.venue_resolve import venue_id_for_object

_STRIP_KEY_PREFIX = "strip-"


def _mining_rooms_in_venue(venue_id: str) -> list[Any]:
    seen: dict[int, Any] = {}
    for s in search_tag("mining_site", category="mining"):
        loc = getattr(s, "location", None)
        if not loc:
            continue
        if (venue_id_for_object(loc) or "nanomega_core") != venue_id:
            continue
        seen[int(loc.id)] = loc
    return list(seen.values())


def _strip_exit_degree(room) -> int:
    """Count outbound strip exits from this room."""
    if not room:
        return 0
    n = 0
    for o in room.contents:
        if not getattr(o, "destination", None):
            continue
        key = str(getattr(o, "key", "") or "")
        if key.startswith(_STRIP_KEY_PREFIX):
            n += 1
    return n


def _rooms_already_adjacent(a, b) -> bool:
    if not a or not b or int(a.id) == int(b.id):
        return True
    b_id = int(b.id)
    for nr in neighbor_rooms(a):
        if int(nr.id) == b_id:
            return True
    return False


def _strip_exit_key(from_room, to_room) -> str:
    return f"{_STRIP_KEY_PREFIX}{int(from_room.id)}-{int(to_room.id)}"


def _invalidate_world_graph() -> None:
    try:
        from web.ui.world_graph import invalidate_world_graph_cache

        invalidate_world_graph_cache()
    except Exception:
        pass


def wire_bidirectional_mining_strip(from_room, to_room) -> None:
    """Two Exit objects (both directions). No-op if already linked."""
    if not from_room or not to_room:
        return
    if int(from_room.id) == int(to_room.id):
        return
    if _rooms_already_adjacent(from_room, to_room):
        return

    k_ab = _strip_exit_key(from_room, to_room)
    k_ba = _strip_exit_key(to_room, from_room)
    alias_b = [f"to-{int(to_room.id)}"]
    alias_a = [f"to-{int(from_room.id)}"]

    _get_or_create_exit(k_ab, alias_b, from_room, to_room)
    _get_or_create_exit(k_ba, alias_a, to_room, from_room)
    _invalidate_world_graph()


def _candidate_peer_rooms(venue_id: str, new_room) -> list[Any]:
    from typeclasses.claim_utils import get_unclaimed_sites

    by_id: dict[int, Any] = {}
    new_id = int(new_room.id)

    for s in get_unclaimed_sites():
        if not s.tags.has("mining_site", category="mining"):
            continue
        loc = getattr(s, "location", None)
        if not loc or int(loc.id) == new_id:
            continue
        if (venue_id_for_object(loc) or "nanomega_core") != venue_id:
            continue
        by_id[int(loc.id)] = loc

    if not by_id:
        for loc in _mining_rooms_in_venue(venue_id):
            if int(loc.id) == new_id:
                continue
            by_id[int(loc.id)] = loc

    return list(by_id.values())


def pick_peer_room_for_new_mining_room(venue_id: str, new_room) -> Any | None:
    """Prefer lowest strip exit degree; tie-break random."""
    candidates = _candidate_peer_rooms(venue_id, new_room)
    if not candidates:
        return None
    degrees = [(r, _strip_exit_degree(r)) for r in candidates]
    min_d = min(d for _r, d in degrees)
    pool = [r for r, d in degrees if d == min_d]
    return random.choice(pool)


def wire_new_mining_room_to_strip(new_room, venue_id: str) -> None:
    """
    After hub exits exist, before creating the new MiningSite in ``new_room``.
    """
    peer = pick_peer_room_for_new_mining_room(venue_id, new_room)
    if not peer:
        return
    wire_bidirectional_mining_strip(new_room, peer)
