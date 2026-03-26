"""
Bootstrap the NanoMegaPlex Real Estate Office room, hub exits, and property-lot inventory.

Creates
-------
- "NanoMegaPlex Real Estate Office" room
- "Property Lots Archive" void room (claimed parcels moved here after sale)
- Hub exit "real estate" (aliases: realty, estate, office, realtor) → office
- Office exit "promenade" (aliases: back, exit, out, plex, hub) → hub
- Property lots from LOT_CATALOGUE (idempotent — attrs updated each run; lots never deleted)
- PropertyLotExchangeRegistry script + rebuild of listable IDs from tags
- PropertyLotDiscoveryEngine periodic restock script
- PropertyOperationRegistry + PropertyOperationsEngine (parcel income tick)
- Moves the NanoMegaPlex Real Estate NPC into the office (if they exist)

Safe to call on every cold start.
"""

from evennia import create_object, create_script, search_object, search_script

from typeclasses.property_lot_discovery import PropertyLotDiscoveryEngine
from typeclasses.property_lot_registry import (
    CLAIMED_LOTS_ARCHIVE_ROOM_KEY,
    PropertyLotExchangeRegistry,
    rebuild_property_exchange_registry,
)
from typeclasses.property_operation_registry import PropertyOperationRegistry
from typeclasses.property_operations_engine import PropertyOperationsEngine

REALTY_OFFICE_KEY  = "NanoMegaPlex Real Estate Office"
REALTY_OFFICE_DESC = (
    "A clean, well-lit suite branching off the NanoMegaPlex Promenade. "
    "Holographic lot schematics rotate slowly behind a polished reception desk. "
    "Standard and prime parcels rotate on the sovereign exchange, with fresh "
    "survey listings as inventory turns. The NanoMegaPlex Real Estate agent "
    "stands ready to assist."
)

PROPERTY_LOTS_ARCHIVE_DESC = (
    "Sovereign record storage for titled parcels. Not on the public promenade map."
)

# ---------------------------------------------------------------------------
# Lot catalogue — optional fixed seed lots in the office (idempotent on lot_key).
# Empty at cold start; PropertyLotDiscoveryEngine adds parcels over time.
# Sold lots (is_claimed=True) are never recreated from catalogue; the row idles.
# ---------------------------------------------------------------------------
LOT_CATALOGUE = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_create_room(key, desc=""):
    found = search_object(key)
    room  = found[0] if found else create_object("typeclasses.rooms.Room", key=key)
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
    """
    Create a PropertyLot if one with spec['lot_key'] does not yet exist in the office.
    If it already exists, update mutable attributes (tier/zone/size_units) in case
    the catalogue spec was edited after initial creation.
    Returns (lot, created: bool).
    """
    for obj in office_room.contents:
        if obj.key == spec["lot_key"] and obj.tags.has("property_lot", category="realty"):
            obj.db.lot_tier   = spec["tier"]
            obj.db.zone       = spec["zone"]
            obj.db.size_units = spec["size_units"]
            return obj, False

    lot = create_object(
        "typeclasses.property_lots.PropertyLot",
        key=spec["lot_key"],
        location=office_room,
        home=office_room,
    )
    lot.db.lot_tier   = spec["tier"]
    lot.db.zone       = spec["zone"]
    lot.db.size_units = spec["size_units"]
    s = spec["size_units"]
    lot.db.desc = (
        f"A {spec['zone']} parcel (Tier {spec['tier']}, "
        f"{s} unit{'s' if s != 1 else ''}). "
        "Available for immediate purchase."
    )
    return lot, True


def _place_npc(office_room):
    """Move the NanoMegaPlex Real Estate character into the office if they exist."""
    from typeclasses.characters import NANOMEGA_REALTY_CHARACTER_KEY

    found = search_object(NANOMEGA_REALTY_CHARACTER_KEY)
    if not found:
        return
    npc = found[0]
    if npc.location != office_room:
        npc.move_to(office_room, quiet=True)
        print(f"[realty-office] Moved '{npc.key}' into '{office_room.key}'.")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def bootstrap_realty_office():
    """Idempotent — safe to call on every cold start."""
    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()
    if not hub:
        print("[realty-office] Hub room not found; skipping.")
        return

    office = _get_or_create_room(REALTY_OFFICE_KEY, desc=REALTY_OFFICE_DESC)
    _get_or_create_room(CLAIMED_LOTS_ARCHIVE_ROOM_KEY, desc=PROPERTY_LOTS_ARCHIVE_DESC)

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
    _place_npc(office)

    reg = search_script("property_lot_exchange_registry")
    if reg:
        print(f"[realty-office] PropertyLotExchangeRegistry exists: {reg[0].key}")
    else:
        create_script(PropertyLotExchangeRegistry)
        print("[realty-office] Created PropertyLotExchangeRegistry.")

    rebuild_property_exchange_registry()

    disc = search_script("property_lot_discovery_engine")
    if disc:
        print(f"[realty-office] PropertyLotDiscoveryEngine exists: {disc[0].key}")
    else:
        create_script(PropertyLotDiscoveryEngine)
        print("[realty-office] Created PropertyLotDiscoveryEngine.")

    op_reg = search_script("property_operation_registry")
    if op_reg:
        print(f"[realty-office] PropertyOperationRegistry exists: {op_reg[0].key}")
    else:
        create_script(PropertyOperationRegistry)
        print("[realty-office] Created PropertyOperationRegistry.")

    op_eng = search_script("property_operations_engine")
    if op_eng:
        print(f"[realty-office] PropertyOperationsEngine exists: {op_eng[0].key}")
    else:
        create_script(PropertyOperationsEngine)
        print("[realty-office] Created PropertyOperationsEngine.")

    print(
        f"[realty-office] Office ready: '{REALTY_OFFICE_KEY}'. "
        f"{created} new lots created ({len(LOT_CATALOGUE)} total in catalogue)."
    )
