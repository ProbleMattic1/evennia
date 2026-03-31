"""
Shared Ore Receiving Bay JSON for /ui/processing and control-surface ``processing``.

Dense rows: every catalog raw key (mining + flora + fauna), tons from inventory
(or zero). Unknown keys get appended for live ops visibility.

Use :func:`serialize_plant_intake_snapshot_rows` for UI totals that should include
all operators’ material at the plant (shared bay + silos + local raw).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def _raw_pipeline_for_catalog_key(kr: str) -> str:
    """mining | flora | fauna — keys from iter_plant_raw_resource_keys() always match one."""
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG
    from typeclasses.flora import FLORA_RESOURCE_CATALOG
    from typeclasses.mining import RESOURCE_CATALOG

    if kr in RESOURCE_CATALOG:
        return "mining"
    if kr in FLORA_RESOURCE_CATALOG:
        return "flora"
    if kr in FAUNA_RESOURCE_CATALOG:
        return "fauna"
    return "unknown"


def serialize_ore_receiving_bay_rows(receiving_bay, plant_room) -> list[dict[str, Any]]:
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG, get_fauna_commodity_bid
    from typeclasses.flora import FLORA_RESOURCE_CATALOG, get_flora_commodity_bid
    from typeclasses.mining import RESOURCE_CATALOG, get_commodity_bid
    from typeclasses.refining import iter_plant_raw_resource_keys, plant_raw_resource_display_name

    inv: dict = {}
    if receiving_bay is not None and getattr(receiving_bay.db, "inventory", None) is not None:
        inv = dict(receiving_bay.db.inventory or {})

    catalog_keys = frozenset(iter_plant_raw_resource_keys())
    sloc = plant_room
    rows: list[dict[str, Any]] = []

    for kr in sorted(catalog_keys):
        try:
            tons = float(inv.get(kr, 0) or 0)
        except (TypeError, ValueError):
            tons = 0.0
        if tons < 0:
            tons = 0.0
        tons = round(tons, 2)
        if kr in RESOURCE_CATALOG:
            bid = int(get_commodity_bid(kr, location=sloc))
        elif kr in FLORA_RESOURCE_CATALOG:
            bid = int(get_flora_commodity_bid(kr, location=sloc))
        elif kr in FAUNA_RESOURCE_CATALOG:
            bid = int(get_fauna_commodity_bid(kr, location=sloc))
        else:
            bid = 0
        rows.append(
            {
                "key": kr,
                "displayName": plant_raw_resource_display_name(kr),
                "tons": tons,
                "estimatedValueCr": int(round(tons * bid)),
                "rawPipeline": _raw_pipeline_for_catalog_key(kr),
            }
        )

    for k, raw_t in inv.items():
        kr = str(k)
        if kr in catalog_keys:
            continue
        try:
            tons = float(raw_t)
        except (TypeError, ValueError):
            continue
        if tons <= 0:
            continue
        tons = round(tons, 2)
        rows.append(
            {
                "key": kr,
                "displayName": kr,
                "tons": tons,
                "estimatedValueCr": 0,
                "rawPipeline": "unknown",
            }
        )

    rows.sort(key=lambda r: r["key"])
    return rows


def serialize_plant_intake_snapshot_rows(plant_room) -> list[dict[str, Any]]:
    """Same shape as :func:`serialize_ore_receiving_bay_rows`, merged across all plant intake."""
    from typeclasses.haulers import iter_plant_aggregated_raw_inventory

    inv_map = iter_plant_aggregated_raw_inventory(plant_room)
    pseudo = SimpleNamespace(db=SimpleNamespace(inventory=inv_map))
    return serialize_ore_receiving_bay_rows(pseudo, plant_room)
