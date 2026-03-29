"""
Venue registry: stable room keys, bank branches, services, and NPC keys per ecosystem.

Bootstraps iterate VENUES.values(); runtime code resolves venue from room/character.
"""

from typeclasses.characters import (
    FRONTIER_ADVERTISING_CHARACTER_KEY,
    FRONTIER_CONSTRUCTION_CHARACTER_KEY,
    FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY,
    FRONTIER_REALTY_CHARACTER_KEY,
    NANOMEGA_ADVERTISING_CHARACTER_KEY,
    NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
    NANOMEGA_REALTY_CHARACTER_KEY,
    PROMENADE_GUIDE_CHARACTER_KEY,
)

VENUE_TAG_CATEGORY = "venue"
VENUE_CONTROLLER_SCRIPT_TAG_CATEGORY = "venue_controller"

_SHOP_TEMPLATE = (
    # room_key_suffix uses venue label in room name for global uniqueness
    {
        "suffix": "Tech Depot",
        "room_desc": "Shelves of consumer electronics, interface modules, and field repair kits glow under cool strip lights.",
        "kiosk_key": "tech kiosk",
        "kiosk_desc": "A sleek terminal lists certified gadgets and spare compute cores.",
        "vendor_slug": "tech-depot",
        "vendor_name": "Tech Depot",
        "hub_exit": "tech",
        "hub_aliases": ["techdepot", "electronics"],
    },
    {
        "suffix": "Mining Outfitters",
        "room_desc": "Industrial racks hold extraction gear rated for vacuum and hard rock.",
        "kiosk_key": "mining supply kiosk",
        "kiosk_desc": "A rugged console catalogs drills, scanners, and crew-rated hazard wear.",
        "vendor_slug": "mining-outfitters",
        "vendor_name": "Mining Outfitters",
        "hub_exit": "mining",
        "hub_aliases": ["miners", "outfitters"],
    },
    {
        "suffix": "General Supply",
        "room_desc": "A compact mercantile bay stacked with consumables and everyday ship-board necessities.",
        "kiosk_key": "supply kiosk",
        "kiosk_desc": "An inventory terminal tracks rations, medical basics, and utility tools.",
        "vendor_slug": "general-supply",
        "vendor_name": "General Supply",
        "hub_exit": "supply",
        "hub_aliases": ["supplies", "general"],
    },
    {
        "suffix": "Toy Gallery",
        "room_desc": "Colorful displays and low-grav novelty bins invite impulse buys.",
        "kiosk_key": "toy kiosk",
        "kiosk_desc": "A playful interface scrolls games, models, and soft goods.",
        "vendor_slug": "toy-gallery",
        "vendor_name": "Toy Gallery",
        "hub_exit": "toys",
        "hub_aliases": ["toy", "gallery"],
    },
)


def _shop_specs_for_venue(venue_id: str, room_prefix: str):
    out = []
    for row in _SHOP_TEMPLATE:
        slug = row["vendor_slug"]
        vid = f"{venue_id}-{slug}"
        room_key = f"{room_prefix} {row['suffix']}"
        out.append(
            {
                "room_key": room_key,
                "room_desc": row["room_desc"],
                "kiosk_key": row["kiosk_key"],
                "kiosk_desc": row["kiosk_desc"],
                "vendor_id": vid,
                "vendor_name": row["vendor_name"],
                "vendor_account": f"vendor:{vid}",
                "hub_exit": row["hub_exit"],
                "hub_aliases": list(row["hub_aliases"]),
            }
        )
    return tuple(out)


