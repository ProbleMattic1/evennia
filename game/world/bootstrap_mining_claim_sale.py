"""
Bootstrap for standalone random mining claim deed at Mining Outfitters.

Purchase charges credits and grants a random claim via claim_utils.grant_random_claim_on_purchase
(see commands.shop and web ui catalog purchase). No inventory item is created.

Runs from at_server_cold_start. Idempotent.
"""

from evennia import create_object, search_object

CLAIM_SALE_SPEC = {
    "key": "Random Mining Claim Deed",
    "vendor_slug": "mining-outfitters",
    "desc": (
        "Survey services register a new unclaimed deposit and issue a deed. "
        "You receive one random claim; use deploymine with a mining package to develop it."
    ),
    "price": 3_750_000,
}


def _ensure_claim_sale_template(spec):
    from world.venues import all_venue_ids

    key = spec["key"]
    slug = spec["vendor_slug"]
    template = None
    for obj in search_object(key):
        if getattr(obj.db, "is_template", False) and getattr(obj.db, "grants_random_claim_only", False):
            template = obj
            break
    if not template:
        template = create_object("typeclasses.objects.Object", key=key, location=None)
    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.grants_random_claim_only = True
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


def bootstrap_mining_claim_sale():
    """Create or update the random claim deed catalog template."""
    t = _ensure_claim_sale_template(CLAIM_SALE_SPEC)
    print(f"[mining_claim_sale] '{t.key}' ready (venue-scoped mining-outfitters tags).")
