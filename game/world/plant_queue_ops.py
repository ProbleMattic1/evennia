"""
Explicit submit of assigned plant silo ore into the Refinery miner_ore_queue.

Use from NPC scripts, web, or staff tools when a character at the plant should
queue ore without using the feedrefinery command.
"""

from typeclasses.refining import Refinery
from world.venue_resolve import processing_plant_room_for_object


def submit_owner_plant_silo_at_refinery(owner, refinery, plant_room=None):
    """
    Merge ``owner``'s assigned plant silo (on the ore-bay floor) into that
    refinery's miner_ore_queue. Pass ``plant_room`` when the refinery object
    lives in a separate refinery chamber.
    """
    if not owner or not refinery:
        return {}
    if not refinery.is_typeclass(Refinery, exact=False):
        return {}
    pr = plant_room or processing_plant_room_for_object(owner)
    return refinery.transfer_owner_plant_silo_to_miner_queue(owner, plant_room=pr) or {}


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
