"""Move refined units from refinery / portable processor buffers into character part_inventory."""

from __future__ import annotations

import copy
from typing import Any

from typeclasses.refining import REFINING_RECIPES, Refinery
from world.part_inventory import add_part_units_batch


def withdraw_attributed_refinery_parts(
    refinery: Refinery,
    char: Any,
    *,
    withdraw_all: bool = False,
    amounts: dict[str, float] | None = None,
) -> tuple[bool, str]:
    """
    Remove units from refinery.db.miner_output[char.id] and credit char.db.part_inventory.
    No credit payout / treasury involvement.
    ``amounts``: explicit part_id -> units; if withdraw_all, ignore amounts and take everything.
    """
    oid = str(char.id)
    output = copy.deepcopy(dict(refinery.db.miner_output or {}))
    cur = dict(output.get(oid, {}))
    if not cur:
        return False, "You have no attributed refined output at this refinery."

    if withdraw_all:
        take = {k: round(float(v), 2) for k, v in cur.items() if float(v) > 0}
    else:
        take = {}
        if not amounts:
            return False, "Specify parts to withdraw or use withdraw all."
        for k, v in amounts.items():
            pk = str(k).strip()
            if pk not in REFINING_RECIPES:
                return False, f"Unknown part key '{pk}'."
            try:
                vu = round(float(v), 2)
            except (TypeError, ValueError):
                return False, f"Invalid amount for {pk}."
            if vu <= 0:
                continue
            take[pk] = take.get(pk, 0.0) + vu

    if not take:
        return False, "Nothing to withdraw."

    new_cur = dict(cur)
    for pk, want in take.items():
        if pk not in REFINING_RECIPES:
            return False, f"Unknown part key '{pk}'."
        have = round(float(new_cur.get(pk, 0.0)), 2)
        if want > have + 1e-9:
            return False, f"Not enough {REFINING_RECIPES[pk].get('name', pk)} (need {want}, have {have})."
        rem = round(have - want, 2)
        if rem <= 0:
            new_cur.pop(pk, None)
        else:
            new_cur[pk] = rem

    snap = copy.deepcopy(dict(refinery.db.miner_output or {}))
    try:
        if new_cur:
            output[oid] = new_cur
        else:
            output.pop(oid, None)
        refinery.db.miner_output = output
        add_part_units_batch(char, take)
    except Exception:
        refinery.db.miner_output = snap
        raise

    lines = [f"Withdrew parts to your fabrication hold ({refinery.key}):"]
    for pk in sorted(take.keys(), key=str):
        lines.append(f"  {REFINING_RECIPES[pk].get('name', pk)}: {take[pk]} units")
    return True, "\n".join(lines)


def withdraw_portable_processor_parts(
    processor: Any,
    char: Any,
    *,
    withdraw_all: bool = False,
    amounts: dict[str, float] | None = None,
) -> tuple[bool, str]:
    """Move units from PortableProcessor.db.output_inventory to char.db.part_inventory."""
    if getattr(processor.db, "owner", None) != char:
        return False, "That processor is not yours."

    out_inv = dict(processor.db.output_inventory or {})
    if not out_inv:
        return False, "Processor output is empty."

    if withdraw_all:
        take = {k: round(float(v), 2) for k, v in out_inv.items() if float(v) > 0}
    else:
        take = {}
        if not amounts:
            return False, "Specify parts to withdraw or use withdraw all."
        for k, v in amounts.items():
            pk = str(k).strip()
            if pk not in REFINING_RECIPES:
                return False, f"Unknown part key '{pk}'."
            try:
                vu = round(float(v), 2)
            except (TypeError, ValueError):
                return False, f"Invalid amount for {pk}."
            if vu <= 0:
                continue
            take[pk] = take.get(pk, 0.0) + vu

    if not take:
        return False, "Nothing to withdraw."

    new_out = dict(out_inv)
    for pk, want in take.items():
        have = round(float(new_out.get(pk, 0.0)), 2)
        if want > have + 1e-9:
            return False, f"Not enough {REFINING_RECIPES[pk].get('name', pk)} (need {want}, have {have})."
        rem = round(have - want, 2)
        if rem <= 0:
            new_out.pop(pk, None)
        else:
            new_out[pk] = rem

    snap = copy.deepcopy(dict(processor.db.output_inventory or {}))
    try:
        processor.db.output_inventory = new_out
        add_part_units_batch(char, take)
    except Exception:
        processor.db.output_inventory = snap
        raise

    lines = [f"Withdrew parts from {processor.key}:"]
    for pk in sorted(take.keys(), key=str):
        lines.append(f"  {REFINING_RECIPES[pk].get('name', pk)}: {take[pk]} units")
    return True, "\n".join(lines)
