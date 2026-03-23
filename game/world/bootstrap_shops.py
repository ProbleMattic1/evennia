"""
World bootstrap for general catalog shops (tech, mining, supply, toy).

Runs automatically from server/conf/at_server_cold_start (at_server_startstop.py)
on every cold start. Idempotent.

Optional manual run (same code path):
    batchcode world.bootstrap_shops

Each kiosk is a CatalogVendor with a unique vendor_id; catalog templates use
tag (vendor_id, category="vendor").
"""

from evennia import create_object, search_object


SHOPS = (
    {
        "room_key": "Aurnom Tech Depot",
        "room_desc": "Shelves of consumer electronics, interface modules, and field repair kits glow under cool strip lights.",
        "kiosk_key": "tech kiosk",
        "kiosk_desc": "A sleek terminal lists certified gadgets and spare compute cores.",
        "vendor_id": "tech-depot",
        "vendor_name": "Tech Depot",
        "vendor_account": "vendor:tech-depot",
        "hub_exit": "tech",
        "hub_aliases": ["techdepot", "electronics"],
    },
    {
        "room_key": "Aurnom Mining Outfitters",
        "room_desc": "Industrial racks hold extraction gear rated for vacuum and hard rock.",
        "kiosk_key": "mining supply kiosk",
        "kiosk_desc": "A rugged console catalogs drills, scanners, and crew-rated hazard wear.",
        "vendor_id": "mining-outfitters",
        "vendor_name": "Mining Outfitters",
        "vendor_account": "vendor:mining-outfitters",
        "hub_exit": "mining",
        "hub_aliases": ["miners", "outfitters"],
    },
    {
        "room_key": "Aurnom General Supply",
        "room_desc": "A compact mercantile bay stacked with consumables and everyday ship-board necessities.",
        "kiosk_key": "supply kiosk",
        "kiosk_desc": "An inventory terminal tracks rations, medical basics, and utility tools.",
        "vendor_id": "general-supply",
        "vendor_name": "General Supply",
        "vendor_account": "vendor:general-supply",
        "hub_exit": "supply",
        "hub_aliases": ["supplies", "general"],
    },
    {
        "room_key": "Aurnom Toy Gallery",
        "room_desc": "Colorful displays and low-grav novelty bins invite impulse buys.",
        "kiosk_key": "toy kiosk",
        "kiosk_desc": "A playful interface scrolls games, models, and soft goods.",
        "vendor_id": "toy-gallery",
        "vendor_name": "Toy Gallery",
        "vendor_account": "vendor:toy-gallery",
        "hub_exit": "toys",
        "hub_aliases": ["toy", "gallery"],
    },
)

CATALOG = (
    ("Tech Datapad", "tech-depot", "A slim personal datapad with standard productivity suites.", 450),
    ("Tech Sensor Node", "tech-depot", "A compact environmental sensor package for hobbyists.", 890),
    ("Tech Repair Drone", "tech-depot", "A palm-sized maintenance drone for light repairs.", 2400),
    ("Mining Drill Bits", "mining-outfitters", "Rated carbide bits for portable rock drills.", 320),
    ("Mining Ore Scanner", "mining-outfitters", "Handheld spectrometer tuned for common ore signatures.", 1100),
    ("Mining Hazard Suit", "mining-outfitters", "Disposable oversuit for dust and chemical splash.", 680),
    ("Supply Ration Pack", "general-supply", "A week's worth of balanced meal bars and hydration.", 85),
    ("Supply Medkit", "general-supply", "Standard trauma and stabilization kit.", 220),
    ("Supply Multitool", "general-supply", "All-in-one driver, cutter, and pry bar.", 140),
    ("Toy Holo Chess", "toy-gallery", "Portable holographic chess set with classic variants.", 95),
    ("Toy Plush Bot", "toy-gallery", "A soft plush replica of a popular station robot.", 42),
    ("Toy Model Freighter", "toy-gallery", "Die-cast display model of a civilian freighter class.", 175),
)


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


def _get_or_create_catalog_vendor(room, spec):
    kiosk = None
    for obj in room.contents:
        if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            continue
        if getattr(obj.db, "catalog_mode", None) == "ships":
            continue
        if getattr(obj.db, "vendor_id", None) == spec["vendor_id"]:
            kiosk = obj
            break
    if not kiosk:
        kiosk = create_object(
            "typeclasses.shops.CatalogVendor",
            key=spec["kiosk_key"],
            location=room,
            home=room,
        )
    kiosk.db.desc = spec["kiosk_desc"]
    kiosk.db.price_modifier = 1.0
    kiosk.db.tax_rate = 0.02
    kiosk.db.market_type = "normal"
    kiosk.db.vendor_id = spec["vendor_id"]
    kiosk.db.vendor_name = spec["vendor_name"]
    kiosk.db.vendor_account = spec["vendor_account"]
    return kiosk


def _ensure_catalog_template(key, vendor_id, desc, price_cr):
    found = search_object(key)
    if found:
        obj = found[0]
    else:
        obj = create_object("typeclasses.objects.Object", key=key, location=None)
    obj.db.desc = desc
    obj.db.economy = {"base_price_cr": int(price_cr)}
    obj.db.is_template = True
    obj.tags.add(vendor_id, category="vendor")
    obj.locks.add("get:false()")
    return obj


def bootstrap_shops():
    """Create four general shops and sample catalog items. Idempotent."""
    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()

    for spec in SHOPS:
        room = _get_or_create_room(spec["room_key"], desc=spec["room_desc"])
        _get_or_create_catalog_vendor(room, spec)
        if hub:
            _get_or_create_exit(
                spec["hub_exit"],
                spec["hub_aliases"],
                hub,
                room,
            )
            _get_or_create_exit("promenade", ["back", "exit", "out", "plex", "hub"], room, hub)

    for key, vendor_id, desc, price in CATALOG:
        _ensure_catalog_template(key, vendor_id, desc, price)

    print("[shops] Catalog vendors: tech-depot, mining-outfitters, general-supply, toy-gallery")
    print("[shops] Rooms created or updated; hub exits wired if NanoMegaPlex Promenade (#2) exists.")
    print("[shops] Bootstrap complete.")


