"""
Registry of property holding object ids eligible for the operations tick.

Mutate only from develop/deploy/transfer/teardown code paths — not from the tick loop.
"""

from evennia import search_script
from evennia.scripts.scripts import DefaultScript

REGISTRY_KEY = "property_operation_registry"


class PropertyOperationRegistry(DefaultScript):
    def at_script_creation(self):
        self.key = REGISTRY_KEY
        self.desc = "Active property holding ids for scheduled operations."
        self.interval = 0
        self.persistent = True
        if self.db.active_holding_ids is None:
            self.db.active_holding_ids = []


def get_property_operation_registry(create_missing=False):
    from evennia import GLOBAL_SCRIPTS

    script = GLOBAL_SCRIPTS.get(REGISTRY_KEY)
    if script:
        return script
    found = search_script(REGISTRY_KEY)
    if found:
        return found[0]
    if create_missing:
        raise RuntimeError(
            "property_operation_registry global script missing. "
            "Add it to server.conf.settings.GLOBAL_SCRIPTS."
        )
    return None


def register_property_holding(holding):
    script = get_property_operation_registry(create_missing=True)
    ids = list(script.db.active_holding_ids or [])
    hid = holding.id
    if hid not in ids:
        ids.append(hid)
        script.db.active_holding_ids = ids


def unregister_property_holding(holding):
    script = get_property_operation_registry(create_missing=False)
    if not script:
        return
    hid = holding.id
    script.db.active_holding_ids = [i for i in (script.db.active_holding_ids or []) if i != hid]
