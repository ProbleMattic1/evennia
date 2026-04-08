"""
District scan cooldown constants and peer listing for the mining scanner.

Peers are adjacent-room mining deposits the operator can buy now (see mining_adjacent_scan).
"""

from __future__ import annotations

from typing import Any

from world.mining_adjacent_scan import list_adjacent_purchasable_mining_peers

DISTRICT_SCAN_COOLDOWN_KEY = "district_scan"
DISTRICT_SCAN_COOLDOWN_SEC = 30.0


def list_district_peers(character, site) -> list[dict[str, Any]]:
    """
    Exit-adjacent mining sites in the same venue as ``site`` that ``character`` can
    purchase immediately (NPC primary deed or active property listing, with balance).
    """
    return list_adjacent_purchasable_mining_peers(character, site)
