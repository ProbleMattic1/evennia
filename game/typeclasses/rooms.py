"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent

_ENV_TICK_INTERVAL = 120
_ENV_TICK_ID = "room_ambient_env"
_NDB_ENV_TICKER_ACTIVE = "_ambient_env_ticker_active"


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
        self._sync_environment_ticker()
        try:
            moved_obj.missions.sync_global_seeds()
            moved_obj.missions.sync_room(self)
            moved_obj.quests.sync_room(self)
        except Exception:
            pass

    def at_object_leave(self, moved_obj, target_location, move_type="move", **kwargs):
        super().at_object_leave(moved_obj, target_location, move_type=move_type, **kwargs)
        if moved_obj and moved_obj.is_typeclass("typeclasses.characters.Character", exact=False):
            self._sync_environment_ticker(leaving=moved_obj)

    def _room_has_puppeted_character(self, ignore=None) -> bool:
        """
        True if this room has at least one Character with an active session.

        `ignore` is used from at_object_leave: the leaver is still in `.contents`
        until after move_to updates location, so they must be excluded when
        deciding whether anyone remains after the leave.
        """
        for obj in self.contents:
            if ignore is not None and obj is ignore:
                continue
            if obj.is_typeclass("typeclasses.characters.Character", exact=False):
                if obj.sessions.count():
                    return True
        return False

    def _sync_environment_ticker(self, leaving=None):
        """
        Register the slow environment tick while puppeted characters are present;
        remove it when none remain. Uses ndb so we never remove a subscription
        we did not record (e.g. NPC-only churn).
        """
        from evennia.scripts.tickerhandler import TICKER_HANDLER

        has_puppeted = self._room_has_puppeted_character(ignore=leaving)
        subscribed = bool(getattr(self.ndb, _NDB_ENV_TICKER_ACTIVE, False))

        if has_puppeted and not subscribed:
            TICKER_HANDLER.add(
                _ENV_TICK_INTERVAL,
                self.at_environment_tick,
                idstring=_ENV_TICK_ID,
                persistent=True,
            )
            setattr(self.ndb, _NDB_ENV_TICKER_ACTIVE, True)
        elif not has_puppeted and subscribed:
            TICKER_HANDLER.remove(
                _ENV_TICK_INTERVAL,
                self.at_environment_tick,
                idstring=_ENV_TICK_ID,
                persistent=True,
            )
            setattr(self.ndb, _NDB_ENV_TICKER_ACTIVE, False)

    def at_environment_tick(self, *args, **kwargs):
        """Slow tick while occupants present; hooks challenges / future ambience."""
        from world.challenges.challenge_signals import emit

        for obj in list(self.contents):
            if not obj.is_typeclass("typeclasses.characters.Character", exact=False):
                continue
            if not obj.sessions.count():
                continue
            emit(
                obj,
                "world_environment_tick",
                {"room_id": self.id, "venue_id": getattr(self.db, "venue_id", None)},
            )
