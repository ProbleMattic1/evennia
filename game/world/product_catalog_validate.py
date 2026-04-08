"""Validate product catalog invariants. Raises ValueError with joined messages on failure."""

from __future__ import annotations

from typing import Any

from typeclasses.refining import REFINING_RECIPES
from world.inventory_taxonomy import inventory_bucket
from world.product_catalog import FABRICATION_RECIPES, PART_DEFINITIONS, PRODUCT_DEFINITIONS


class _TagProbe:
    """Minimal object so inventory_bucket() accepts a single inventory tag."""

    def __init__(self, bucket_tag: str):
        self.tags = self
        self._bucket_tag = bucket_tag

    def has(self, name: str, category: str | None = None) -> bool:
        return name == self._bucket_tag and category == "inventory"


def validate_product_catalog() -> None:
    errors: list[str] = []

    rr_keys = set(REFINING_RECIPES.keys())
    pd_keys = set(PART_DEFINITIONS.keys())
    if rr_keys != pd_keys:
        missing = sorted(rr_keys - pd_keys)
        extra = sorted(pd_keys - rr_keys)
        if missing:
            errors.append(f"PART_DEFINITIONS missing refining keys: {missing[:20]}{'…' if len(missing) > 20 else ''}")
        if extra:
            errors.append(f"PART_DEFINITIONS has unknown keys: {extra[:20]}{'…' if len(extra) > 20 else ''}")

    seen_catalog_ids: set[str] = set()
    for cid, row in PRODUCT_DEFINITIONS.items():
        if cid != row.get("catalog_id"):
            errors.append(f"PRODUCT_DEFINITIONS top-level key {cid!r} != row catalog_id {row.get('catalog_id')!r}")
        if cid in seen_catalog_ids:
            errors.append(f"Duplicate product catalog_id {cid!r}")
        seen_catalog_ids.add(cid)

        tag = row.get("inventory_bucket_tag")
        if not tag or not isinstance(tag, str):
            errors.append(f"Product {cid!r} missing inventory_bucket_tag")
        else:
            b = inventory_bucket(_TagProbe(tag))
            if b != tag:
                errors.append(
                    f"Product {cid!r} inventory_bucket_tag {tag!r} is not a recognized inventory bucket "
                    f"(inventory_bucket resolved to {b!r})"
                )

        if not row.get("typeclass_path"):
            errors.append(f"Product {cid!r} missing typeclass_path")
        if not row.get("display_key"):
            errors.append(f"Product {cid!r} missing display_key")

    for rid, rec in FABRICATION_RECIPES.items():
        if rid != rec.get("recipe_id"):
            errors.append(f"FABRICATION_RECIPES key {rid!r} != recipe_id field")
        out_id = rec.get("output_catalog_id")
        if not out_id or out_id not in PRODUCT_DEFINITIONS:
            errors.append(f"Recipe {rid!r} output_catalog_id {out_id!r} not in PRODUCT_DEFINITIONS")
        inputs = rec.get("inputs") or {}
        if not isinstance(inputs, dict) or not inputs:
            errors.append(f"Recipe {rid!r} has no inputs")
        else:
            for pk, amt in inputs.items():
                if pk not in REFINING_RECIPES:
                    errors.append(f"Recipe {rid!r} input part {pk!r} not in REFINING_RECIPES")
                try:
                    if float(amt) <= 0:
                        errors.append(f"Recipe {rid!r} input {pk!r} must be positive")
                except (TypeError, ValueError):
                    errors.append(f"Recipe {rid!r} input {pk!r} has invalid amount {amt!r}")
        ou = rec.get("output_units_per_batch", 1)
        try:
            if int(ou) < 1:
                errors.append(f"Recipe {rid!r} output_units_per_batch must be >= 1")
        except (TypeError, ValueError):
            errors.append(f"Recipe {rid!r} invalid output_units_per_batch {ou!r}")

    if errors:
        raise ValueError("product catalog validation failed:\n" + "\n".join(errors))
