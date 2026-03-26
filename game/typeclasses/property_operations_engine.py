"""
Global interval script: runs scheduled property operations (bounded batch per tick).
"""

from datetime import UTC

from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.time import utc_now

from typeclasses.property_operation_registry import get_property_operation_registry
from typeclasses.scripts import Script

ENGINE_INTERVAL = 1800
MAX_HOLDINGS_PER_TICK = 200


class PropertyOperationsEngine(Script):
    def at_script_creation(self):
        self.key = "property_operations_engine"
        self.desc = "Scheduled property operations (rent, production, upkeep)."
        self.persistent = True
        self.interval = ENGINE_INTERVAL
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self):
        reg = get_property_operation_registry(create_missing=False)
        if not reg:
            return
        ids = list(reg.db.active_holding_ids or [])
        if not ids:
            return
        ids = ids[:MAX_HOLDINGS_PER_TICK]
        now = utc_now().astimezone(UTC)
        objs = ObjectDB.objects.filter(id__in=ids)
        by_id = {o.id: o for o in objs}
        processed = 0
        for pid in ids:
            holding = by_id.get(pid)
            if not holding:
                continue
            if not holding.tags.has("property_holding", category="realty"):
                continue
            msg = holding.tick_operation(now)
            if msg:
                processed += 1
                owner = holding.db.title_owner
                if owner and owner.sessions.count():
                    owner.msg(f"|w[Property]|n {msg}")
        if processed:
            logger.log_info(f"[property_ops_engine] processed={processed}")
