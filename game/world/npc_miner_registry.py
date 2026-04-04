"""
Registry of character ids that receive automated Processing Plant payouts
(collect_miner_output economics) without a player command.

O(1) membership via dict on a persistent script. Bootstrap industrial NPCs
call register_npc_miner_character_id after the character is ensured.
"""

from evennia import search_script

from typeclasses.scripts import Script

REGISTRY_SCRIPT_KEY = "npc_miner_registry"


class NpcMinerRegistryScript(Script):
    """Persistent db.registered_miner_ids: { str(character_id): True }"""

    def at_script_creation(self):
        self.key = REGISTRY_SCRIPT_KEY
        self.desc = "Character ids eligible for automated plant refining settlement."
        self.persistent = True
        if self.db.registered_miner_ids is None:
            self.db.registered_miner_ids = {}


def get_npc_miner_registry():
    from evennia import GLOBAL_SCRIPTS

    script = GLOBAL_SCRIPTS.get(REGISTRY_SCRIPT_KEY)
    if script:
        return script
    hits = search_script(REGISTRY_SCRIPT_KEY)
    if hits:
        return hits[0]
    raise RuntimeError(
        "npc_miner_registry global script missing. Add it to server.conf.settings.GLOBAL_SCRIPTS."
    )


def register_npc_miner_character_id(character_id: int) -> None:
    reg = get_npc_miner_registry()
    m = dict(reg.db.registered_miner_ids or {})
    m[str(int(character_id))] = True
    reg.db.registered_miner_ids = m


def unregister_npc_miner_character_id(character_id: int) -> None:
    reg = get_npc_miner_registry()
    m = dict(reg.db.registered_miner_ids or {})
    m.pop(str(int(character_id)), None)
    reg.db.registered_miner_ids = m


def is_registered_npc_miner_owner_id(owner_id_str: str) -> bool:
    if not owner_id_str:
        return False
    reg = get_npc_miner_registry()
    return owner_id_str in (reg.db.registered_miner_ids or {})
