"""
Explicit submit of assigned plant silo ore into the Refinery miner_ore_queue.

Use from NPC scripts, web, or staff tools when a character at the plant should
queue ore without using the feedrefinery command.
"""

from typeclasses.refining import Refinery


def submit_owner_plant_silo_at_refinery(owner, refinery):
    """
    Merge ``owner``'s assigned plant silo in ``refinery.location`` into that
    refinery's miner_ore_queue. Use when the owner is not necessarily in the
    plant room (e.g. NPC at a mine). Returns {resource_key: tons_moved} or {}.
    """
    if not owner or not refinery:
        return {}
    if not refinery.is_typeclass(Refinery, exact=False):
        return {}
    return refinery.transfer_owner_plant_silo_to_miner_queue(owner) or {}


def submit_character_plant_silo_to_plant_refinery(character):
    """
    If ``character`` is in a room with a Refinery, merge their plant silo into
    that refinery's miner_ore_queue. Returns {resource_key: tons_moved} or {}.
    """
    room = character.location
    if not room:
        return {}
    for obj in room.contents:
        if obj.is_typeclass(Refinery, exact=False):
            return submit_owner_plant_silo_at_refinery(character, obj)
    return {}
