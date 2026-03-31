"""Create BattlespaceWorldEngine script if missing (idempotent)."""

from evennia import create_script, search_script


def bootstrap_battlespace_world():
    if search_script("battlespace_world_engine"):
        return
    create_script("typeclasses.battlespace_world_engine.BattlespaceWorldEngine")
    print("[battlespace] Created BattlespaceWorldEngine.")
