from __future__ import annotations


class StationServiceError(Exception):
    """User-visible failure for station service NPCs."""


def require_npc_in_room(character, npc_key: str) -> object:
    loc = character.location
    if not loc:
        raise StationServiceError("You are not anywhere a clerk could help.")
    for obj in loc.contents:
        if getattr(obj, "key", None) == npc_key:
            return obj
    raise StationServiceError("That clerk is not here.")


def venue_id_for_caller(character) -> str | None:
    from world.venue_resolve import venue_id_for_object

    return venue_id_for_object(character)
