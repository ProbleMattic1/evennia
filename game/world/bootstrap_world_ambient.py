"""Create AmbientWorldEngine script if missing (idempotent)."""

from evennia import create_script, search_script

from typeclasses.ambient_world_engine import AmbientWorldEngine


def bootstrap_world_ambient():
    if search_script("ambient_world_engine"):
        return
    create_script(AmbientWorldEngine)
    print("[world-ambient] Created AmbientWorldEngine.")
