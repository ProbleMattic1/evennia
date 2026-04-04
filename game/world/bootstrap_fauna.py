"""
Ensure the global FaunaEngine script exists. Idempotent.

Runs from at_server_cold_start after flora engine bootstrap so fauna ticks are available
when fauna sites and haulers are deployed.
"""

from world.global_scripts_util import require_global_script


def bootstrap_fauna_engine():
    ae = require_global_script("fauna_engine")
    print(f"[fauna] FaunaEngine: {ae.key}")
    print("[fauna] Bootstrap complete.")
