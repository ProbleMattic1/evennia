"""
Resolve hubs, plants, banks, and treasury accounts from venue_id or a world object.
"""

from world.bootstrap_hub import get_hub_room as get_core_hub_room
from world.venues import VENUES, get_venue, venue_id_for_object


def hub_room_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    spec = get_venue(venue_id)
    found = search_object(spec["hub_key"])
    return found[0] if found else None


def hub_for_object(obj):
    """Promenade/hub for the venue the object is in (falls back to core hub)."""
    vid = venue_id_for_object(obj)
    if not vid:
        return get_core_hub_room()
    room = hub_room_for_venue(vid)
    return room or get_core_hub_room()


def processing_plant_room_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    spec = get_venue(venue_id)
    key = spec["processing"]["plant_room_key"]
    found = search_object(key)
    return found[0] if found else None


def processing_plant_room_for_object(obj):
    vid = venue_id_for_object(obj) or "nanomega_core"
    return processing_plant_room_for_venue(vid)


def refinery_room_for_venue(venue_id: str):
    """Resolve the refinery chamber from ``VENUES[venue_id]["processing"]["refinery_room_key"]`` only."""
    from evennia.utils.search import search_object

    spec = get_venue(venue_id)
    proc = spec.get("processing") or {}
    key = proc.get("refinery_room_key")
    if not key or not str(key).strip():
        return None
    key = str(key).strip()
    found = search_object(key)
    return found[0] if found else None


def refinery_room_for_object(obj):
    vid = venue_id_for_object(obj) or "nanomega_core"
    return refinery_room_for_venue(vid)


# Canonical venue for all NPC-owned autonomous haulers (mining / flora / fauna contractor supply).
NPC_AUTONOMOUS_SUPPLY_VENUE_ID = "nanomega_core"


def processing_plant_room_for_npc_autonomous_supply():
    """Processing plant room where NPC contractor haulers must unload raw (Ore Receiving Bay + treasury)."""
    return processing_plant_room_for_venue(NPC_AUTONOMOUS_SUPPLY_VENUE_ID)


def treasury_bank_id_for_venue(venue_id: str) -> str:
    return str(get_venue(venue_id)["bank"]["bank_id"])


def treasury_bank_id_for_object(obj) -> str:
    vid = venue_id_for_object(obj)
    if not vid:
        return treasury_bank_id_for_venue("nanomega_core")
    if vid in VENUES:
        return treasury_bank_id_for_venue(vid)
    return treasury_bank_id_for_venue("nanomega_core")


def treasury_bank_id_for_lot(lot) -> str:
    vid = getattr(lot.db, "venue_id", None) if lot else None
    if vid and vid in VENUES:
        return treasury_bank_id_for_venue(vid)
    loc = getattr(lot, "location", None) if lot else None
    if loc:
        v2 = getattr(loc.db, "venue_id", None)
        if v2 and v2 in VENUES:
            return treasury_bank_id_for_venue(v2)
    return treasury_bank_id_for_venue("nanomega_core")


def realty_broker_key_for_venue(venue_id: str) -> str:
    return str(get_venue(venue_id)["npcs"]["realty_key"])


def get_realty_broker_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    key = realty_broker_key_for_venue(venue_id)
    found = search_object(key)
    return found[0] if found else None


def construction_builder_key_for_venue(venue_id: str) -> str:
    return str(get_venue(venue_id)["npcs"]["construction_key"])


def get_construction_builder_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    key = construction_builder_key_for_venue(venue_id)
    found = search_object(key)
    return found[0] if found else None


def advertising_agent_key_for_venue(venue_id: str) -> str:
    return str(get_venue(venue_id)["npcs"]["advertising_key"])


def get_advertising_agent_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    key = advertising_agent_key_for_venue(venue_id)
    found = search_object(key)
    return found[0] if found else None


def infer_venue_id_from_holding(holding) -> str:
    """Venue for property economy flows from the titled lot."""
    lot = getattr(holding.db, "lot_ref", None) if holding else None
    if not lot:
        return "nanomega_core"
    from typeclasses.property_lot_registry import infer_lot_venue_id

    return infer_lot_venue_id(lot)


def bank_reserve_room_for_venue(venue_id: str):
    from evennia.utils.search import search_object

    spec = get_venue(venue_id)
    key = spec["bank"]["reserve_room_key"]
    found = search_object(key)
    return found[0] if found else None
