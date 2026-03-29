"""
Ensure the global FloraEngine script exists. Idempotent.

Runs from at_server_cold_start after mining/hauler bootstrap so flora ticks are available
when flora sites and haulers are deployed.
"""

from evennia import create_script, search_script


def bootstrap_flora_engine():
    if search_script("flora_engine"):
        print("[flora] FloraEngine already exists.")
    else:
        create_script("typeclasses.flora.FloraEngine")
        print("[flora] Created FloraEngine.")
    print("[flora] Bootstrap complete.")
