"""
Player autonomous hauls → local raw reserve (Personal Storage read model).

Non-NPC characters default to unloading into tagged local raw storage at the
processing plant for their haul route instead of selling into the Ore Receiving Bay.
Does not change mining wear/breakdown (no mining_owner_uses_npc_production).
"""

from __future__ import annotations


def player_autonomous_haul_uses_local_raw_reserve(character) -> bool:
    """
    Return True and set db.haul_delivers_to_local_raw_storage when character
    should use local delivery. No-op for missing or NPC characters.
    """
    if not character or getattr(character.db, "is_npc", False):
        return False
    character.db.haul_delivers_to_local_raw_storage = True
    return True


def prime_local_raw_storage_for_plant(character, plant_room):
    """
    Idempotent: ensure local raw MiningStorage exists in plant_room and link
    character.db.local_raw_storage. Skips storage moves when the character
    already has a different haul_destination_room (e.g. Marcus annex).

    Call with the same plant room used as hauler.db.hauler_refinery_room for this deploy.
    """
    if not player_autonomous_haul_uses_local_raw_reserve(character) or not plant_room:
        return

    from typeclasses.haulers import ensure_local_raw_storage, resolve_room

    hdr = getattr(character.db, "haul_destination_room", None)
    if hdr:
        existing = resolve_room(hdr)
        if existing and existing != plant_room:
            return

    st = ensure_local_raw_storage(plant_room, character)
    character.db.local_raw_storage = st
    if not getattr(character.db, "haul_destination_room", None):
        character.db.haul_destination_room = plant_room


def bootstrap_player_haul_delivers_to_local_raw_storage():
    """Cold-start backfill: set local-haul flag on all non-NPC characters."""
    from typeclasses.characters import Character

    for ch in Character.objects.all():
        if getattr(ch.db, "is_npc", False):
            continue
        ch.db.haul_delivers_to_local_raw_storage = True
