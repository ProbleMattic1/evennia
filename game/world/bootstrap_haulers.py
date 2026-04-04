"""
Bootstrap for the autonomous hauler system.

Creates:
- HaulerEngine global script
- RefineryEngine global script
- Ore Receiving Bay storage at the refinery room (autonomous hauler unload + plant intake)
- Processing Plant treasury account in the economy engine

The standalone hauler depot and direct-sale templates have been removed.
Haulers are now bundled inside mining packages (bootstrap_mining_packages.py).
"""

from evennia import create_object, search_object

from world.global_scripts_util import require_global_script

# Vast storage for the global plant's shared receiving bay.
ORE_RECEIVING_BAY_CAPACITY_TONS = 1_000_000.0


def _get_or_create_refinery_receiving_storage(room):
    """Ensure an Ore Receiving Bay MiningStorage exists in the refinery room."""
    from typeclasses.haulers import ORE_RECEIVING_BAY_TAG, ORE_RECEIVING_BAY_TAG_CATEGORY
    from typeclasses.mining import MiningStorage
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining") and obj.key == "Ore Receiving Bay":
            obj.db.capacity_tons = ORE_RECEIVING_BAY_CAPACITY_TONS
            obj.tags.add(ORE_RECEIVING_BAY_TAG, category=ORE_RECEIVING_BAY_TAG_CATEGORY)
            return obj
    storage = create_object(
        MiningStorage,
        key="Ore Receiving Bay",
        location=room,
        home=room,
    )
    storage.db.desc = (
        "A vast designated receiving bay for ore delivered by autonomous haulers. "
        "Sell-mode ore is held here for automated plant processing."
    )
    storage.db.capacity_tons = ORE_RECEIVING_BAY_CAPACITY_TONS
    storage.tags.add(ORE_RECEIVING_BAY_TAG, category=ORE_RECEIVING_BAY_TAG_CATEGORY)
    return storage


def bootstrap_haulers():
    """Ensure HaulerEngine, RefineryEngine, refinery receiving storage, and plant treasury exist. Idempotent."""
    he = require_global_script("hauler_engine")
    print(f"[haulers] HaulerEngine: {he.key}")
    re_eng = require_global_script("refinery_engine")
    print(f"[haulers] RefineryEngine: {re_eng.key}")

    from world.npc_miner_registry import get_npc_miner_registry

    get_npc_miner_registry()
    print("[haulers] NpcMinerRegistryScript ready.")

    from world.venues import all_venue_ids, get_venue

    for venue_id in all_venue_ids():
        plant_key = get_venue(venue_id)["processing"]["plant_room_key"]
        refinery_rooms = search_object(plant_key)
        if refinery_rooms:
            storage = _get_or_create_refinery_receiving_storage(refinery_rooms[0])
            print(
                f"[haulers] [{venue_id}] Refinery receiving storage: '{storage.key}' "
                f"({storage.db.capacity_tons:,.0f}t) ready."
            )
        else:
            print(f"[haulers] WARNING: {plant_key!r} not found; receiving storage skipped.")

    print("[haulers] Bootstrap complete.")
