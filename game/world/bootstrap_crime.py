"""Verify CrimeWorldEngine global script."""

from world.global_scripts_util import require_global_script


def bootstrap_crime_world():
    require_global_script("crime_world_engine")
    print("[crime] CrimeWorldEngine ok.")
