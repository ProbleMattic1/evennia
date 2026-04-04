"""
Bootstrap real estate offices, archives, and hub exits for each venue.

Global engines (discovery, operations, events) are created once.
Per-venue: office room, archive, exchange registry script, NPC placement.

Safe to call on every cold start.
"""

from evennia import create_object, create_script, search_object, search_script

from typeclasses.property_lot_registry import (
    PropertyLotExchangeRegistry,
    rebuild_property_exchange_registry,
)
from world.global_scripts_util import require_global_script

PROPERTY_LOTS_ARCHIVE_DESC = (
    "Sovereign record storage for titled parcels. Not on the public promenade map."
)

LOT_CATALOGUE = []


def _get_or_create_room(key, desc=""):
    found = search_object(key)
    room = found[0] if found else create_object("typeclasses.rooms.Room", key=key)
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


def _ensure_lot(spec, office_room):
    for obj in office_room.contents:
        if obj.key == spec["lot_key"] and obj.tags.has("property_lot", category="realty"):
            obj.db.lot_tier = spec["tier"]
            obj.db.zone = spec["zone"]
            obj.db.size_units = spec["size_units"]
            return obj, False

    lot = create_object(
        "typeclasses.property_lots.PropertyLot",
        key=spec["lot_key"],
        location=office_room,
        home=office_room,
    )
    lot.db.lot_tier = spec["tier"]
    lot.db.zone = spec["zone"]
    lot.db.size_units = spec["size_units"]
    s = spec["size_units"]
    lot.db.desc = (
        f"A {spec['zone']} parcel (Tier {spec['tier']}, "
        f"{s} unit{'s' if s != 1 else ''}). "
        "Available for immediate purchase."
    )
    return lot, True


def _place_npc(office_room, npc_key: str):
    found = search_object(npc_key)
    if not found:
        return
    npc = found[0]
    if npc.location != office_room:
        npc.move_to(office_room, quiet=True)
        print(f"[realty-office] Moved '{npc.key}' into '{office_room.key}'.")


def bootstrap_realty_office():
    from world.venue_resolve import hub_room_for_venue
    from world.venues import all_venue_ids, apply_venue_metadata, get_venue

    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        hub = hub_room_for_venue(venue_id)
        if not hub:
            print(f"[realty-office] Hub missing for {venue_id!r}; skip office.")
            continue

        realty = vspec["realty"]
        office = _get_or_create_room(realty["office_key"], desc=realty["office_desc"])
        apply_venue_metadata(office, venue_id)

        archive = _get_or_create_room(
            realty["archive_room_key"],
            desc=PROPERTY_LOTS_ARCHIVE_DESC,
        )
        apply_venue_metadata(archive, venue_id)

        _get_or_create_exit(
            "real estate",
            ["realty", "estate", "office", "realtor"],
            hub,
            office,
        )
        _get_or_create_exit(
            "promenade",
            ["back", "exit", "out", "plex", "hub"],
            office,
            hub,
        )

        created = sum(1 for spec in LOT_CATALOGUE if _ensure_lot(spec, office)[1])
        npc_key = vspec["npcs"]["realty_key"]
        _place_npc(office, npc_key)

        reg_key = realty["exchange_registry_script_key"]
        if search_script(reg_key):
            print(f"[realty-office] Registry exists: {reg_key}")
        else:
            create_script(PropertyLotExchangeRegistry, key=reg_key)
            print(f"[realty-office] Created PropertyLotExchangeRegistry: {reg_key}")

        print(
            f"[realty-office] Office '{realty['office_key']}' ({venue_id}): "
            f"{created} new catalogue lots."
        )

    rebuild_property_exchange_registry()

    disc = require_global_script("property_lot_discovery_engine")
    print(f"[realty-office] PropertyLotDiscoveryEngine: {disc.key}")

    op_reg = require_global_script("property_operation_registry")
    print(f"[realty-office] PropertyOperationRegistry: {op_reg.key}")

    op_eng = require_global_script("property_operations_engine")
    print(f"[realty-office] PropertyOperationsEngine: {op_eng.key}")

    ev_eng = require_global_script("property_events_engine")
    print(f"[realty-office] PropertyEventsEngine: {ev_eng.key}")

    print("[realty-office] Bootstrap complete.")
