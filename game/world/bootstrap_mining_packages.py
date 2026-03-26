"""
Bootstrap for mining sale packages at Aurnom Mining Outfitters.

Each package bundles a rig, storage, and hauler sold as a single item.
Packages appear in the Mining Outfitters shop (vendor_id="mining-outfitters").

With-claim packages grant a random MiningClaim on purchase (see shop / web API).
Equipment-only packages are the same gear at the prior price tier without a claim.
Use deploymine <package> <claim> to deploy at a claim you own.
"""

from evennia import create_object, search_object


# With random claim: 4× prior catalog (1M / 2.25M / 3.5M → 4M / 9M / 14M).
# Equipment only: prior pricing (1M / 2.25M / 3.5M), no claim on purchase.

MINING_PACKAGES = [
    {
        "key": "Mining Starter Pack",
        "deploy_profile": "mining_starter",
        "includes_random_claim": True,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Entry-level mine-in-a-box. Includes a Mining Rig Mk I, "
            "Storage Unit (500t), and an Mk I Autonomous Hauler (50t; daily UTC pickup, staggered). "
            "Buy to receive package + random claim; use deploymine to deploy."
        ),
        "price": 4_000_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk I",
                "desc": "A rugged single-head extraction platform rated for hard-rock formations.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Storage Unit Alpha",
                "desc": "A sealed ore hopper with a tamper-evident manifest panel.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
    {
        "key": "Mining Starter Pack (Equipment Only)",
        "deploy_profile": "mining_starter",
        "includes_random_claim": False,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Entry-level mine-in-a-box. Includes a Mining Rig Mk I, "
            "Storage Unit (500t), and an Mk I Autonomous Hauler (50t; daily UTC pickup, staggered). "
            "Equipment only — obtain a claim deed separately; use deploymine to deploy."
        ),
        "price": 1_000_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk I",
                "desc": "A rugged single-head extraction platform rated for hard-rock formations.",
                "rig_rating": 1.0,
            },
            {
                "type": "storage",
                "key": "Storage Unit Alpha",
                "desc": "A sealed ore hopper with a tamper-evident manifest panel.",
                "capacity_tons": 500.0,
            },
            {
                "type": "hauler",
                "key": "Mk I Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 50.0,
                "cycle_hours": 4.0,
            },
        ],
    },
    {
        "key": "Mining Operator Pack",
        "deploy_profile": "mining_operator",
        "includes_random_claim": True,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Mid-tier operation for established miners. Includes a Mining Rig Mk II, "
            "Storage Unit (800t), and an Mk II Autonomous Hauler (120t; daily UTC pickup, staggered). "
            "Buy to receive package + random claim; use deploymine to deploy."
        ),
        "price": 9_000_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk II",
                "desc": "A precision-drill platform suited for selective gem-bearing extraction.",
                "rig_rating": 1.1,
            },
            {
                "type": "storage",
                "key": "Storage Unit Beta",
                "desc": "A reinforced ore safe with separate gem-matrix compartments.",
                "capacity_tons": 800.0,
            },
            {
                "type": "hauler",
                "key": "Mk II Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 120.0,
                "cycle_hours": 3.0,
            },
        ],
    },
    {
        "key": "Mining Operator Pack (Equipment Only)",
        "deploy_profile": "mining_operator",
        "includes_random_claim": False,
        "vendor_id": "mining-outfitters",
        "desc": (
            "Mid-tier operation for established miners. Includes a Mining Rig Mk II, "
            "Storage Unit (800t), and an Mk II Autonomous Hauler (120t; daily UTC pickup, staggered). "
            "Equipment only — obtain a claim deed separately; use deploymine to deploy."
        ),
        "price": 2_250_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk II",
                "desc": "A precision-drill platform suited for selective gem-bearing extraction.",
                "rig_rating": 1.1,
            },
            {
                "type": "storage",
                "key": "Storage Unit Beta",
                "desc": "A reinforced ore safe with separate gem-matrix compartments.",
                "capacity_tons": 800.0,
            },
            {
                "type": "hauler",
                "key": "Mk II Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 120.0,
                "cycle_hours": 3.0,
            },
        ],
    },
    {
        "key": "Mining Pro Pack",
        "deploy_profile": "mining_pro",
        "includes_random_claim": True,
        "vendor_id": "mining-outfitters",
        "desc": (
            "High-output industrial operation. Includes a Mining Rig Mk III, "
            "Storage Unit (1,500t), and an Mk III Autonomous Hauler (250t; daily UTC pickup, staggered). "
            "Buy to receive package + random claim; use deploymine to deploy."
        ),
        "price": 14_000_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk III",
                "desc": "A high-throughput tri-head drill platform for industrial-scale extraction.",
                "rig_rating": 1.25,
            },
            {
                "type": "storage",
                "key": "Storage Unit Gamma",
                "desc": "A heavy-gauge pressurised silo rated for bulk ore and volatile mineral storage.",
                "capacity_tons": 1500.0,
            },
            {
                "type": "hauler",
                "key": "Mk III Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 250.0,
                "cycle_hours": 2.0,
            },
        ],
    },
    {
        "key": "Mining Pro Pack (Equipment Only)",
        "deploy_profile": "mining_pro",
        "includes_random_claim": False,
        "vendor_id": "mining-outfitters",
        "desc": (
            "High-output industrial operation. Includes a Mining Rig Mk III, "
            "Storage Unit (1,500t), and an Mk III Autonomous Hauler (250t; daily UTC pickup, staggered). "
            "Equipment only — obtain a claim deed separately; use deploymine to deploy."
        ),
        "price": 3_500_000,
        "components": [
            {
                "type": "rig",
                "key": "Mining Rig Mk III",
                "desc": "A high-throughput tri-head drill platform for industrial-scale extraction.",
                "rig_rating": 1.25,
            },
            {
                "type": "storage",
                "key": "Storage Unit Gamma",
                "desc": "A heavy-gauge pressurised silo rated for bulk ore and volatile mineral storage.",
                "capacity_tons": 1500.0,
            },
            {
                "type": "hauler",
                "key": "Mk III Autonomous Hauler",
                "desc": "Autonomous hauler assigned to your mine route at purchase.",
                "cargo_capacity_tons": 250.0,
                "cycle_hours": 2.0,
            },
        ],
    },
]


def _ensure_package_template(spec):
    """Create or update a sale package template for a given spec."""
    key = spec["key"]
    vendor_id = spec["vendor_id"]
    found = search_object(key)
    # Only match templates, not previously created package instances
    template = None
    for obj in found:
        if getattr(obj.db, "is_sale_package", False) and getattr(obj.db, "is_template", False):
            template = obj
            break

    if not template:
        template = create_object("typeclasses.objects.Object", key=key, location=None)

    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.is_sale_package = True
    template.db.package_tier = spec["deploy_profile"]
    template.db.includes_random_claim = bool(spec.get("includes_random_claim", False))
    template.db.package_components = spec["components"]
    template.db.economy = {
        "base_price_cr": int(spec["price"]),
        "total_price_cr": int(spec["price"]),
    }
    template.tags.add(vendor_id, category="vendor")
    template.locks.add("get:false()")
    return template


def bootstrap_mining_packages():
    """Create or update all mining sale package templates. Idempotent."""
    for spec in MINING_PACKAGES:
        t = _ensure_package_template(spec)
        print(f"[mining_packages] Package '{t.key}' ready for vendor '{spec['vendor_id']}'.")
    print("[mining_packages] Bootstrap complete.")
