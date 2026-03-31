"""
Parcel mission NPCs — player commands; require the NPC in the caller's room.
Interaction keys must match mission_templates.json interaction objectives.
"""

from commands.command import Command
from world.web_interactions import (
    InteractionError,
    handle_parcel_clerk,
    handle_parcel_commuter,
)


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
        try:
            dialogue, interaction_key = handle_parcel_commuter(caller)
        except InteractionError as exc:
            caller.msg(str(exc))
            return
        caller.msg(dialogue)
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction(interaction_key)
        caller.quests.on_interaction(interaction_key)
        if caller.location:
            caller.missions.sync_room(caller.location)
            caller.quests.sync_room(caller.location)


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
        try:
            dialogue, interaction_key = handle_parcel_clerk(caller)
        except InteractionError as exc:
            caller.msg(str(exc))
            return
        caller.msg(dialogue)
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction(interaction_key)
        caller.quests.on_interaction(interaction_key)
        if caller.location:
            caller.missions.sync_room(caller.location)
            caller.quests.sync_room(caller.location)
