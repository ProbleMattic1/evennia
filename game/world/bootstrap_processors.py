"""
Bootstrap for standalone personal ore processors at Mining Outfitters.

Three models are available for purchase. Processors are stored in inventory
until a player base is built; they will be placeable at the base later.

Runs from at_server_cold_start. Idempotent.
"""

from evennia import create_object, search_object


PROCESSORS = [
    {
        "key": "Ore Processor Mk I",
        "vendor_id": "mining-outfitters",
        "desc": (
            "A compact, entry-level ore refining unit. Accepts up to 200t of raw ore "
            "and processes it into refined materials. Stores in inventory; install at "
            "a player base to route your hauler directly."
        ),
        "price": 150_000,
        "capacity_tons": 200.0,
        "efficiency": 1.0,
        "mk": 1,
    },
    {
        "key": "Ore Processor Mk II",
        "vendor_id": "mining-outfitters",
        "desc": (
            "A mid-tier refining platform with expanded capacity and a 5% output "
            "efficiency bonus. Accepts up to 500t of raw ore. Store in inventory "
            "until you have a base to install it."
        ),
        "price": 380_000,
        "capacity_tons": 500.0,
        "efficiency": 1.05,
        "mk": 2,
    },
    {
        "key": "Ore Processor Mk III",
        "vendor_id": "mining-outfitters",
        "desc": (
            "Industrial-grade processing unit. Accepts up to 1,000t of raw ore with "
            "a 12% output efficiency bonus. The choice of serious mining operations. "
            "Store in inventory until a base is available."
        ),
        "price": 850_000,
        "capacity_tons": 1000.0,
        "efficiency": 1.12,
        "mk": 3,
    },
]


def _ensure_processor_template(spec):
    """Create or update a PortableProcessor template for Mining Outfitters."""
    key = spec["key"]
    vendor_id = spec["vendor_id"]

    template = None
    for obj in search_object(key):
        if (
            getattr(obj.db, "is_template", False)
            and obj.is_typeclass("typeclasses.processors.PortableProcessor", exact=False)
        ):
            template = obj
            break

    if not template:
        template = create_object(
            "typeclasses.processors.PortableProcessor",
            key=key,
            location=None,
        )

    template.db.desc = spec["desc"]
    template.db.is_template = True
    template.db.processor_mk = spec["mk"]
    template.db.capacity_tons = spec["capacity_tons"]
    template.db.efficiency = spec["efficiency"]
    template.db.economy = {
        "base_price_cr": int(spec["price"]),
        "total_price_cr": int(spec["price"]),
    }
    template.tags.add(vendor_id, category="vendor")
    template.locks.add("get:false()")
    return template


def bootstrap_processors():
    """Create or update all processor templates at Mining Outfitters. Idempotent."""
    for spec in PROCESSORS:
        t = _ensure_processor_template(spec)
        print(f"[processors] '{t.key}' ready for vendor '{spec['vendor_id']}'.")
    print("[processors] Bootstrap complete.")
