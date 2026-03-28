"""
Manufacturing UI helpers — feed stock for property detail (no command imports in typeclasses).
"""

from __future__ import annotations

from commands.manufacturing import _refined_sources_for_feed, _refined_sources_on_holding_only
from typeclasses.refining import REFINING_RECIPES


def _aggregate_refined_output(holding, caller, *, holding_sources_only: bool, room):
    totals: dict[str, float] = {}
    if holding_sources_only:
        sources = _refined_sources_on_holding_only(holding, caller)
    else:
        sources = _refined_sources_for_feed(holding, room, caller)
    for src in sources:
        inv = getattr(src.db, "output_inventory", None) or {}
        for k, raw in inv.items():
            totals[k] = round(float(totals.get(k, 0.0)) + float(raw), 2)
    return totals


def manufacturing_feed_stock_rows(holding, caller, *, holding_sources_only: bool, room):
    """
    Rows for <select>: only keys with units > 0.
    room: char.location (may be None); used when holding_sources_only is False.
    """
    totals = _aggregate_refined_output(
        holding, caller, holding_sources_only=holding_sources_only, room=room
    )
    rows = []
    for pk in sorted(totals):
        u = float(totals[pk])
        if u <= 0:
            continue
        rows.append(
            {
                "productKey": pk,
                "unitsAvailable": u,
                "name": REFINING_RECIPES[pk]["name"],
            }
        )
    return rows
