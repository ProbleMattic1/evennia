"""
Geological survey at a MiningSite — requires deployed MiningScanner (room + binding).

Used by telnet (CmdSurvey) and web (handle_survey / play_interact).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from world.web_interactions import InteractionError, InteractionLine

if TYPE_CHECKING:
    pass

SURVEY_COOLDOWN_KEY = "survey_scan"
SURVEY_COOLDOWN_SEC = 3.0


def resolve_mining_site_in_room(room) -> Any | None:
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("mining_site", category="mining"):
            return obj
    return None


def room_has_deployed_scanner(room, character, site) -> bool:
    if not room or not site:
        return False
    for obj in room.contents:
        is_tc = getattr(obj, "is_typeclass", None)
        if not callable(is_tc):
            continue
        try:
            if not is_tc("typeclasses.mining_scanner.MiningScanner", exact=False):
                continue
        except (AttributeError, TypeError):
            continue
        if not getattr(obj.db, "is_deployed", False):
            continue
        if getattr(obj.db, "owner", None) != character:
            continue
        if getattr(obj.db, "deploy_site_ref", None) != site:
            continue
        return True
    return False


def execute_survey(character) -> InteractionLine:
    """
    Advance survey one tier. Applies cooldown on success.
    Raises InteractionError on failure.
    """
    if not character.cooldowns.ready(SURVEY_COOLDOWN_KEY):
        left = float(character.cooldowns.time_left(SURVEY_COOLDOWN_KEY))
        raise InteractionError(f"Survey equipment is still recalibrating ({left:.1f}s).")

    loc = character.location
    if not loc:
        raise InteractionError("There is no minable deposit here.")

    site = resolve_mining_site_in_room(loc)
    if not site:
        raise InteractionError("There is no minable deposit here.")

    if not room_has_deployed_scanner(loc, character, site):
        raise InteractionError(
            "You need a deployed Mining Scanner — Basic Stationary at this deposit "
            "to run a geological survey. Use |wdeployminingscanner|n."
        )

    new_level, report = site.advance_survey()

    if getattr(site.db, "discovery_pending", False) and site.tags.has("mining_site", category="mining"):
        from django.utils import timezone

        site.db.discovered_by = character
        site.db.discovery_pending = False
        site.db.discovered_at = timezone.now()
        from world.claims_market_read_model import invalidate_claims_market_snapshot

        invalidate_claims_market_snapshot()

    from typeclasses.mining import SURVEY_LEVELS

    label = SURVEY_LEVELS.get(new_level, "?")
    if new_level >= 3:
        dialogue = f"|wSurvey complete ({label}).|n\n{report}"
    else:
        remaining = 3 - new_level
        dialogue = (
            f"|wSurvey advanced to level {new_level} ({label}).|n  "
            f"({remaining} more survey{'s' if remaining > 1 else ''} to full assessment)\n{report}"
        )

    character.cooldowns.add(SURVEY_COOLDOWN_KEY, SURVEY_COOLDOWN_SEC)
    return InteractionLine(dialogue, "survey", None)
