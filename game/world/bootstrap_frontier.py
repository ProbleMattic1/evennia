"""
Player arrival zone + hub links. Idempotent.

bootstrap_frontier: create room (runs before bootstrap_hub).
bootstrap_frontier_hub_links: exits after hub rename (runs after bootstrap_hub).
"""

from evennia import create_object, search_object

START_ROOM_KEY = "Frontier Transit Shell"

START_ROOM_DESC = (
    "A marginal dock: patch panels, recycled air, and a dead kiosk row. "
    "One display still flickers — someone hotwired it to a salvage cell. "
    "Coreward, the holos keep advertising a multiplex you cannot afford yet."
)


def get_player_start_room():
    """Single canonical spawn for Account/Guest create_character when location omitted."""
    found = search_object(START_ROOM_KEY)
    assert found, (
        f"{START_ROOM_KEY!r} missing — run bootstrap_frontier at cold start "
        "before any create_character without explicit location"
    )
    return found[0]


def _get_or_create_room(key, typeclass="typeclasses.rooms.Room", desc=""):
    found = search_object(key)
    if found:
        room = found[0]
    else:
        room = create_object(typeclass, key=key)
    if desc:
        room.db.desc = desc
    return room


def _get_or_create_exit(key, aliases, location, destination, typeclass="typeclasses.exits.Exit"):
    for obj in location.contents:
        if getattr(obj, "destination", None) == destination and obj.key == key:
            return obj
    return create_object(
        typeclass,
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )


def bootstrap_frontier():
    _get_or_create_room(START_ROOM_KEY, desc=START_ROOM_DESC)


def bootstrap_frontier_hub_links():
    from world.bootstrap_hub import get_hub_room

    frontier = search_object(START_ROOM_KEY)
    assert frontier, f"{START_ROOM_KEY!r} missing — bootstrap_frontier must run first"
    frontier = frontier[0]
    hub = get_hub_room()
    assert hub, "hub missing — bootstrap_hub must run before bootstrap_frontier_hub_links"
    _get_or_create_exit(
        "coreward transit",
        ["plex", "hub", "promenade", "nanomega", "core"],
        frontier,
        hub,
    )
    _get_or_create_exit(
        "rim shuttle",
        ["frontier", "rim", "arrival", "shell", "dock"],
        hub,
        frontier,
    )
