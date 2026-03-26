"""
Hourly batch: roll property events from staff/security quality (deep RPG hook).
"""

from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.time import to_iso, utc_now

from typeclasses.property_operation_registry import get_property_operation_registry
from typeclasses.scripts import Script

MAX_EVENTS_PER_TICK = 100


class PropertyEventsEngine(Script):
    def at_script_creation(self):
        self.key = "property_events_engine"
        self.desc = "Property holding event rolls (staff/security scaled)."
        self.persistent = True
        self.interval = 3600
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self):
        reg = get_property_operation_registry(create_missing=False)
        if not reg:
            return
        ids = list(reg.db.active_holding_ids or [])[:MAX_EVENTS_PER_TICK]
        now = utc_now()
        for obj in ObjectDB.objects.filter(id__in=ids):
            if not obj.tags.has("property_holding", category="realty"):
                continue
            self._roll_and_enqueue(obj, now)

    def _roll_and_enqueue(self, holding, now):
        q = list(holding.db.event_queue or [])
        staff = (holding.db.staff or {}).get("roles", {})
        sec = staff.get("security", {})
        quality = int(sec.get("quality") or 0)
        roll = (holding.id + now.hour * 97 + now.day * 13) % 10000
        threshold = int(500 / (1 + quality))
        if roll < threshold:
            q.append(
                {
                    "id": f"evt_{holding.id}_{int(now.timestamp())}",
                    "severity": "info",
                    "due_at_iso": to_iso(now),
                    "resolved": False,
                }
            )
        holding.db.event_queue = q
        logger.log_info(f"[property_events] tick {holding.key}")
