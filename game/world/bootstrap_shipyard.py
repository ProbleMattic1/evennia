"""
Batchcode bootstrap for shipyard demo rooms + kiosk, per venue hub.
"""

from evennia import create_object, search_object, search_tag

from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids, apply_venue_metadata, get_venue


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
        if obj.destination == destination and obj.key == key:
            return obj
    return create_object(
        typeclass,
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )


def _get_or_create_shipyard(room, vendor_id: str, vendor_name: str, vendor_account: str):
    for obj in room.contents:
        if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            continue
        if getattr(obj.db, "catalog_mode", None) == "ships":
            shop = obj
            break
    else:
        shop = create_object(
            "typeclasses.shops.CatalogVendor",
            key="shipyard kiosk",
            location=room,
            home=room,
        )
        shop.db.catalog_mode = "ships"
    shop.db.desc = "A polished terminal lists civilian and commercial hulls currently available for purchase."
    shop.db.price_modifier = 1.0
    shop.db.tax_rate = 0.02
    shop.db.market_type = "normal"
    shop.db.vendor_id = vendor_id
    shop.db.vendor_name = vendor_name
    shop.db.vendor_account = vendor_account
    return shop


def _tag_legacy_catalog(shop):
    vendor_id = shop.db.vendor_id
    if not vendor_id:
        return
    _SHIPYARD_VEHICLE_IDS = ("sparrow-mk-v", "kestrel-mk-vi", "wayfarer-mk-vii")
    for vehicle_id in _SHIPYARD_VEHICLE_IDS:
        matches = search_tag(vehicle_id, category="vehicle_id")
        for obj in matches:
            if getattr(obj.db, "vehicle_kind", None) == "hauler":
                if obj.tags.has(vendor_id, category="vendor"):
                    obj.tags.remove(vendor_id, category="vendor")
                continue
            if getattr(obj.db, "owner", None):
                if obj.tags.has(vendor_id, category="vendor"):
                    obj.tags.remove(vendor_id, category="vendor")
                continue
            if getattr(obj.db, "is_template", None) is False:
                if obj.tags.has(vendor_id, category="vendor"):
                    obj.tags.remove(vendor_id, category="vendor")
                continue
            obj.tags.add(vendor_id, category="vendor")
            obj.db.is_template = True
            obj.locks.add("get:false()")
            print(f"[shipyard] Tagged {obj.key} for vendor {vendor_id}")


def bootstrap_shipyard():
    """Create shipyard rooms and kiosk for each venue. Idempotent."""
    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        sy = vspec["shipyard"]
        hub = hub_room_for_venue(venue_id)

        showroom = _get_or_create_room(
            sy["showroom_key"],
            desc=sy["showroom_desc"],
        )
        apply_venue_metadata(showroom, venue_id)
        delivery = _get_or_create_room(
            sy["delivery_key"],
            desc=sy["delivery_desc"],
        )
        apply_venue_metadata(delivery, venue_id)
        showroom.db.ship_delivery_room = delivery

        shop = _get_or_create_shipyard(
            showroom,
            sy["vendor_id"],
            sy["vendor_name"],
            sy["vendor_account"],
        )
        shop.db.delivery_room = delivery

        _tag_legacy_catalog(shop)

        if hub:
            _get_or_create_exit(
                sy["hub_exit"],
                sy["hub_aliases"],
                hub,
                showroom,
            )
            _get_or_create_exit(
                "back",
                ["exit", "promenade", "plex", "hub"],
                showroom,
                hub,
            )

        _get_or_create_exit("hangar", ["delivery", "pickup"], showroom, delivery)
        _get_or_create_exit("showroom", ["back", "exit"], delivery, showroom)

        print(f"[shipyard] {venue_id}: {sy['showroom_key']}, vendor_id={sy['vendor_id']}")

    print("[shipyard] Bootstrap complete.")
