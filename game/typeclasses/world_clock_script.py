"""
Persists the latest in-character clock snapshot and broadcasts to world engines.
"""

from typeclasses.scripts import Script
from world.world_clock import compute_clock_snapshot
from world import world_events

WORLD_CLOCK_INTERVAL = 60


class WorldClockScript(Script):
    def at_script_creation(self):
        self.key = "world_clock_script"
        self.desc = "In-character clock snapshot for world engines and UI."
        self.persistent = True
        self.interval = WORLD_CLOCK_INTERVAL
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self):
        snap = compute_clock_snapshot()
        self.db.last_snapshot = dict(snap)
        world_events.emit_world_clock_tick(snap)
