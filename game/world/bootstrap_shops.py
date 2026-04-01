"""
World bootstrap for general catalog shops (tech, mining, supply, toy), per venue hub.

Each kiosk has a unique vendor_id; catalog templates carry tag (vendor_id, category="vendor")
for every venue that sells that SKU.
"""

from evennia import create_object, search_object

from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids, apply_venue_metadata, get_venue

# (template key, vendor_slug matching venues shops, desc, price, inventory bucket)
CATALOG = (
    ("Tech Datapad", "tech-depot", "A slim personal datapad with standard productivity suites.", 450, "tool"),
    ("Tech Sensor Node", "tech-depot", "A compact environmental sensor package for hobbyists.", 890, "tool"),
    ("Tech Repair Drone", "tech-depot", "A palm-sized maintenance drone for light repairs.", 2400, "tool"),
    ("Supply Ration Pack", "general-supply", "A week's worth of balanced meal bars and hydration.", 85, "consumable"),
    ("Supply Medkit", "general-supply", "Standard trauma and stabilization kit.", 220, "consumable"),
    ("Supply Multitool", "general-supply", "All-in-one driver, cutter, and pry bar.", 140, "tool"),
    ("Toy Holo Chess", "toy-gallery", "Portable holographic chess set with classic variants.", 95, "novelty"),
    ("Toy Plush Bot", "toy-gallery", "A soft plush replica of a popular station robot.", 42, "novelty"),
    ("Toy Model Freighter", "toy-gallery", "Die-cast display model of a civilian freighter class.", 175, "novelty"),
)

_LEGACY_VENDOR_IDS = frozenset(
    {"tech-depot", "mining-outfitters", "general-supply", "toy-gallery"}
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


def _ensure_catalog_template(key, vendor_slug, desc, price_cr, inventory_bucket_tag: str):
    found = search_object(key)
    if found:
        obj = found[0]
    else:
        obj = create_object("typeclasses.objects.Object", key=key, location=None)
    obj.db.desc = desc
    obj.db.economy = {"base_price_cr": int(price_cr)}
    obj.db.is_template = True
    for leg in _LEGACY_VENDOR_IDS:
        if obj.tags.has(leg, category="vendor"):
            obj.tags.remove(leg, category="vendor")
    for venue_id in all_venue_ids():
        vid = f"{venue_id}-{vendor_slug}"
        obj.tags.add(vid, category="vendor")
    obj.tags.add(inventory_bucket_tag, category="inventory")
    obj.locks.add("get:false()")
    return obj


def bootstrap_shops():
    """Create catalog shops per venue and sample catalog items. Idempotent."""
    for venue_id in all_venue_ids():
        hub = hub_room_for_venue(venue_id)
        for spec in get_venue(venue_id)["shops"]:
            room = _get_or_create_room(spec["room_key"], desc=spec["room_desc"])
            apply_venue_metadata(room, venue_id)
            if spec["vendor_slug"] == "mining-outfitters":
                room.db.ui_ambient = {
                    "themeId": "industrial",
                    "label": spec["vendor_name"],
                    "tagline": "Extraction gear, claims, and field-rated kit.",
                    "bannerSlides": [
                        {
                            "id": "mo-1",
                            "title": spec["vendor_name"],
                            "body": spec["room_desc"],
                            "graphicKey": "industrial",
                        },
                        {
                            "id": "mo-2",
                            "title": "Commodity desk",
                            "body": "Spot rates echo from the multiplex exchange feed.",
                            "graphicKey": "asteroid",
                        },
                    ],
                    "marqueeLines": [
                        "Certified drills and survey gear in stock.",
                        "Deploy claims from the kiosk — haulers route to sovereign plants.",
                    ],
                    "chips": [{"id": "hazard", "text": "HAZMAT B"}],
                    "layoutHints": {"rightColumn": "commodity_board"},
                }
            _get_or_create_catalog_vendor(room, spec)
            if hub:
                _get_or_create_exit(
                    spec["hub_exit"],
                    spec["hub_aliases"],
                    hub,
                    room,
                )
                _get_or_create_exit(
                    "promenade",
                    ["back", "exit", "out", "plex", "hub"],
                    room,
                    hub,
                )

    for key, vendor_slug, desc, price, bucket in CATALOG:
        _ensure_catalog_template(key, vendor_slug, desc, price, bucket)

    print("[shops] Catalog vendors per venue; templates tagged with venue-scoped vendor_ids.")
    print("[shops] Bootstrap complete.")


# Control surface / legacy imports: flat list of {room_key, label} for all venues
def all_item_shop_specs():
    rows = []
    for venue_id in all_venue_ids():
        for spec in get_venue(venue_id)["shops"]:
            rows.append(
                {
                    "venue_id": venue_id,
                    "room_key": spec["room_key"],
                    "vendor_name": spec["vendor_name"],
                    "vendor_id": spec["vendor_id"],
                }
            )
    return rows
