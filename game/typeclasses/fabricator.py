"""
Station catalog fabricator — consumes character part_inventory and spawns PRODUCT_DEFINITIONS items.
"""

from __future__ import annotations

from typing import Any

from evennia.objects.objects import DefaultObject

from typeclasses.objects import ObjectParent
from world.part_inventory import consume_part_units_batch, get_part_inventory
from world.product_catalog import FABRICATION_RECIPES
from world.product_spawn import spawn_product_instance

STATION_FABRICATOR_TAG = "station_fabricator"
STATION_FABRICATOR_TAG_CATEGORY = "industry"


def fabricate_for_character(character: Any, recipe_id: str, *, batches: int = 1) -> tuple[int, str]:
    """
    Run a FABRICATION_RECIPES entry for ``character`` using their part_inventory.
    Returns (batches_completed, message).
    """
    recipe = FABRICATION_RECIPES.get(recipe_id)
    if not recipe:
        return 0, f"Unknown fabrication recipe '{recipe_id}'."

    batches = max(1, int(batches))
    inputs = dict(recipe.get("inputs") or {})
    out_cid = recipe.get("output_catalog_id")
    out_n = int(recipe.get("output_units_per_batch", 1) or 1)
    if not out_cid or out_n < 1:
        return 0, "Recipe misconfigured (output)."

    inv = get_part_inventory(character)
    possible = batches
    for pk, per_batch in inputs.items():
        per_batch = float(per_batch)
        if per_batch <= 0:
            return 0, "Recipe misconfigured (non-positive input)."
        have = float(inv.get(str(pk), 0.0))
        max_from_this = int(have / per_batch)
        possible = min(possible, max_from_this)

    if possible <= 0:
        need_lines = ", ".join(f"{float(v) * batches}× {k}" for k, v in inputs.items())
        return 0, f"Insufficient parts for {recipe.get('name', recipe_id)}. Need (for {batches} batch(es)): {need_lines}."

    required = {k: float(v) * possible for k, v in inputs.items()}
    if not consume_part_units_batch(character, required):
        return 0, "Could not consume parts (inventory changed)."

    name = recipe.get("name", recipe_id)
    for _ in range(possible * out_n):
        spawn_product_instance(out_cid, character, location=character)

    return possible, f"Fabricated {possible} batch(es) of {name}: {out_n * possible} unit(s) added to inventory."


class Fabricator(ObjectParent, DefaultObject):
    """Room object; players use fabricateproduct while in the same room."""

    def at_object_creation(self):
        self.db.desc = (
            "A compact industrial assembler tied to the station catalog. "
            "Withdraw refined output to parts, then fabricate listed products here."
        )
        self.tags.add(STATION_FABRICATOR_TAG, category=STATION_FABRICATOR_TAG_CATEGORY)
        self.locks.add("get:false()")

    def fabricate(self, operator, recipe_id: str, *, batches: int = 1) -> tuple[int, str]:
        return fabricate_for_character(operator, recipe_id, batches=batches)
