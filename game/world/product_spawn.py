"""Spawn product instances from PRODUCT_DEFINITIONS."""

from __future__ import annotations

from typing import Any

from evennia import create_object

from world.product_catalog import PRODUCT_DEFINITIONS


def spawn_product_instance(catalog_id: str, owner: Any, *, location: Any | None = None):
    """
    Create a carried good from the catalog. Sets db.catalog_id, tags, economy, locks.
    ``location`` defaults to ``owner`` (inventory).
    """
    spec = PRODUCT_DEFINITIONS.get(catalog_id)
    if not spec:
        raise ValueError(f"Unknown catalog_id {catalog_id!r}")

    loc = location if location is not None else owner
    key = str(spec.get("display_key") or catalog_id)

    obj = create_object(
        spec["typeclass_path"],
        key=key,
        location=loc,
        home=loc,
    )
    obj.db.catalog_id = catalog_id
    obj.db.desc = str(spec.get("desc") or "")
    obj.db.economy = {"base_price_cr": int(spec.get("base_price_cr", 0) or 0)}
    obj.db.is_template = False
    obj.db.owner = owner

    tag = spec["inventory_bucket_tag"]
    obj.tags.add(str(tag), category="inventory")
    obj.locks.add("get:true();drop:true();give:true()")
    return obj
