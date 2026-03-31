"""Create CrimeWorldEngine script if missing (idempotent)."""

from evennia import create_script, search_script


def bootstrap_crime_world():
    if search_script("crime_world_engine"):
        return
    create_script("typeclasses.crime_world_engine.CrimeWorldEngine")
    print("[crime] Created CrimeWorldEngine.")
