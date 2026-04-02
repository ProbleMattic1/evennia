"""
World bootstrap for the mining system.

Runs from at_server_cold_start (at_server_startstop.py).  Idempotent.

Creates
-------
1. MiningEngine global script (if missing).
2. SiteDiscoveryEngine periodic script (generates unclaimed sites over time).
3. Ore processing plant room + separate refinery chamber per venue (hub → plant; hub → refinery; no direct plant ↔ refinery).

Mining sites are NOT pre-seeded.  They are created dynamically:
  - On package purchase (via claim_utils.generate_mining_site)
  - Periodically by the SiteDiscoveryEngine script
"""

from evennia import create_object, create_script, search_object, search_script

MINING_SITES = []


def _get_or_create_room(key, desc=""):
    found = search_object(key)
    if found:
        room = found[0]
    else:
        room = create_object("typeclasses.rooms.Room", key=key)
    if desc:
        room.db.desc = desc
    return room


def _get_or_create_exit(key, aliases, location, destination, nav_order=None):
    for obj in location.contents:
        if getattr(obj, "destination", None) == destination and obj.key == key:
            if nav_order is not None:
                obj.db.nav_order = int(nav_order)
            return obj
    exit_obj = create_object(
        "typeclasses.exits.Exit",
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )
    if nav_order is not None:
        exit_obj.db.nav_order = int(nav_order)
    return exit_obj


def _get_or_create_refinery(room, refinery_key, refinery_desc):
    """Find or create the Refinery object in room."""
    for obj in room.contents:
        if obj.tags.has("refinery", category="mining") and obj.key == refinery_key:
            return obj
    ref = create_object(
        "typeclasses.refining.Refinery",
        key=refinery_key,
        location=room,
        home=room,
    )
    ref.db.desc = refinery_desc
    return ref


def _ensure_main_refinery_in_chamber(refinery_room, plant_room, refinery_key, refinery_desc):
    """
    Venue main Refinery lives in ``refinery_room``; migrate from ``plant_room`` if needed.
    """
    for obj in refinery_room.contents:
        if obj.tags.has("refinery", category="mining") and obj.key == refinery_key:
            return obj
    for obj in plant_room.contents:
        if obj.tags.has("refinery", category="mining") and obj.key == refinery_key:
            obj.move_to(refinery_room, quiet=True)
            obj.home = refinery_room
            return obj
    return _get_or_create_refinery(refinery_room, refinery_key, refinery_desc)


