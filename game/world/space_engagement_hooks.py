"""
Phase 4 hooks: space engagement → challenges + crime_record.

Called from SpaceEngagement after resolver events and on close.
"""

from __future__ import annotations

from typing import Any

from evennia.utils import logger


def _actor_id_for_character(state: dict, character) -> str | None:
    for actor in state.get("actors") or []:
        if actor.get("character_id") == character.id:
            return str(actor.get("id") or "") or None
    return None


def _target_is_player_ev(ev: dict, player_actor_id: str | None) -> bool:
    if not player_actor_id:
        return False
    kind = str(ev.get("kind") or "")
    if kind in ("kinetic_hit", "missile_hit"):
        return str(ev.get("target_id") or "") == player_actor_id
    if kind in ("heat_warning", "heat_critical"):
        return str(ev.get("actor_id") or "") == player_actor_id
    return False


def apply_engagement_events_to_participants(
    characters: list,
    events: list[dict],
    state: dict,
) -> None:
    """Emit challenge telemetry for each participant per resolver event."""
    if not events:
        return
    try:
        from world.challenges.challenge_signals import emit
    except Exception:
        return

    for ev in events:
        kind = str(ev.get("kind") or "")
        if kind == "error":
            continue
        for char in list(characters or []):
            if not char:
                continue
            aid = _actor_id_for_character(state, char)
            payload: dict[str, Any] = {
                "kind": kind,
                "engagement_tick": int(state.get("tick") or 0),
                "actor_id": ev.get("actor_id"),
                "target_id": ev.get("target_id"),
                "hull_pct": ev.get("hull_pct"),
                "heat": ev.get("heat"),
            }
            if aid:
                payload["player_actor_id"] = aid
                payload["target_is_player"] = _target_is_player_ev(ev, aid)
            try:
                emit(char, "space_engagement", payload)
            except Exception:
                logger.log_trace(
                    f"[space_engagement_hooks] emit failed char={getattr(char, 'key', '?')} kind={kind}"
                )


def apply_engagement_close_to_participants(
    characters: list,
    state: dict,
    *,
    bravo_profile_key: str = "",
) -> None:
    """Final emit + optional crime_record when the engagement ends."""
    tags = list(state.get("mission_tags") or [])
    victor_tag = next((t for t in tags if t.startswith("victor:")), None)
    victor = victor_tag.split(":", 1)[1] if victor_tag else ""

    try:
        from world.challenges.challenge_signals import emit
    except Exception:
        emit = None  # type: ignore

    profile = str(bravo_profile_key or "").strip().lower()

    for char in list(characters or []):
        if not char:
            continue
        player_side = None
        for a in state.get("actors") or []:
            if a.get("character_id") == char.id:
                player_side = a.get("side")
                break

        won = bool(victor and player_side and victor == player_side)

        if emit:
            try:
                emit(
                    char,
                    "space_engagement",
                    {
                        "kind": "engagement_closed",
                        "victor": victor,
                        "player_side": player_side,
                        "won": won,
                        "bravo_profile": profile or None,
                        "engagement_tick": int(state.get("tick") or 0),
                    },
                )
            except Exception:
                logger.log_trace(
                    f"[space_engagement_hooks] close emit failed char={getattr(char, 'key', '?')}"
                )

        try:
            cr = char.crime_record
        except Exception:
            continue

        if won and profile == "ghost_hull":
            cr.add_flag("ghost_hull_encounter_resolved")
        if won and profile == "pirate_fighter":
            cr.add_flag("pirate_engagement_survivor")
        if (not won) and profile == "patrol_corvette":
            cr.add_infraction(
                category="naval_contact",
                magnitude=1,
                note="Unfavorable outcome vs station picket (abstract)",
            )
