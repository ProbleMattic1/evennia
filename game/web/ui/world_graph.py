"""
Read-only world topology for the Universal Locator Map (rooms + exits).

Uses ObjectDB so procedural rooms (mining discovery, etc.) appear without a
static map. Cached briefly; invalidated when new mining sites are generated.
"""

from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from evennia.objects.models import ObjectDB

from typeclasses.characters import CHARACTER_TYPECLASS_PATH
from world.bootstrap_hub import HUB_ROOM_KEY

from .room_nav_utils import should_show_mining_exit_dict

CACHE_KEY = "ui:world_graph:v1"
CACHE_TTL = 45

ROOM_TYPECLASS_SUBSTRING = "typeclasses.rooms.Room"
EXIT_TYPECLASS_SUBSTRING = "typeclasses.exits.Exit"


def _typeclass_path(obj) -> str:
    return (getattr(obj, "db_typeclass_path", None) or "") or ""


def _is_room_obj(obj) -> bool:
    return ROOM_TYPECLASS_SUBSTRING in _typeclass_path(obj)


def _is_exit_obj(obj) -> bool:
    return EXIT_TYPECLASS_SUBSTRING in _typeclass_path(obj)


def _room_has_mining_site(room) -> bool:
    for o in room.contents:
        if o.tags.has("mining_site", category="mining"):
            return True
    return False


def _edge_visible_for_char(e: dict, char) -> bool:
    if e["fromKey"] != HUB_ROOM_KEY:
        return True
    return should_show_mining_exit_dict({"destination": e["toKey"]}, char)


def _build_skeleton() -> dict:
    rooms_out: list[dict] = []
    edges_out: list[dict] = []
    seen_room_ids: set[int] = set()

    exit_qs = ObjectDB.objects.filter(
        db_destination__isnull=False,
        db_location__isnull=False,
    ).select_related("db_location", "db_destination")

    for ex in exit_qs:
        loc = ex.location
        dest = ex.destination
        if not loc or not dest:
            continue
        if not _is_room_obj(loc) or not _is_room_obj(dest):
            continue
        if not _is_exit_obj(ex):
            continue

        for r in (loc, dest):
            rid = r.id
            if rid not in seen_room_ids:
                seen_room_ids.add(rid)
                rooms_out.append(
                    {
                        "id": rid,
                        "key": r.key,
                        "hasMiningSite": _room_has_mining_site(r),
                    }
                )

        edges_out.append(
            {
                "fromId": loc.id,
                "toId": dest.id,
                "fromKey": loc.key,
                "toKey": dest.key,
                "exitKey": ex.key,
            }
        )

    return {"rooms": rooms_out, "edgesAll": edges_out}


def _get_skeleton() -> dict:
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    data = _build_skeleton()
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def invalidate_world_graph_cache() -> None:
    cache.delete(CACHE_KEY)


def _pc_room_counts_qs(*, online_only: bool = False):
    """
    Player-capable characters in a room, excluding NPCs (db.is_npc).
    online_only: restrict to characters with an active session (db_sessid set).
    """
    npc_ids = ObjectDB.objects.get_objs_with_attr_value(
        "is_npc",
        True,
        typeclasses=[CHARACTER_TYPECLASS_PATH],
    ).values_list("id", flat=True)

    qs = ObjectDB.objects.filter(
        db_typeclass_path=CHARACTER_TYPECLASS_PATH,
        db_location_id__isnull=False,
    ).exclude(id__in=npc_ids)

    if online_only:
        qs = qs.filter(db_sessid__isnull=False).exclude(db_sessid="")

    return qs.values("db_location_id").annotate(c=Count("id"))


def _player_count_by_room_id(*, online_only: bool = False) -> dict[int, int]:
    return {row["db_location_id"]: row["c"] for row in _pc_room_counts_qs(online_only=online_only)}


def _bfs_reachable(from_id: int, edges: list[dict]) -> set[int]:
    by_from: dict[int, list[int]] = defaultdict(list)
    for e in edges:
        by_from[e["fromId"]].append(e["toId"])

    seen: set[int] = {from_id}
    stack = [from_id]
    while stack:
        nid = stack.pop()
        for tid in by_from.get(nid, ()):
            if tid not in seen:
                seen.add(tid)
                stack.append(tid)
    return seen


def build_world_graph_payload(*, char) -> dict:
    skel = _get_skeleton()
    rooms = list(skel["rooms"])
    edges_all = list(skel["edgesAll"])

    counts = _player_count_by_room_id(online_only=False)
    for r in rooms:
        r["playerCount"] = int(counts.get(r["id"], 0))

    edges = [e for e in edges_all if _edge_visible_for_char(e, char)]

    current_room_key = None
    current_room_id = None
    reachable_ids: list[int] | None = None
    adjacent_room_keys: list[str] | None = None

    if char is not None and getattr(char, "location", None):
        loc = char.location
        if _is_room_obj(loc):
            current_room_key = loc.key
            current_room_id = loc.id
            reachable = _bfs_reachable(loc.id, edges)
            reachable_ids = sorted(reachable)
            adjacent_room_keys = sorted(
                {e["toKey"] for e in edges if e["fromId"] == current_room_id}
            )

    return {
        "schemaVersion": 2,
        "generatedAt": timezone.now().isoformat(),
        "rooms": rooms,
        "edges": edges,
        "edgesAll": edges_all,
        "currentRoomKey": current_room_key,
        "reachableRoomIds": reachable_ids,
        "adjacentRoomKeys": adjacent_room_keys,
    }


@require_GET
def world_graph_state(request):
    """
    Universal Locator Map: room/exit graph from DB + optional player overlay.

    Anonymous: topology with hub mining exits hidden (same as nav_state).
    Authenticated: current room, BFS reachable ids, one-hop adjacent keys for travel.
    """
    char = None
    if request.user.is_authenticated:
        from .views import _resolve_character_for_web

        char, _ = _resolve_character_for_web(request.user)

    payload = build_world_graph_payload(char=char)
    return JsonResponse(payload)
