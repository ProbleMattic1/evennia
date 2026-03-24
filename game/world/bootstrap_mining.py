"""
World bootstrap for the mining system.

Runs from at_server_cold_start (at_server_startstop.py).  Idempotent.

Creates
-------
1. MiningEngine global script (if missing).
2. SiteDiscoveryEngine periodic script (generates unclaimed sites over time).
3. Refinery room(s) accessible from the hub.

Mining sites are NOT pre-seeded.  They are created dynamically:
  - On package purchase (via claim_utils.generate_mining_site)
  - Periodically by the SiteDiscoveryEngine script
"""

from evennia import create_object, create_script, search_object, search_script


# ---------------------------------------------------------------------------
# Site definitions — intentionally empty.
# Sites are generated dynamically by SiteDiscoveryEngine and on purchase.
# ---------------------------------------------------------------------------

MINING_SITES = []


REFINERY_ROOMS = [
    {
        "room_key": "Aurnom Ore Processing Plant",
        "room_desc": (
            "Heavy industrial equipment lines the floor of this processing bay. "
            "Conveyor systems, smelting units, and cutting bays handle everything "
            "from iron ore to gem-grade kimberlite.  The air smells of flux and heat."
        ),
        "refinery_key": "Ore Processing Unit",
        "refinery_desc": "A multi-stage processing platform handling ore smelting and gem cutting.",
        "hub_exit": "processing plant",
        "hub_aliases": ["processing", "refinery", "plant", "smelt"],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_room(key, desc=""):
    found = search_object(key)
    if found:
        room = found[0]
    else:
        room = create_object("typeclasses.rooms.Room", key=key)
    if desc:
        room.db.desc = desc
    return room


def _get_or_create_exit(key, aliases, location, destination):
    for obj in location.contents:
        if getattr(obj, "destination", None) == destination and obj.key == key:
            return obj
    return create_object(
        "typeclasses.exits.Exit",
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )



def _get_or_create_refinery(room, spec):
    """Find or create the Refinery object in room."""
    for obj in room.contents:
        if obj.tags.has("refinery", category="mining") and obj.key == spec["refinery_key"]:
            return obj
    ref = create_object(
        "typeclasses.refining.Refinery",
        key=spec["refinery_key"],
        location=room,
        home=room,
    )
    ref.db.desc = spec["refinery_desc"]
    return ref



# ---------------------------------------------------------------------------
# Main bootstrap
# ---------------------------------------------------------------------------

def bootstrap_mining():
    """
    Ensure the MiningEngine and SiteDiscoveryEngine exist; set up refinery rooms.
    Mining sites are generated dynamically — none are pre-seeded.
    Idempotent — safe to call on every cold start.
    """
    # -- Mining engine --
    found = search_script("mining_engine")
    if found:
        engine = found[0]
        print(f"[mining] Engine already exists: {engine.key}")
    else:
        engine = create_script("typeclasses.mining.MiningEngine")
        print(f"[mining] Created engine: {engine.key}")

    # -- Site discovery engine --
    from typeclasses.site_discovery import SiteDiscoveryEngine

    disc = search_script("site_discovery_engine")
    if disc:
        print(f"[mining] SiteDiscoveryEngine already exists: {disc[0].key}")
    else:
        create_script(SiteDiscoveryEngine)
        print("[mining] Created SiteDiscoveryEngine.")

    # -- Hub --
    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()

    # -- Refinery rooms --
    for spec in REFINERY_ROOMS:
        room = _get_or_create_room(spec["room_key"], desc=spec["room_desc"])
        ref = _get_or_create_refinery(room, spec)

        if hub:
            _get_or_create_exit(spec["hub_exit"], spec["hub_aliases"], hub, room)
            _get_or_create_exit(
                "promenade",
                ["back", "exit", "out", "plex", "hub"],
                room,
                hub,
            )

        print(f"[mining] Refinery '{ref.key}' in '{spec['room_key']}' ready.")

    print("[mining] Bootstrap complete.")
