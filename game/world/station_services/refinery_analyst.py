from __future__ import annotations

from typeclasses.haulers import get_refinery_in_room
from typeclasses.refining import (
    PROCESSING_FEE_RATE,
    is_plant_raw_resource_key,
    plant_raw_resource_display_name,
    refined_payout_breakdown,
)


def handle(character, args: str, extra_switches: tuple[str, ...]) -> str:
    loc = character.location
    ref = get_refinery_in_room(loc) if loc else None
    if not ref:
        return "No refinery in this room — I can't price behavior here."

    fee_rate = float(getattr(ref.db, "processing_fee_rate", None) or PROCESSING_FEE_RATE)
    gross_example = 10_000
    br = refined_payout_breakdown(gross_example, fee_rate)

    lines = [
        f"|wRefinery analyst|n (|c{ref.key}|n)",
        f"  Example gross |w{gross_example:,}|n cr, fee rate |y{fee_rate:.2%}|n:",
        f"    net to miner (illustrative): |g{br.get('net', 0):,}|n cr",
        f"    fee total: |y{br.get('fee', 0):,}|n cr",
    ]

    raw_keys = []
    for obj in character.contents:
        rk = getattr(obj.db, "resource_key", None) or getattr(obj.db, "ore_type", None)
        if rk and is_plant_raw_resource_key(str(rk)):
            raw_keys.append(str(rk))
    if raw_keys:
        uniq = sorted(set(raw_keys))
        names = [plant_raw_resource_display_name(k) for k in uniq[:12]]
        lines.append(f"  Plant-facing raw in your inventory: |c{', '.join(names)}|n")
        if len(uniq) > 12:
            lines.append(f"    ... and {len(uniq) - 12} more resource type(s).")
    else:
        lines.append(
            "  |gTip:|n feed ore into the plant silo or receiving bay, then |wfeedrefinery|n."
        )

    return "\n".join(lines)
