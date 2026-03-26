"""
Blueprint catalog for purchasable structures on property holdings.

Each row: id (blueprint_id), display name, structure kind label, slot weight,
price in credits, allowed parcel zones.
"""

STRUCTURE_BLUEPRINT_CATALOG = (
    # --- Industrial only: HQ + making things ---
    {
        "id": "starter_hq",
        "name": "Starter HQ",
        "structureKind": "hq",
        "slotWeight": 3,
        "priceCr": 2500,
        "zones": ("industrial",),
    },
    {
        "id": "fab_bay_mk1",
        "name": "Fab Bay Mk I",
        "structureKind": "fab",
        "slotWeight": 5,
        "priceCr": 8500,
        "zones": ("industrial",),
    },
    {
        "id": "assembly_cell",
        "name": "Assembly Cell",
        "structureKind": "assembly",
        "slotWeight": 5,
        "priceCr": 9800,
        "zones": ("industrial",),
    },
    {
        "id": "junkyard_line",
        "name": "Junkyard Line",
        "structureKind": "line",
        "slotWeight": 4,
        "priceCr": 3200,
        "zones": ("industrial",),
    },
    {
        "id": "augmented_line",
        "name": "Augmented Line",
        "structureKind": "line",
        "slotWeight": 6,
        "priceCr": 12000,
        "zones": ("industrial",),
    },
    {
        "id": "warehouse_stack",
        "name": "Warehouse Stack",
        "structureKind": "warehouse",
        "slotWeight": 8,
        "priceCr": 18000,
        "zones": ("industrial",),
    },
    {
        "id": "logistics_hub",
        "name": "Logistics Hub",
        "structureKind": "logistics",
        "slotWeight": 7,
        "priceCr": 15500,
        "zones": ("industrial",),
    },
    {
        "id": "refinery_annex",
        "name": "Refinery Annex",
        "structureKind": "refinery",
        "slotWeight": 10,
        "priceCr": 35000,
        "zones": ("industrial",),
    },
    {
        "id": "power_foundry",
        "name": "Power Foundry",
        "structureKind": "power",
        "slotWeight": 9,
        "priceCr": 28000,
        "zones": ("industrial",),
    },
    # --- Commercial only: foot traffic / services / retail ---
    {
        "id": "vendor_booth",
        "name": "Vendor Booth",
        "structureKind": "booth",
        "slotWeight": 1,
        "priceCr": 800,
        "zones": ("commercial",),
    },
    {
        "id": "retail_strip",
        "name": "Retail Strip",
        "structureKind": "retail",
        "slotWeight": 4,
        "priceCr": 5200,
        "zones": ("commercial",),
    },
    {
        "id": "food_court_hall",
        "name": "Food Court Hall",
        "structureKind": "foodcourt",
        "slotWeight": 5,
        "priceCr": 6800,
        "zones": ("commercial",),
    },
    {
        "id": "service_counter",
        "name": "Service Counter",
        "structureKind": "service",
        "slotWeight": 3,
        "priceCr": 4100,
        "zones": ("commercial",),
    },
    {
        "id": "signage_network",
        "name": "Signage Network",
        "structureKind": "ads",
        "slotWeight": 2,
        "priceCr": 2200,
        "zones": ("commercial",),
    },
    {
        "id": "trade_spire",
        "name": "Trade Spire",
        "structureKind": "spire",
        "slotWeight": 11,
        "priceCr": 72000,
        "zones": ("commercial",),
    },
    # --- Residential only: living / community (no HQ / no heavy industry) ---
    {
        "id": "hab_tower_wing",
        "name": "Hab Tower Wing",
        "structureKind": "hab",
        "slotWeight": 4,
        "priceCr": 4800,
        "zones": ("residential",),
    },
    {
        "id": "garden_atrium",
        "name": "Garden Atrium",
        "structureKind": "garden",
        "slotWeight": 3,
        "priceCr": 3600,
        "zones": ("residential",),
    },
    {
        "id": "parking_pod",
        "name": "Parking Pod",
        "structureKind": "parking",
        "slotWeight": 2,
        "priceCr": 1900,
        "zones": ("residential",),
    },
    {
        "id": "civic_clubhouse",
        "name": "Civic Clubhouse",
        "structureKind": "civic",
        "slotWeight": 4,
        "priceCr": 5500,
        "zones": ("residential",),
    },
    {
        "id": "microgrid_node",
        "name": "Microgrid Node",
        "structureKind": "utility",
        "slotWeight": 3,
        "priceCr": 6200,
        "zones": ("residential",),
    },
    {
        "id": "arcology_core",
        "name": "Arcology Core",
        "structureKind": "arcology",
        "slotWeight": 12,
        "priceCr": 90000,
        "zones": ("residential",),
    },
)


def catalog_rows_for_zone(zone):
    z = (zone or "residential").lower()
    return [row for row in STRUCTURE_BLUEPRINT_CATALOG if z in row["zones"]]


def catalog_row_by_id(blueprint_id):
    bid = (blueprint_id or "").strip()
    for row in STRUCTURE_BLUEPRINT_CATALOG:
        if row["id"] == bid:
            return row
    return None