_NANOMEGA_INDUSTRIAL_UNITS = (
    {
        "unit_id": "N1",
        "npc_key": "NanoMegaPlex Mining Unit Foxtrot",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N2",
        "npc_key": "NanoMegaPlex Mining Unit Golf",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N3",
        "npc_key": "NanoMegaPlex Mining Unit Hotel",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N4",
        "npc_key": "NanoMegaPlex Mining Unit India",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N5",
        "npc_key": "NanoMegaPlex Mining Unit Juliet",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
)

_FRONTIER_INDUSTRIAL_UNITS = (
    {
        "unit_id": "F1",
        "npc_key": "Frontier Mining Unit Foxtrot",
        "npc_desc": "Outpost contractor; ore routed under frontier plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "F2",
        "npc_key": "Frontier Mining Unit Golf",
        "npc_desc": "Outpost contractor; ore routed under frontier plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "F3",
        "npc_key": "Frontier Mining Unit Hotel",
        "npc_desc": "Outpost contractor; ore routed under frontier plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "F4",
        "npc_key": "Frontier Mining Unit India",
        "npc_desc": "Outpost contractor; ore routed under frontier plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "F5",
        "npc_key": "Frontier Mining Unit Juliet",
        "npc_desc": "Outpost contractor; ore routed under frontier plant tariffs.",
        "deploy_profile": "mining_starter",
    },
)


VENUES: dict = {
    "nanomega_core": {
        "id": "nanomega_core",
        "label": "NanoMegaPlex",
        "hub_key": "NanoMegaPlex Promenade",
        "arrival_room_key": None,
        "room_prefix": "Aurnom",
        "bank": {
            "reserve_room_key": "Alpha Prime Central Reserve",
            "reserve_room_desc": (
                "A secure treasury chamber of armored terminals, sovereign seals, and reserve ledgers."
            ),
            "bank_object_key": "Alpha Prime",
            "bank_id": "alpha-prime",
        },
        "processing": {
            "plant_room_key": "Aurnom Ore Processing Plant",
            "plant_room_desc": (
                "Heavy industrial equipment lines the floor of this processing bay. "
                "Conveyor systems, smelting units, and cutting bays handle everything "
                "from iron ore to gem-grade kimberlite.  The air smells of flux and heat."
            ),
            "refinery_key": "Ore Processing Unit",
            "refinery_desc": "A multi-stage processing platform handling ore smelting and gem cutting.",
            "hub_exit": "processing plant",
            "hub_aliases": ["processing", "refinery", "plant", "smelt"],
        },
        "shipyard": {
            "showroom_key": "Meridian Civil Shipyard",
            "showroom_desc": (
                "A bright commercial shipyard lined with polished hulls, financing kiosks, "
                "and launch-bay displays."
            ),
            "delivery_key": "Meridian Delivery Hangar",
            "delivery_desc": "A secured hangar where purchased ships are staged for pickup.",
            "vendor_id": "nanomega_core-shipyard-kiosk",
            "vendor_name": "Meridian Civil Shipyard",
            "vendor_account": "vendor:nanomega_core-shipyard-kiosk",
            "hub_exit": "shipyard",
            "hub_aliases": ["yard", "meridian"],
        },
        "shops": _shop_specs_for_venue("nanomega_core", "Aurnom"),
        "realty": {
            "office_key": "NanoMegaPlex Real Estate Office",
            "office_desc": (
                "A clean, well-lit suite branching off the NanoMegaPlex Promenade. "
                "Holographic lot schematics rotate slowly behind a polished reception desk. "
                "Standard and prime parcels rotate on the sovereign exchange, with fresh "
                "survey listings as inventory turns. The NanoMegaPlex Real Estate agent "
                "stands ready to assist."
            ),
            "archive_room_key": "Property Lots Archive",
            "exchange_registry_script_key": "property_lot_exchange_registry",
        },
        "advertising": {
            "room_key": "NanoMegaPlex Advertising Agency",
            "room_desc": (
                "Glass-walled suites off the promenade where licensed brokers place tenancy "
                "and income-stream campaigns on sovereign ad bands. Holo rate cards flicker "
                "above a reception counter staffed by the station advertising agent."
            ),
            "hub_exit": "advertising",
            "hub_aliases": ["ads", "ad agency", "marketing", "agency"],
        },
        "industrial": {
            "staging_room_key": "NanoMegaPlex Industrial Subdeck",
            "staging_room_desc": (
                "Below-deck contractor grid for multiplex build-out: leased pads, "
                "ore hoppers, and dispatch uplinks to the central processing plant."
            ),
            "hub_exit_key": "nanomega industrial",
            "hub_exit_aliases": [
                "plex industrial",
                "nanomega mines",
                "contractor subdeck",
                "industrial subdeck",
            ],
            "pad_room_prefix": "NanoMegaPlex Industrial Pad",
            "pad_desc_template": (
                "NanoMegaPlex lease pad {cell}: contracted extraction feeding "
                "multiplex construction and fab lines."
            ),
            "site_key_template": "NanoMegaPlex Pad {cell} Deposit",
            "deploy_tag": "npc_nanomega_industrial_supply",
            "units": _NANOMEGA_INDUSTRIAL_UNITS,
        },
        "npcs": {
            "realty_key": NANOMEGA_REALTY_CHARACTER_KEY,
            "construction_key": NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
            "advertising_key": NANOMEGA_ADVERTISING_CHARACTER_KEY,
            "promenade_guide_key": PROMENADE_GUIDE_CHARACTER_KEY,
        },
    },
    "frontier_outpost": {
        "id": "frontier_outpost",
        "label": "Frontier",
        "hub_key": "Frontier Promenade",
        "arrival_room_key": "Frontier Transit Shell",
        "room_prefix": "Frontier Aurnom",
        "bank": {
            "reserve_room_key": "Frontier Alpha Prime Reserve",
            "reserve_room_desc": (
                "A compact treasury annex: armored terminals and branch ledgers tied to "
                "the same sovereign economy as coreward Alpha Prime."
            ),
            "bank_object_key": "Alpha Prime Frontier Branch",
            "bank_id": "alpha-prime-frontier",
        },
        "processing": {
            "plant_room_key": "Frontier Ore Processing Plant",
            "plant_room_desc": (
                "A frontier-scale ore bay: scaled conveyors and portable smelters "
                "handle regional feedstock under harsher lighting and thinner margins."
            ),
            "refinery_key": "Frontier Ore Processing Unit",
            "refinery_desc": "Regional processing stack for ore smelting and gem cutting.",
            "hub_exit": "processing plant",
            "hub_aliases": ["processing", "refinery", "plant", "smelt"],
        },
        "shipyard": {
            "showroom_key": "Frontier Meridian Civil Shipyard",
            "showroom_desc": (
                "A frontier shipyard annex: hull mockups, financing kiosks, and "
                "dust-scuffed displays aimed at rim operators."
            ),
            "delivery_key": "Frontier Meridian Delivery Hangar",
            "delivery_desc": "Staging hangar for hulls sold through the frontier yard.",
            "vendor_id": "frontier_outpost-shipyard-kiosk",
            "vendor_name": "Frontier Meridian Civil Shipyard",
            "vendor_account": "vendor:frontier_outpost-shipyard-kiosk",
            "hub_exit": "shipyard",
            "hub_aliases": ["yard", "meridian", "ships"],
        },
        "shops": _shop_specs_for_venue("frontier_outpost", "Frontier Aurnom"),
        "realty": {
            "office_key": "Frontier Real Estate Office",
            "office_desc": (
                "A frontier realty suite off the local promenade: schematics on budget "
                "displays, sovereign listings scoped to the rim exchange."
            ),
            "archive_room_key": "Frontier Property Lots Archive",
            "exchange_registry_script_key": "property_lot_exchange_registry__frontier_outpost",
        },
        "advertising": {
            "room_key": "Frontier Advertising Agency",
            "room_desc": (
                "A smaller ad bureau serving the frontier promenade: rate cards and "
                "tenancy bands tuned for outpost operators."
            ),
            "hub_exit": "advertising",
            "hub_aliases": ["ads", "ad agency", "marketing", "agency"],
        },
        "industrial": {
            "staging_room_key": "Frontier Industrial Subdeck",
            "staging_room_desc": (
                "Rim contractor grid: leased pads and hoppers uplinked to the "
                "frontier processing plant."
            ),
            "hub_exit_key": "frontier industrial",
            "hub_exit_aliases": [
                "outpost industrial",
                "frontier mines",
                "rim industrial",
                "industrial subdeck",
            ],
            "pad_room_prefix": "Frontier Industrial Pad",
            "pad_desc_template": (
                "Frontier lease pad {cell}: contracted extraction feeding outpost fab demand."
            ),
            "site_key_template": "Frontier Pad {cell} Deposit",
            "deploy_tag": "npc_frontier_industrial_supply",
            "units": _FRONTIER_INDUSTRIAL_UNITS,
        },
        "npcs": {
            "realty_key": FRONTIER_REALTY_CHARACTER_KEY,
            "construction_key": FRONTIER_CONSTRUCTION_CHARACTER_KEY,
            "advertising_key": FRONTIER_ADVERTISING_CHARACTER_KEY,
            "promenade_guide_key": FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY,
        },
    },
}


def all_venue_ids() -> list[str]:
    return list(VENUES.keys())


def get_venue(venue_id: str) -> dict:
    return VENUES[venue_id]


def apply_venue_metadata(room, venue_id: str) -> None:
    if not room:
        return
    room.db.venue_id = venue_id
    room.tags.add(venue_id, category=VENUE_TAG_CATEGORY)


def venue_id_for_object(obj) -> str | None:
    """Walk location chain; optional self.db.venue_id."""
    if not obj:
        return None
    cur = obj
    depth = 0
    while cur is not None and depth < 48:
        vid = getattr(cur.db, "venue_id", None)
        if vid:
            return str(vid)
        cur = cur.location
        depth += 1
    return getattr(obj.db, "venue_id", None)
