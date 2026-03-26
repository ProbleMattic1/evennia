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
        if engine.interval != 60:
            engine.interval = 60
            engine.restart()
            print(f"[mining] Engine already exists: {engine.key} — interval updated to 60s.")
        else:
            print(f"[mining] Engine already exists: {engine.key}")
    else:
        engine = create_script("typeclasses.mining.MiningEngine")
        print(f"[mining] Created engine: {engine.key}")

    # -- Package listings script + container --
    pkg_list = search_script("package_listings")
    if pkg_list:
        print(f"[mining] Package listings script already exists: {pkg_list[0].key}")
    else:
        from typeclasses.package_listings import PackageListingsScript
        create_script(PackageListingsScript, key="package_listings")
        print("[mining] Created package_listings script.")

    prop_list = search_script("property_listings")
    if prop_list:
        print(f"[mining] Property listings script already exists: {prop_list[0].key}")
    else:
        from typeclasses.property_listings import PropertyListingsScript
        create_script(PropertyListingsScript, key="property_listings")
        print("[mining] Created property_listings script.")

    claim_list = search_script("claim_listings")
    if claim_list:
        print(f"[mining] Claim listings script already exists: {claim_list[0].key}")
    else:
        from typeclasses.claim_listings import ClaimListingsScript
        create_script(ClaimListingsScript, key="claim_listings")
        print("[mining] Created claim_listings script.")

    # -- Hub for listings container (get_hub_room already imported above) --

    from world.bootstrap_hub import get_hub_room
    hub_for_listings = get_hub_room()
    if hub_for_listings:
        container = None
        for obj in hub_for_listings.contents:
            if obj.key == "Package Listings" and getattr(obj.db, "is_listings_container", False):
                container = obj
                break
        if not container:
            container = create_object("typeclasses.objects.Object", key="Package Listings", location=hub_for_listings, home=hub_for_listings)
            container.db.desc = "A board where mining packages are listed for sale."
            container.db.is_listings_container = True
            container.locks.add("get:false();drop:false()")
            print("[mining] Created Package Listings container in hub.")

        ccontainer = None
        for obj in hub_for_listings.contents:
            if obj.key == "Claim Listings" and getattr(obj.db, "is_claim_listings_container", False):
                ccontainer = obj
                break
        if not ccontainer:
            ccontainer = create_object(
                "typeclasses.objects.Object",
                key="Claim Listings",
                location=hub_for_listings,
                home=hub_for_listings,
            )
            ccontainer.db.desc = "Escrow for mining claim deeds listed for sale."
            ccontainer.db.is_claim_listings_container = True
            ccontainer.locks.add("get:false();drop:false()")
            print("[mining] Created Claim Listings container in hub.")

        dcontainer = None
        for obj in hub_for_listings.contents:
            if obj.key == "Property Deed Listings" and getattr(obj.db, "is_property_deed_listings_container", False):
                dcontainer = obj
                break
        if not dcontainer:
            dcontainer = create_object(
                "typeclasses.objects.Object",
                key="Property Deed Listings",
                location=hub_for_listings,
                home=hub_for_listings,
            )
            dcontainer.db.desc = "Escrow for property parcel deeds listed by players."
            dcontainer.db.is_property_deed_listings_container = True
            dcontainer.locks.add("get:false();drop:false()")
            print("[mining] Created Property Deed Listings container in hub.")

    deed_list = search_script("property_deed_listings")
    if deed_list:
        print(f"[mining] Property deed listings script already exists: {deed_list[0].key}")
    else:
        from typeclasses.property_deed_listings import PropertyDeedListingsScript

        create_script(PropertyDeedListingsScript, key="property_deed_listings")
        print("[mining] Created property_deed_listings script.")

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
