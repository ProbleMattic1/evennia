"""
Property lots — claimable land parcels sold at the Real Estate Office.

Distinct from mining sites.  A Residential / Commercial / Industrial property
claim deed references one lot.  Future rules differ by claim kind.

Tiers: 1 Starter, 2 Standard, 3 Prime.
The lot's ``db.zone`` selects which property-claim typeclass is minted on sale.
"""

from .objects import Object

ZONE_LABELS = {
    "commercial":  "Commercial District",
    "industrial":  "Industrial Sector",
    "residential": "Residential Block",
}

TIER_LABELS = {1: "Starter", 2: "Standard", 3: "Prime"}

TIER_LIST_PRICES = {1: 5_000, 2: 15_000, 3: 45_000}

ZONE_MULTIPLIERS = {
    "commercial":  1.20,
    "industrial":  1.05,
    "residential": 1.00,
}


class PropertyLot(Object):
    """A claimable parcel listed by the sovereign realty office."""

    def at_object_creation(self):
        self.db.is_claimed = False
        self.db.owner      = None
        self.db.holding_ref = None
        self.db.lot_tier   = 1
        self.db.zone       = "residential"
        self.db.size_units = 1
        loc = self.location
        if loc and getattr(loc.db, "venue_id", None):
            self.db.venue_id = loc.db.venue_id
        self.tags.add("property_lot", category="realty")
        self.locks.add("get:false();drop:false()")
        from typeclasses.property_lot_registry import register_listable_property_lot

        register_listable_property_lot(self)

    @property
    def tier_label(self):
        return TIER_LABELS.get(int(self.db.lot_tier or 1), "Unknown")

    @property
    def zone_label(self):
        return ZONE_LABELS.get(self.db.zone or "residential", "Unknown")
