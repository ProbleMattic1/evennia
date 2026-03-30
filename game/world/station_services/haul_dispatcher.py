from __future__ import annotations

from typeclasses.haulers import (
    format_next_hauler_run_utc,
    get_hauler_next_cycle_at,
    get_mining_storage_in_room,
    get_refinery_in_room,
)


def handle(character, args: str, extra_switches: tuple[str, ...]) -> str:
    loc = character.location
    if not loc:
        return "No location."

    lines = ["|wHaul dispatch|n (this room / your carried haulers):"]

    ref = get_refinery_in_room(loc)
    if ref:
        lines.append(f"  Refinery |c{ref.key}|n present.")
    stor = get_mining_storage_in_room(loc)
    if stor:
        lines.append(f"  Mining storage |c{stor.key}|n present.")

    checked = set()
    for obj in list(loc.contents) + [character]:
        if obj is None or id(obj) in checked:
            continue
        checked.add(id(obj))
        nxt = get_hauler_next_cycle_at(obj)
        if nxt:
            lines.append(
                f"  Hauler on |c{obj.key}|n — next run ~ {format_next_hauler_run_utc(obj)}"
            )

    if len(lines) == 1:
        lines.append("No hauler-linked objects detected here. Try your claim site or dock.")

    return "\n".join(lines)
