"""
Low-rate room messages; no global alert queue.
"""

import random

from typeclasses.scripts import Script


class RoomAmbienceScript(Script):
    def at_script_creation(self):
        self.key = "room_ambience_promenade"
        self.desc = "Occasional promenade crowd chatter."
        self.persistent = True
        self.interval = 120
        self.repeats = 0

    def at_repeat(self):
        room = self.obj
        if not room:
            return
        lines = getattr(room.db, "ambience_lines", None) or [
            "A maintenance skiff hums overhead.",
            "Someone argues about berth fees near the transit map.",
        ]
        line = random.choice(lines)
        room.msg_contents(f"|w{line}|n", exclude=None)
