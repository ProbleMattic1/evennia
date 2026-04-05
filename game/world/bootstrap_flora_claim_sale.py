"""
Bootstrap: standalone random flora claim deed at Mining Outfitters.

Purchase charges credits and grants a random FloraClaim via
claim_utils.grant_random_flora_claim_on_purchase. Idempotent.
"""

from evennia import create_object, search_object

CLAIM_SALE_SPEC = {
    "key": "Random Flora Claim Deed",
    "vendor_slug": "mining-outfitters",
    "desc": (
        "Agronomy services register a new unleased botanical stand and issue a deed. "
        "You receive one random flora claim; use deployflora with a flora package to develop it."
    ),
    "price": 3_750_000,
}


def _ensure_claim_sale_template(spec):
    from world.venues import all_venue_ids

    key = spec["key"]
    slug = spec["vendor_slug"]
    template = None
    for obj in search_object(key):
        if getattr(obj.db, "is_template", False) and getattr(
            obj.db, "grants_random_flora_claim_only", False
        ):
            template = obj
            break
    if not template:
        template = create_object("typeclasses.objects.Object", key=key, location=None)
    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.grants_random_flora_claim_only = True
    template.db.economy = {
        "base_price_cr": int(spec["price"]),
        "total_price_cr": int(spec["price"]),
    }
    if template.tags.has("mining-outfitters", category="vendor"):
        template.tags.remove("mining-outfitters", category="vendor")
    for venue_id in all_venue_ids():
        template.tags.add(f"{venue_id}-{slug}", category="vendor")
    template.locks.add("get:false()")
    return template


def bootstrap_flora_claim_sale():
    """Create or update the random flora claim deed catalog template."""
    t = _ensure_claim_sale_template(CLAIM_SALE_SPEC)
    print(f"[flora_claim_sale] '{t.key}' ready (venue-scoped mining-outfitters tags).")
