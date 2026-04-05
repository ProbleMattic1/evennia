"""
Flora and fauna sale packages at Mining Outfitters (harvester / storage / hauler).

Mirrors mining packages: with-claim SKUs grant a random flora or fauna claim on purchase;
equipment-only variants omit the claim. Use deployflora / deployfauna with package + claim.
"""

from evennia import create_object, search_object

FLORA_PACKAGES = [
    {
        "key": "Flora Starter Pack",
        "deploy_profile": "flora_starter",
        "package_kind": "flora",
        "includes_random_claim": True,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Entry-level flora harvest-in-a-box: Flora Harvester Mk I, Flora Storage Alpha (500t), "
            "Mk I Autonomous Flora Hauler (50t; UTC hourly harvest grid; hauler pickup +15m after deposit). "
            "Buy to receive package + random flora claim; use deployflora to deploy."
        ),
        "price": 4_000_000,
        "components": [
            {
                "type": "harvester",
                "key": "Flora Harvester Mk I",
                "desc": "Single-head botanical harvest head for leased stands.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Flora Storage Alpha",
                "desc": "Pressurised bulk bin for mixed harvest manifests.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Flora Hauler",
                "desc": "Autonomous hauler on the flora route.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
    {
        "key": "Flora Starter Pack (Equipment Only)",
        "deploy_profile": "flora_starter",
        "package_kind": "flora",
        "includes_random_claim": False,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Flora harvest equipment only — obtain a flora claim deed separately; use deployflora."
        ),
        "price": 1_000_000,
        "components": [
            {
                "type": "harvester",
                "key": "Flora Harvester Mk I",
                "desc": "Single-head botanical harvest head for leased stands.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Flora Storage Alpha",
                "desc": "Pressurised bulk bin for mixed harvest manifests.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Flora Hauler",
                "desc": "Autonomous hauler on the flora route.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
]

FAUNA_PACKAGES = [
    {
        "key": "Fauna Starter Pack",
        "deploy_profile": "fauna_starter",
        "package_kind": "fauna",
        "includes_random_claim": True,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Entry-level fauna harvest-in-a-box: Fauna Harvester Mk I, Fauna Storage Alpha (500t), "
            "Mk I Autonomous Fauna Hauler (50t; UTC hourly harvest grid; hauler pickup +15m after deposit). "
            "Buy to receive package + random fauna claim; use deployfauna to deploy."
        ),
        "price": 4_000_000,
        "components": [
            {
                "type": "harvester",
                "key": "Fauna Harvester Mk I",
                "desc": "Single-head culture harvest unit for leased ranges.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Fauna Storage Alpha",
                "desc": "Cold-chain biomass bin for culture harvest.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Fauna Hauler",
                "desc": "Autonomous hauler on the fauna route.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
    {
        "key": "Fauna Starter Pack (Equipment Only)",
        "deploy_profile": "fauna_starter",
        "package_kind": "fauna",
        "includes_random_claim": False,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Fauna harvest equipment only — obtain a fauna claim deed separately; use deployfauna."
        ),
        "price": 1_000_000,
        "components": [
            {
                "type": "harvester",
                "key": "Fauna Harvester Mk I",
                "desc": "Single-head culture harvest unit for leased ranges.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Fauna Storage Alpha",
                "desc": "Cold-chain biomass bin for culture harvest.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Fauna Hauler",
                "desc": "Autonomous hauler on the fauna route.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
]


def _ensure_bio_package_template(spec):
    from world.venues import all_venue_ids

    key = spec["key"]
    slug = spec["vendor_id"]
    found = search_object(key)
    template = None
    for obj in found:
        if obj.key == key and getattr(obj.db, "is_sale_package", False) and getattr(
            obj.db, "is_template", False
        ):
            template = obj
            break
    if not template:
        template = create_object("typeclasses.objects.Object", key=key, location=None)
    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.is_sale_package = True
    template.db.package_tier = spec["deploy_profile"]
    template.db.package_kind = spec["package_kind"]
    template.db.includes_random_claim = bool(spec.get("includes_random_claim", False))
    template.db.package_components = spec["components"]
    template.db.economy = {
        "base_price_cr": int(spec["price"]),
        "total_price_cr": int(spec["price"]),
    }
    if template.tags.has(slug, category="vendor"):
        template.tags.remove(slug, category="vendor")
    for venue_id in all_venue_ids():
        template.tags.add(f"{venue_id}-{slug}", category="vendor")
    template.locks.add("get:false()")
    return template


def bootstrap_bio_packages():
    """Create or update flora/fauna package templates at Mining Outfitters."""
    for spec in FLORA_PACKAGES:
        t = _ensure_bio_package_template(spec)
        print(f"[bio_packages] Flora package '{t.key}' ready.")
    for spec in FAUNA_PACKAGES:
        t = _ensure_bio_package_template(spec)
        print(f"[bio_packages] Fauna package '{t.key}' ready.")
    print("[bio_packages] Bootstrap complete.")
