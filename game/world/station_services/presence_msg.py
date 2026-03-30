from __future__ import annotations

import time
from typing import Any

DESK_AMBIENCE_MIN_INTERVAL_SEC = 120.0


def station_room_echo(
    room,
    npc,
    player,
    template: str,
    *,
    extra_mapping: dict[str, Any] | None = None,
) -> None:
    """
    Others in the room see `template`; caller is excluded (they already got private text).
    Evennia replaces {player}, {npc}, etc. when those keys are in mapping (object-aware).
    """
    if not room or not npc or not player:
        return
    mapping = {"player": player, "npc": npc}
    if extra_mapping:
        mapping.update(extra_mapping)
    room.msg_contents(template, exclude=player, from_obj=npc, mapping=mapping)


def npc_in_room_by_key(room, npc_key: str):
    if not room:
        return None
    for obj in room.contents:
        if getattr(obj, "key", None) == npc_key:
            return obj
    return None


def room_announce_or_system(room, npc_key: str, text: str) -> None:
    npc = npc_in_room_by_key(room, npc_key)
    if npc:
        room.msg_contents(text, from_obj=npc)
    else:
        room.msg_contents(f"|w[Station]|n {text}")


def maybe_desk_ambience(
    character,
    npc_key: str,
    template: str,
    *,
    min_interval: float = DESK_AMBIENCE_MIN_INTERVAL_SEC,
) -> None:
    """
    Optional low-frequency room line for read-only desk use (listings / claims browse).
    Uses npc.ndb.last_desk_echo_at; no DB churn.
    """
    loc = character.location
    if not loc:
        return
    npc = npc_in_room_by_key(loc, npc_key)
    if not npc:
        return
    now = time.time()
    last = float(getattr(npc.ndb, "last_desk_echo_at", None) or 0.0)
    if now - last < min_interval:
        return
    npc.ndb.last_desk_echo_at = now
    station_room_echo(loc, npc, character, template)


def room_echo_web_action(room, player, template: str) -> None:
    """Room-visible line for web when no NPC is present; excludes acting character."""
    if not room or not player:
        return
    room.msg_contents(template, exclude=player, mapping={"player": player})
