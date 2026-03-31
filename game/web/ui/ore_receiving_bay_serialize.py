"""
Shared Ore Receiving Bay JSON for /ui/processing and control-surface ``processing``.

Dense rows: every catalog raw key (mining + flora + fauna), tons from bay inventory
(or zero). Unknown bay keys get appended for live ops visibility.
"""

from __future__ import annotations

from typing import Any


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
            }
        )

    rows.sort(key=lambda r: r["key"])
    return rows
