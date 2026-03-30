"""
Character level / XP rules. Mechanics live here; typeclasses and commands stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

BASE_XP_PER_LEVEL = 1000
GROWTH_EXPONENT = 1.0
MAX_LEVEL: Optional[int] = None


def xp_to_next_level(level: int) -> int:
    """Total XP required to complete this level tier (L -> L+1)."""
    if level < 1:
        level = 1
    need = int(round(BASE_XP_PER_LEVEL * (level**GROWTH_EXPONENT)))
    return max(1, need)


@dataclass
class LevelUpEvent:
    old_level: int
    new_level: int


@dataclass
class XpGrantResult:
    xp_gained: int
    level_ups: list[LevelUpEvent]
    xp_into_current: int
    xp_needed_for_next: int
    level: int
    capped: bool = False


def _get_level(char: Any) -> int:
    return int(getattr(char.db, "rpg_level", None) or 1)


def _get_xp_into(char: Any) -> int:
    return int(getattr(char.db, "rpg_xp_into_level", None) or 0)


def _set_progress(char: Any, level: int, xp_into: int) -> None:
    char.db.rpg_level = level
    char.db.rpg_xp_into_level = xp_into


def snapshot(char: Any) -> dict:
    """Read-only view for sheets, API, debugging."""
    level = _get_level(char)
    need = xp_to_next_level(level)
    into = _get_xp_into(char)
    return {
        "level": level,
        "xp_into_level": into,
        "xp_to_next": need,
        "fraction": (into / need) if need else 1.0,
    }


def add_xp(
    char: Any,
    amount: int,
    *,
    on_level_up: Optional[Callable[[Any, LevelUpEvent], None]] = None,
) -> XpGrantResult:
    """
    Add XP; may level up zero or many times. Persists to char.db.

    on_level_up: optional (character, event) for messaging and trait rewards.
    """
    if amount <= 0:
        level = _get_level(char)
        need = xp_to_next_level(level)
        return XpGrantResult(
            xp_gained=0,
            level_ups=[],
            xp_into_current=_get_xp_into(char),
            xp_needed_for_next=need,
            level=level,
        )

    level = _get_level(char)
    into = _get_xp_into(char)
    remaining = int(amount)
    events: list[LevelUpEvent] = []

    while remaining > 0:
        if MAX_LEVEL is not None and level >= MAX_LEVEL:
            _set_progress(char, level, into)
            return XpGrantResult(
                xp_gained=int(amount),
                level_ups=events,
                xp_into_current=into,
                xp_needed_for_next=xp_to_next_level(level),
                level=level,
                capped=True,
            )

        need = xp_to_next_level(level)
        space = need - into
        if remaining < space:
            into += remaining
            remaining = 0
            break

        remaining -= space
        old = level
        level += 1
        into = 0
        ev = LevelUpEvent(old_level=old, new_level=level)
        events.append(ev)
        if on_level_up:
            on_level_up(char, ev)

    _set_progress(char, level, into)
    return XpGrantResult(
        xp_gained=int(amount),
        level_ups=events,
        xp_into_current=into,
        xp_needed_for_next=xp_to_next_level(level),
        level=level,
        capped=bool(MAX_LEVEL is not None and level >= MAX_LEVEL),
    )
