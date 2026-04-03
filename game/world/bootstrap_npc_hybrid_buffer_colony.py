"""
Bootstrap NPC-owned Hybrid Buffer Colony — split local raw (default 50%) then plant bay + payout.

Thin wrapper around ``bootstrap_split_buffer_colony`` with ``HYBRID_SPLIT_BUFFER_BOOTSTRAP``.
"""

from world.bootstrap_npc_split_buffer_colony import (
    apply_split_buffer_colony_haul_attrs,
    bootstrap_split_buffer_colony,
    sync_split_buffer_hauler_destinations,
)
from world.hybrid_colony_constants import HYBRID_SPLIT_BUFFER_BOOTSTRAP


def apply_hybrid_buffer_colony_haul_attrs(owner) -> bool:
    """Set split-haul attributes; 50% local cap via unset ``haul_local_plant_fill_fraction``."""
    return apply_split_buffer_colony_haul_attrs(owner, None)


sync_hybrid_buffer_hauler_destinations = sync_split_buffer_hauler_destinations


def bootstrap_npc_hybrid_buffer_colony():
    bootstrap_split_buffer_colony(HYBRID_SPLIT_BUFFER_BOOTSTRAP)
