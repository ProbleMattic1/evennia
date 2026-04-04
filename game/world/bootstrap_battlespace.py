"""Verify BattlespaceWorldEngine global script."""

from world.global_scripts_util import require_global_script


def bootstrap_battlespace_world():
    require_global_script("battlespace_world_engine")
    print("[battlespace] BattlespaceWorldEngine ok.")
