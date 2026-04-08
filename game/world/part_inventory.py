"""Character-scoped part balances for fabrication (keys = REFINING_RECIPES output keys)."""

from __future__ import annotations

from typing import Any

PART_UNIT_DECIMALS = 2


def _round_units(u: float) -> float:
    return round(float(u), PART_UNIT_DECIMALS)


def get_part_inventory(char: Any) -> dict[str, float]:
    raw = getattr(char.db, "part_inventory", None) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in raw.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv <= 0:
            continue
        out[str(k)] = _round_units(fv)
    return out


def set_part_inventory(char: Any, inv: dict[str, float]) -> None:
    char.db.part_inventory = {str(k): _round_units(v) for k, v in inv.items() if _round_units(v) > 0}


def add_part_units(char: Any, part_id: str, units: float) -> float:
    """Add units to char's part inventory; returns new total for that part."""
    part_id = str(part_id).strip()
    u = _round_units(units)
    if u <= 0:
        return _round_units(float((get_part_inventory(char).get(part_id) or 0)))
    inv = get_part_inventory(char)
    new_total = _round_units(float(inv.get(part_id, 0.0)) + u)
    inv[part_id] = new_total
    set_part_inventory(char, inv)
    return new_total


def add_part_units_batch(char: Any, amounts: dict[str, float]) -> None:
    for k, v in amounts.items():
        add_part_units(char, k, float(v))


def consume_part_units(char: Any, part_id: str, units: float) -> bool:
    """Subtract units if available. Returns False if insufficient."""
    part_id = str(part_id).strip()
    need = _round_units(units)
    if need <= 0:
        return True
    inv = get_part_inventory(char)
    have = _round_units(float(inv.get(part_id, 0.0)))
    if have + 1e-9 < need:
        return False
    rem = _round_units(have - need)
    if rem <= 0:
        inv.pop(part_id, None)
    else:
        inv[part_id] = rem
    set_part_inventory(char, inv)
    return True


def consume_part_units_batch(char: Any, required: dict[str, float]) -> bool:
    inv = get_part_inventory(char)
    for pk, amt in required.items():
        pk = str(pk).strip()
        need = _round_units(float(amt))
        if need <= 0:
            continue
        have = _round_units(float(inv.get(pk, 0.0)))
        if have + 1e-9 < need:
            return False
    for pk, amt in required.items():
        pk = str(pk).strip()
        need = _round_units(float(amt))
        if need <= 0:
            continue
        have = _round_units(float(inv.get(pk, 0.0)))
        rem = _round_units(have - need)
        if rem <= 0:
            inv.pop(pk, None)
        else:
            inv[pk] = rem
    set_part_inventory(char, inv)
    return True


def part_inventory_for_json(char: Any) -> list[dict[str, Any]]:
    """Sorted rows for dashboard / fabricator payloads."""
    inv = get_part_inventory(char)
    rows = []
    for k in sorted(inv.keys(), key=str):
        rows.append({"partId": k, "units": inv[k]})
    return rows
