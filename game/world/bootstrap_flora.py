"""
Ensure the global FloraEngine script exists. Idempotent.

Runs from at_server_cold_start after mining/hauler bootstrap so flora ticks are available
when flora sites and haulers are deployed.
"""

from world.global_scripts_util import require_global_script


def bootstrap_flora_engine():
    fe = require_global_script("flora_engine")
    print(f"[flora] FloraEngine: {fe.key}")
    print("[flora] Bootstrap complete.")
