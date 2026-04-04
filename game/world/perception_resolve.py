"""
Deterministic spot check: observer perception vs mover stealth × environment.
"""

from __future__ import annotations


def _skill_val(character, skill_key: str) -> int:
    try:
        sk = character.skills.get(skill_key)
        if sk:
            return int(sk.value)
    except Exception:
        pass
    return 10


def resolve_spot(
    observer,
    mover,
    *,
    room_mod: float = 1.0,
    environment_mod: float = 1.0,
) -> tuple[bool, int]:
    """
    Returns (spotted, margin).

    ``room_mod`` / ``environment_mod`` multiply effective perception (values around 1.0).
    """
    per = _skill_val(observer, "perception_rating")
    sth = _skill_val(mover, "stealth_rating")
    eff_per = int(round(per * float(room_mod) * float(environment_mod)))
    margin = eff_per - sth
    return margin >= 0, margin


def environment_mods_for_character(character) -> float:
    """Combine venue environment snapshot perception modifier if available."""
    from world.venues import venue_id_for_object
    from evennia import GLOBAL_SCRIPTS

    vid = venue_id_for_object(character)
    if not vid:
        return 1.0
    eng = GLOBAL_SCRIPTS.get("world_environment_engine")
    if not eng:
        return 1.0
    row = (eng.db.by_venue or {}).get(vid) or {}
    return float(row.get("perception_mod") or 1.0)
