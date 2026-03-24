"""
Batchcode bootstrap for a minimal shipyard demo.

Run with:
    batchcode/debug world.bootstrap_shipyard
    batchcode world.bootstrap_shipyard

Catalog is tag-based: items with tag (vendor_id, category="vendor") appear for sale.
Assign via Django admin (Object → Tags) or in-game @tag.
"""

from evennia import create_object, search_object, search_tag


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
    """Find or create an exit by name in a given location. Idempotent."""
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


def _get_or_create_shipyard(room):
    for obj in room.contents:
        if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            continue
        if getattr(obj.db, "catalog_mode", None) == "ships":
            shop = obj
            break
    else:
        shop = create_object("typeclasses.shops.CatalogVendor", key="shipyard kiosk", location=room, home=room)
        shop.db.catalog_mode = "ships"
    shop.db.desc = "A polished terminal lists civilian and commercial hulls currently available for purchase."
    shop.db.price_modifier = 1.0
    shop.db.tax_rate = 0.02
    shop.db.market_type = "normal"
    shop.db.vendor_id = "shipyard-kiosk"
    shop.db.vendor_name = "Meridian Civil Shipyard"
    shop.db.vendor_account = "vendor:shipyard-kiosk"
    return shop


def _tag_legacy_catalog(shop):
    """
    Ensure demo showroom hulls carry the vendor tag. Safe on every cold start.

    search_tag(vehicle_id) matches every hull with that id (templates + purchased copies).
    Only templates / legacy stock (no owner, not explicitly is_template=False) are tagged.
    Player-owned or sold copies are skipped and any stray vendor tag is removed so the
    kiosk catalog cannot list them after restart.
    """
    vendor_id = shop.db.vendor_id
    if not vendor_id:
        return
    _SHIPYARD_VEHICLE_IDS = ("sparrow-mk-v", "kestrel-mk-vi", "wayfarer-mk-vii")
    for vehicle_id in _SHIPYARD_VEHICLE_IDS:
        matches = search_tag(vehicle_id, category="vehicle_id")
        for obj in matches:
            # Never add haulers to the shipyard catalog
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
    """Create the Meridian shipyard demo. Safe to call multiple times (idempotent)."""
    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()

    showroom = _get_or_create_room(
        "Meridian Civil Shipyard",
        desc="A bright commercial shipyard lined with polished hulls, financing kiosks, and launch-bay displays.",
    )
    delivery = _get_or_create_room(
        "Meridian Delivery Hangar",
        desc="A secured hangar where purchased ships are staged for pickup.",
    )
    showroom.db.ship_delivery_room = delivery

    shop = _get_or_create_shipyard(showroom)
    shop.db.delivery_room = delivery

    _tag_legacy_catalog(shop)

    if hub:
        _get_or_create_exit("shipyard", ["yard", "meridian"], hub, showroom)
        _get_or_create_exit("back", ["exit", "promenade", "plex", "hub"], showroom, hub)

    _get_or_create_exit("hangar", ["delivery", "pickup"], showroom, delivery)
    _get_or_create_exit("showroom", ["back", "exit"], delivery, showroom)

    print("[shipyard] Rooms: Meridian Civil Shipyard, Meridian Delivery Hangar")
    print("[shipyard] Shop: shipyard kiosk (vendor_id=shipyard-kiosk)")
    print("[shipyard] Exits wired.")
    print("[shipyard] Bootstrap complete.")


