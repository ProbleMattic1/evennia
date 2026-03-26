"""
Parcel mission NPCs — player commands; require the NPC in the caller's room.
Interaction keys must match mission_templates.json interaction objectives.
"""

from commands.command import Command
from typeclasses.characters import (
    GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
    PARCEL_COMMUTER_CHARACTER_KEY,
)
from world.bootstrap_hub import HUB_ROOM_KEY


class CmdAskParcelCommuter(Command):
    """
    Ask Mira Okonkwo about the misrouted parcel.

    Usage:
      askparcelcommuter
    """

    key = "askparcelcommuter"
    aliases = ["askparcel", "ask mira", "parcel commuter"]
    locks = "cmd:all()"
    help_category = "NPC"

    def func(self):
        caller = self.caller
        loc = caller.location
        if not loc:
            caller.msg("You are not anywhere public enough to ask.")
            return
        if str(loc.key) != HUB_ROOM_KEY:
            caller.msg("Mira is only on the main promenade when she is looking for help.")
            return
        found = [o for o in loc.contents if o.key == PARCEL_COMMUTER_CHARACTER_KEY]
        if not found:
            caller.msg("Mira is not here.")
            return
        caller.msg(
            f'{PARCEL_COMMUTER_CHARACTER_KEY} lowers her voice. "The trace dead-ends at '
            f'General Supply — kiosk shelf, not the clinic. Whoever coded the pouch '
            f'used a medical routing glyph. If you go, do not flash the seal around."'
        )
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction("parcel:commuter")
        if caller.location:
            caller.missions.sync_room(caller.location)


class CmdAskParcelClerk(Command):
    """
    Ask the supply clerk about the parcel routing entry.

    Usage:
      askparcelclerk
    """

    key = "askparcelclerk"
    aliases = ["ask clerk parcel", "supply parcel", "parcel clerk"]
    locks = "cmd:all()"
    help_category = "NPC"

    def func(self):
        caller = self.caller
        loc = caller.location
        if not loc:
            caller.msg("You are not in a shop.")
            return
        found = [o for o in loc.contents if o.key == GENERAL_SUPPLY_CLERK_CHARACTER_KEY]
        if not found:
            caller.msg("The supply clerk is not on duty here.")
            return
        caller.msg(
            f'{GENERAL_SUPPLY_CLERK_CHARACTER_KEY} squints at a handheld scanner. "Last ping '
            f'was holding bay gamma — seal still intact. Contents flagged confidential '
            f'upstream; we are not supposed to open it. You did not hear that from me."'
        )
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction("parcel:supply_clerk")
        if caller.location:
            caller.missions.sync_room(caller.location)
