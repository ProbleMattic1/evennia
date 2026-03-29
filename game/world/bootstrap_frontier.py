"""
Player arrival zone + Frontier Promenade + hub links. Idempotent.

bootstrap_frontier: transit shell + frontier promenade (runs before bootstrap_hub).
bootstrap_frontier_hub_links: exits after hub rename (runs after bootstrap_hub).
"""

from evennia import create_object, search_object

START_ROOM_KEY = "Frontier Transit Shell"

START_ROOM_DESC = (
    "A marginal dock: patch panels, recycled air, and a dead kiosk row. "
    "One display still flickers — someone hotwired it to a salvage cell. "
    "Coreward, the holos keep advertising a multiplex you cannot afford yet."
)

FRONTIER_PROMENADE_KEY = "Frontier Promenade"
FRONTIER_PROMENADE_DESC = (
    "A cramped outpost promenade: vendor strips, recycled signage, and "
    "threadbare holos promising the same services as coreward — on frontier terms."
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
    from world.venues import apply_venue_metadata

    shell = _get_or_create_room(START_ROOM_KEY, desc=START_ROOM_DESC)
    apply_venue_metadata(shell, "frontier_outpost")
    prom = _get_or_create_room(FRONTIER_PROMENADE_KEY, desc=FRONTIER_PROMENADE_DESC)
    apply_venue_metadata(prom, "frontier_outpost")


def bootstrap_frontier_hub_links():
    from world.bootstrap_hub import get_hub_room

    frontier_shell = search_object(START_ROOM_KEY)
    assert frontier_shell, f"{START_ROOM_KEY!r} missing — bootstrap_frontier must run first"
    frontier_shell = frontier_shell[0]

    fhub = search_object(FRONTIER_PROMENADE_KEY)
    assert fhub, f"{FRONTIER_PROMENADE_KEY!r} missing — bootstrap_frontier must run first"
    fhub = fhub[0]

    nanomega_hub = get_hub_room()
    assert nanomega_hub, "hub missing — bootstrap_hub must run before bootstrap_frontier_hub_links"

    _get_or_create_exit(
        "coreward transit",
        ["plex", "hub", "promenade", "nanomega", "core"],
        frontier_shell,
        nanomega_hub,
    )
    _get_or_create_exit(
        "rim shuttle",
        ["frontier", "rim", "arrival", "shell", "dock"],
        nanomega_hub,
        frontier_shell,
    )

    _get_or_create_exit(
        "portside concourse",
        ["frontier plex", "local promenade", "outpost", "yard", "portside"],
        frontier_shell,
        fhub,
    )
    _get_or_create_exit(
        "rim dock",
        ["transit shell", "shell", "dock", "arrival", "transit"],
        fhub,
        frontier_shell,
    )
