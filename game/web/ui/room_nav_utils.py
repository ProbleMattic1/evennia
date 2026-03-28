"""
Shared helpers for web nav: exit destination resolution and mining-site visibility.

Used by views.nav_state and world_graph so hub→mining exit rules stay in one place.
"""

from __future__ import annotations

from evennia import search_object


def resolve_exit_destination_dict(ex: dict) -> object | None:
    """Resolve serialized exit dict (with ``destination`` room key) to a room object."""
    dest_key = ex.get("destination")
    if not dest_key:
        return None
    found = search_object(dest_key)
    return found[0] if found else None


def is_mining_site_room(room) -> tuple[bool, object | None]:
    if not room:
        return False, None
    for obj in room.contents:
        if obj.tags.has("mining_site", category="mining"):
            return True, obj
    return False, None


def should_show_mining_exit_dict(ex: dict, char) -> bool:
    """
    Whether a hub-style exit to ``ex['destination']`` should appear for ``char``.

    Matches legacy ``nav_state`` semantics: non–mining-site destinations always visible;
    mining sites hidden unless claimed by ``char``. When ``char`` is None, mining exits
    to claimed sites are hidden as well.
    """
    dest = resolve_exit_destination_dict(ex)
    is_site, site = is_mining_site_room(dest)
    if not is_site:
        return True
    if not getattr(site.db, "is_claimed", False):
        return False
    return site.db.owner == char
