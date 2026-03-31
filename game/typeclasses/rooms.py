"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(
            moved_obj,
            source_location,
            move_type=move_type,
            **kwargs,
        )
        if not moved_obj or not moved_obj.is_typeclass("typeclasses.characters.Character", exact=False):
            return
        try:
            moved_obj.missions.sync_global_seeds()
            moved_obj.missions.sync_room(self)
            moved_obj.quests.sync_room(self)
        except Exception:
            pass
