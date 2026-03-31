"""
Quest signal bus.

Call emit() from combat resolution, interactions, or other hooks:

    from world.quest_signals import emit
    emit(character, "combat_victory", {"encounter_id": "dock_ambush_01"})
"""

from __future__ import annotations

from typing import Any

from evennia.utils import logger


def emit(character, event_name: str, payload: dict[str, Any] | None = None) -> None:
    if character is None:
        return
    try:
        character.quests.on_event(event_name, payload or {})
    except Exception:
        logger.log_trace(
            f"[quests] emit error event={event_name!r} char={getattr(character, 'key', '?')}"
        )
