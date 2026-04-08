"""
Unified product catalog: parts (refining outputs) + fabricatable products + recipes.

Part IDs match REFINING_RECIPES keys. Raw resources stay in mining/flora/fauna catalogs.
"""

from __future__ import annotations

from typing import Any

from typeclasses.refining import REFINING_RECIPES

# ---------------------------------------------------------------------------
# Parts — derived from refining (single source for names/values)
# ---------------------------------------------------------------------------

PART_DEFINITIONS: dict[str, dict[str, Any]] = {
    k: {
        "part_id": k,
        "name": v["name"],
        "desc": v.get("desc") or "",
        "category": v.get("category") or "",
        "base_value_cr": int(v.get("base_value_cr", 0) or 0),
    }
    for k, v in REFINING_RECIPES.items()
}

# ---------------------------------------------------------------------------
# Products — finished goods (spawned Evennia objects)
# ---------------------------------------------------------------------------

# display_key must match shop template object key where applicable (bootstrap_shops).
PRODUCT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "prod.supply_multitool": {
        "catalog_id": "prod.supply_multitool",
        "display_key": "Supply Multitool",
        "desc": "All-in-one driver, cutter, and pry bar.",
        "typeclass_path": "typeclasses.objects.Object",
        "inventory_bucket_tag": "tool",
        "base_price_cr": 140,
    },
}

# ---------------------------------------------------------------------------
# Fabrication — parts (units) -> product instances
# ---------------------------------------------------------------------------

FABRICATION_RECIPES: dict[str, dict[str, Any]] = {
    "fab.supply_multitool_v1": {
        "recipe_id": "fab.supply_multitool_v1",
        "name": "Assemble Supply Multitool",
        "inputs": {
            "refined_iron": 1.0,
            "refined_copper": 1.0,
        },
        "output_catalog_id": "prod.supply_multitool",
        "output_units_per_batch": 1,
    },
}


def catalog_id_for_display_key(display_key: str) -> str | None:
    dk = (display_key or "").strip()
    if not dk:
        return None
    for cid, row in PRODUCT_DEFINITIONS.items():
        if row.get("display_key") == dk:
            return cid
    return None


def get_fabrication_recipe(recipe_id: str) -> dict[str, Any] | None:
    r = FABRICATION_RECIPES.get(recipe_id)
    return dict(r) if r else None
