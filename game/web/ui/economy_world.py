from collections.abc import Mapping, Sequence

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from evennia import search_script

from world.time import (
    MINING_DELIVERY_PERIOD,
    current_mining_delivery_slot_start_iso,
    next_mining_delivery_boundary_iso,
    to_iso,
    utc_now,
)


def _to_json_plain(value):
    """
    Recursively convert Evennia db-backed dict/list wrappers (_SaverDict, _SaverList, …)
    and other Mapping/Sequence values into plain dict/list/primitives for JsonResponse.
    """
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {str(k): _to_json_plain(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_to_json_plain(v) for v in value]
    raise TypeError(f"economy-world JSON: unsupported type {type(value).__name__}")


@require_GET
def economy_world_state(request):
    from world.market_snapshot import serialize_resource_market

    found = search_script("economy_world_telemetry")
    script = found[0] if found else None
    if script and script.db.snapshot:
        world = _to_json_plain(script.db.snapshot)
    else:
        world = {}

    implied = (world.get("mining") or {}).get("impliedCycleValueCr") or 0
    slot_start = current_mining_delivery_slot_start_iso()
    slot_end = next_mining_delivery_boundary_iso()

    meters = [
        {
            "id": "world_mining_slot_value_cr",
            "kind": "linear_accruing",
            "unit": "cr",
            "label": "Projected global mining value (this delivery slot)",
            "startAtIso": slot_start,
            "endAtIso": slot_end,
            "valueAtStart": 0,
            "valueAtEnd": int(implied),
            "note": "Synthetic meter from implied active-rig output at current bids; reconciles each snapshot tick and at grid boundary.",
        },
    ]

    payload = {
        "schemaVersion": 1,
        "serverTimeIso": to_iso(utc_now()) or "",
        "miningDeliveryPeriodSeconds": int(MINING_DELIVERY_PERIOD),
        "miningNextCycleAt": slot_end,
        "miningSlotStartAt": slot_start,
        "world": world,
        "meters": meters,
        "market": _to_json_plain(serialize_resource_market()),
    }
    return JsonResponse(_to_json_plain(payload))
