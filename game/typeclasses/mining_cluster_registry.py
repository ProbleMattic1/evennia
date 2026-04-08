"""
Persistent registry for mining camp / base cluster records (audit and form-base validation).
"""

from __future__ import annotations

from evennia import GLOBAL_SCRIPTS, search_script

from typeclasses.scripts import Script

REGISTRY_KEY = "mining_cluster_registry"


class MiningClusterRegistry(Script):
    """db.clusters: dict[str, dict] — camp:uuid / base:uuid metadata."""

    def at_script_creation(self):
        self.key = REGISTRY_KEY
        self.desc = "Mining camp and base cluster records."
        self.persistent = True
        if self.db.clusters is None:
            self.db.clusters = {}


def get_mining_cluster_registry():
    script = GLOBAL_SCRIPTS.get(REGISTRY_KEY)
    if script:
        return script
    hits = search_script(REGISTRY_KEY)
    if hits:
        return hits[0]
    raise RuntimeError(
        "mining_cluster_registry missing from GLOBAL_SCRIPTS (server.conf.settings)."
    )
