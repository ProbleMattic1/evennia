"""
Station Guide Kiran — player-facing ask command and NPC cmdset (GM puppet).
"""

from evennia import CmdSet

from commands.command import Command
from world.web_interactions import InteractionError, handle_askguide


class CmdAskGuide(Command):
    """
    Ask the station guide a short question.

    Usage:
      askguide <topic>
      askguide
    """

    key = "askguide"
    aliases = ["ask guide", "guide"]
    locks = "cmd:all()"
    help_category = "NPC"

    def func(self):
        caller = self.caller
        topic = (self.args or "").strip().lower()
        payload = {"topic": topic} if topic else None
        try:
            dialogue, interaction_key = handle_askguide(caller, payload)
        except InteractionError as exc:
            caller.msg(str(exc))
            return
        caller.msg(dialogue)
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction(interaction_key)
        caller.quests.on_interaction(interaction_key)


class NPCPromenadeCmdSet(CmdSet):
    key = "NPCPromenade"
    priority = 1

    def at_cmdset_creation(self):
        self.add(CmdAskGuide())
