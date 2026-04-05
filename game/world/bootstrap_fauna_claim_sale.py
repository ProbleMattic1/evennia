"""
Bootstrap: standalone random fauna claim deed at Mining Outfitters.

Purchase charges credits and grants a random FaunaClaim via
claim_utils.grant_random_fauna_claim_on_purchase. Idempotent.
"""

from evennia import create_object, search_object

CLAIM_SALE_SPEC = {
    "key": "Random Fauna Claim Deed",
    "vendor_slug": "mining-outfitters",
    "desc": (
        "Range services register a new unleased culture band and issue a deed. "
        "You receive one random fauna claim; use deployfauna with a fauna package to develop it."
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
            obj.db, "grants_random_fauna_claim_only", False
        ):
            template = obj
            break
    if not template:
        template = create_object("typeclasses.objects.Object", key=key, location=None)
    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.grants_random_fauna_claim_only = True
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


def bootstrap_fauna_claim_sale():
    """Create or update the random fauna claim deed catalog template."""
    t = _ensure_claim_sale_template(CLAIM_SALE_SPEC)
    print(f"[fauna_claim_sale] '{t.key}' ready (venue-scoped mining-outfitters tags).")
