"""
Shared HTTP read model for the processing plant (raw mass storage + pricing knobs + hauler modes).

Single place to build the ``processing`` block and ``/ui/processing`` ore snapshot so
control-surface and the dedicated processing endpoint stay in sync.

Intentionally excludes refinery input/output/queue/refined-owner fields — those belong
to a separate refining read model if the game exposes them again.
"""

from __future__ import annotations

from typing import Any


def build_processing_plant_payload(
    room,
    *,
    char_for_haulers=None,
    venue_id: str | None = None,
) -> dict[str, Any]:
    """
    Args:
        room: Processing plant room (resolved ``Object``).
        char_for_haulers: Optional character; when set, serializes autonomous hauler delivery modes.
        venue_id: When set, included as ``venueId`` for clients that key off venue.

    Returns:
        Dict with plantName, oreReceivingBay, raw mass storage meters, fee rates, myHaulers.
    """
    from typeclasses.haulers import plant_aggregated_raw_storage_meters
    from typeclasses.mining import COMMODITY_ASK_OVER_BID
    from typeclasses.refining import PROCESSING_FEE_RATE, RAW_SALE_FEE_RATE

    from web.ui.ore_receiving_bay_serialize import serialize_plant_intake_snapshot_rows

    raw_used, raw_cap = plant_aggregated_raw_storage_meters(room)

    my_haulers = None
    if char_for_haulers:
        haulers = []
        for entry in (char_for_haulers.db.owned_vehicles or []):
            h = entry if hasattr(entry, "key") else None
            if not h:
                continue
            if (
                h.tags.has("autonomous_hauler", category="mining")
                or h.tags.has("autonomous_hauler", category="flora")
                or h.tags.has("autonomous_hauler", category="fauna")
            ):
                haulers.append(
                    {
                        "id": h.id,
                        "key": h.key,
                        "deliveryMode": (
                            "local_raw_reserve"
                            if getattr(char_for_haulers.db, "haul_delivers_to_local_raw_storage", False)
                            else "ore_receiving_bay"
                        ),
                    }
                )
        my_haulers = haulers or None

    out: dict[str, Any] = {
        "plantName": room.key,
        "oreReceivingBay": serialize_plant_intake_snapshot_rows(room),
        "rawStorageUsed": raw_used,
        "rawStorageCapacity": raw_cap,
        "processingFeeRate": PROCESSING_FEE_RATE,
        "rawSaleFeeRate": RAW_SALE_FEE_RATE,
        "rawAskPremiumRate": float(COMMODITY_ASK_OVER_BID) - 1.0,
        "myHaulers": my_haulers,
    }
    if venue_id is not None:
        out["venueId"] = venue_id
    return out
