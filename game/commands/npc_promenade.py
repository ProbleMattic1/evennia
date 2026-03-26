"""
Station Guide Kiran — player-facing ask command and NPC cmdset (GM puppet).
"""

from evennia import CmdSet

from commands.command import Command
from typeclasses.characters import PROMENADE_GUIDE_CHARACTER_KEY


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
        loc = caller.location
        if not loc:
            caller.msg("You are not in a place where a guide could help.")
            return
        guides = [o for o in loc.contents if o.key == PROMENADE_GUIDE_CHARACTER_KEY]
        if not guides:
            caller.msg("The station guide is not here.")
            return
        topic = (self.args or "").strip().lower()
        replies = {
            "property": (
                "Try the Sovereign property exchange — the broker in the realty office lives for paperwork."
            ),
            "mining": (
                "Ashfall Basin keeps the independents busy. Mining Outfitters sells the boring but vital bits."
            ),
            "default": (
                "Kiran taps a holo-slate. 'Transit, permits, or profit — pick one and I'll narrow it down.'"
            ),
        }
        msg = replies.get(topic, replies["default"])
        interaction_key = "askguide" if not topic else f"askguide:{topic}"
        caller.missions.sync_global_seeds()
        caller.missions.sync_interaction(interaction_key)
        caller.msg(f"{PROMENADE_GUIDE_CHARACTER_KEY} says, \"{msg}\"")


class NPCPromenadeCmdSet(CmdSet):
    key = "NPCPromenade"
    priority = 1

    def at_cmdset_creation(self):
        self.add(CmdAskGuide())
