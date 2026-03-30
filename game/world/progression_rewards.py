"""
Apply TraitHandler changes when a character levels up. Called from Character.grant_xp.
"""

from __future__ import annotations

from typing import Any

from world.progression import LevelUpEvent

HP_PER_LEVEL = 2


def apply_level_up_rewards(character: Any, event: LevelUpEvent) -> None:
    """
    Persist trait updates after level is saved. HP max increases; athletics skill rises.
    """
    if not hasattr(character, "ensure_default_rpg_traits"):
        return
    character.ensure_default_rpg_traits()

    hp = character.vitals.get("hp")
    if hp:
        old_max = int(hp.max)
        hp.base = int(hp.base) + HP_PER_LEVEL
        new_max = int(hp.max)
        delta = new_max - old_max
        cur = int(hp.current)
        hp.current = min(cur + delta, new_max)

    ath = character.skills.get("athletics")
    if ath:
        ath.current = int(ath.current) + 1