def bootstrap_mining():
    """
    Ensure the MiningEngine and SiteDiscoveryEngine exist; set up refinery rooms per venue.
    Idempotent — safe to call on every cold start.
    """
    from typeclasses.claim_listings import ClaimListingsScript, claim_listings_script_key
    from typeclasses.package_listings import PackageListingsScript
    from typeclasses.packages import package_listings_script_key
    from typeclasses.property_deed_listings import PropertyDeedListingsScript
    from typeclasses.property_deed_market import property_deed_listings_script_key
    from typeclasses.site_discovery import SiteDiscoveryEngine
    from world.venues import all_venue_ids, apply_venue_metadata, get_venue

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

    prop_list = search_script("property_listings")
    if prop_list:
        print(f"[mining] Property listings script already exists: {prop_list[0].key}")
    else:
        from typeclasses.property_listings import PropertyListingsScript

        create_script(PropertyListingsScript, key="property_listings")
        print("[mining] Created property_listings script.")

    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        hub = search_object(vspec["hub_key"])
        hub = hub[0] if hub else None
        if hub:
            apply_venue_metadata(hub, venue_id)

        pk = package_listings_script_key(venue_id)
        if search_script(pk):
            print(f"[mining] Package listings script exists: {pk}")
        else:
            create_script(PackageListingsScript, key=pk)
            print(f"[mining] Created package listings script: {pk}")

        ck = claim_listings_script_key(venue_id)
        if search_script(ck):
            print(f"[mining] Claim listings script exists: {ck}")
        else:
            create_script(ClaimListingsScript, key=ck)
            print(f"[mining] Created claim listings script: {ck}")

        dk = property_deed_listings_script_key(venue_id)
        if search_script(dk):
            print(f"[mining] Property deed listings script exists: {dk}")
        else:
            create_script(PropertyDeedListingsScript, key=dk)
            print(f"[mining] Created property deed listings script: {dk}")

        if hub:
            pkg_key = "Package Listings" if venue_id == "nanomega_core" else "Frontier Package Listings"
            container = None
            for obj in hub.contents:
                if getattr(obj.db, "is_listings_container", False):
                    container = obj
                    break
            if not container:
                container = create_object(
                    "typeclasses.objects.Object",
                    key=pkg_key,
                    location=hub,
                    home=hub,
                )
                container.db.desc = "A board where mining packages are listed for sale."
                container.db.is_listings_container = True
                container.locks.add("get:false();drop:false()")
                print(f"[mining] Created {pkg_key!r} container in {hub.key!r}.")

            claim_key = "Claim Listings" if venue_id == "nanomega_core" else "Frontier Claim Listings"
            ccontainer = None
            for obj in hub.contents:
                if getattr(obj.db, "is_claim_listings_container", False):
                    ccontainer = obj
                    break
            if not ccontainer:
                ccontainer = create_object(
                    "typeclasses.objects.Object",
                    key=claim_key,
                    location=hub,
                    home=hub,
                )
                ccontainer.db.desc = "Escrow for mining claim deeds listed for sale."
                ccontainer.db.is_claim_listings_container = True
                ccontainer.locks.add("get:false();drop:false()")
                print(f"[mining] Created {claim_key!r} container in {hub.key!r}.")

            deed_key = (
                "Property Deed Listings"
                if venue_id == "nanomega_core"
                else "Frontier Property Deed Listings"
            )
            dcontainer = None
            for obj in hub.contents:
                if getattr(obj.db, "is_property_deed_listings_container", False):
                    dcontainer = obj
                    break
            if not dcontainer:
                dcontainer = create_object(
                    "typeclasses.objects.Object",
                    key=deed_key,
                    location=hub,
                    home=hub,
                )
                dcontainer.db.desc = "Escrow for property parcel deeds listed by players."
                dcontainer.db.is_property_deed_listings_container = True
                dcontainer.locks.add("get:false();drop:false()")
                print(f"[mining] Created {deed_key!r} container in {hub.key!r}.")

    disc = search_script("site_discovery_engine")
    if disc:
        print(f"[mining] SiteDiscoveryEngine already exists: {disc[0].key}")
    else:
        create_script(SiteDiscoveryEngine)
        print("[mining] Created SiteDiscoveryEngine.")

    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        proc = vspec["processing"]
        plant_room = _get_or_create_room(proc["plant_room_key"], desc=proc["plant_room_desc"])
        apply_venue_metadata(plant_room, venue_id)
        plant_titles = {
            "nanomega_core": (
                "Ore Processing Plant",
                "Heavy conveyors, smelting manifolds, treasury-linked receiving bays.",
            ),
            "frontier_outpost": (
                "Frontier Ore Plant",
                "Scaled conveyors and portable smelters; rim tariffs apply.",
            ),
        }
        ptitle, ptag = plant_titles.get(
            venue_id,
            ("Ore Processing Plant", (proc.get("plant_room_desc") or "")[:160]),
        )
        plant_room.db.ui_ambient = {
            "themeId": "industrial",
            "label": ptitle,
            "tagline": ptag,
            "bannerSlides": [
                {
                    "id": "plant-hero",
                    "title": ptitle,
                    "body": ptag,
                    "graphicKey": "refinery",
                },
            ],
            "marqueeLines": [
                "Yield to thermal load warnings.",
                "Use the Processor kiosk for silo and hauler routing.",
            ],
            "chips": [{"id": "proc", "text": "PROCESS"}],
        }
        refinery_key = proc["refinery_room_key"]
        refinery_desc = proc["refinery_room_desc"]
        refinery_room = _get_or_create_room(refinery_key, desc=refinery_desc)
        apply_venue_metadata(refinery_room, venue_id)
        ref = _ensure_main_refinery_in_chamber(
            refinery_room, plant_room, proc["refinery_key"], proc["refinery_desc"]
        )

        hub = search_object(vspec["hub_key"])
        hub = hub[0] if hub else None
        if hub:
            _get_or_create_exit(
                proc["hub_exit"], proc["hub_aliases"], hub, plant_room, nav_order=-2
            )
            _get_or_create_exit(
                proc["refinery_hub_exit"],
                proc["refinery_hub_aliases"],
                hub,
                refinery_room,
                nav_order=-1,
            )
            _get_or_create_exit(
                "promenade",
                ["back", "exit", "out", "plex", "hub"],
                plant_room,
                hub,
            )
            _get_or_create_exit(
                "promenade",
                ["back", "exit", "out", "plex", "hub"],
                refinery_room,
                hub,
            )

        print(f"[mining] Refinery '{ref.key}' in '{refinery_key}' ({venue_id}) ready.")

    print("[mining] Bootstrap complete.")
