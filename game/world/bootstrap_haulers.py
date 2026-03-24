"""
Bootstrap for the autonomous hauler system.

Creates:
- HaulerEngine global script
- RefineryEngine global script
- Ore Receiving Bay storage at the refinery room (for sell-mode hauler drop-offs)
- Processing Plant treasury account in the economy engine

The standalone hauler depot and direct-sale templates have been removed.
Haulers are now bundled inside mining packages (bootstrap_mining_packages.py).
"""

from evennia import create_script, search_object, search_script

# Vast storage for the global plant's shared receiving bay.
ORE_RECEIVING_BAY_CAPACITY_TONS = 50_000.0


def _get_or_create_refinery_receiving_storage(room):
    """Ensure an Ore Receiving Bay MiningStorage exists in the refinery room."""
    from typeclasses.mining import MiningStorage
    from evennia import create_object

    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining") and obj.key == "Ore Receiving Bay":
            obj.db.capacity_tons = ORE_RECEIVING_BAY_CAPACITY_TONS
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
    return storage


def bootstrap_haulers():
    """Ensure HaulerEngine, RefineryEngine, refinery receiving storage, and plant treasury exist. Idempotent."""
    # HaulerEngine
    if search_script("hauler_engine"):
        print("[haulers] HaulerEngine already exists.")
    else:
        create_script("typeclasses.haulers.HaulerEngine")
        print("[haulers] Created HaulerEngine.")

    # RefineryEngine
    if search_script("refinery_engine"):
        print("[haulers] RefineryEngine already exists.")
    else:
        create_script("typeclasses.refining.RefineryEngine")
        print("[haulers] Created RefineryEngine.")

    # Ore Receiving Bay at the processing plant
    refinery_rooms = search_object("Aurnom Ore Processing Plant")
    if refinery_rooms:
        storage = _get_or_create_refinery_receiving_storage(refinery_rooms[0])
        print(f"[haulers] Refinery receiving storage: '{storage.key}' ({storage.db.capacity_tons:,.0f}t) ready.")
    else:
        print("[haulers] WARNING: 'Aurnom Ore Processing Plant' room not found; receiving storage skipped.")

    # Plant treasury account — collects processing fees from miners
    from typeclasses.economy import get_economy
    econ = get_economy(create_missing=True)
    plant_acct = "vendor:processing-plant"
    econ.ensure_account(plant_acct, opening_balance=0)
    print(f"[haulers] Plant treasury account '{plant_acct}' ready.")

    print("[haulers] Bootstrap complete.")
