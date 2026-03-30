"""
Ensure the global FaunaEngine script exists. Idempotent.

Runs from at_server_cold_start after flora engine bootstrap so fauna ticks are available
when fauna sites and haulers are deployed.
"""

from evennia import create_script, search_script


def bootstrap_fauna_engine():
    if search_script("fauna_engine"):
        print("[fauna] FaunaEngine already exists.")
    else:
        create_script("typeclasses.fauna.FaunaEngine")
        print("[fauna] Created FaunaEngine.")
    print("[fauna] Bootstrap complete.")
