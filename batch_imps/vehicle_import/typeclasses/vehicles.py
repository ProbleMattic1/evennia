"""
Vehicle typeclass skeletons for an Evennia-based RPG vehicle catalog.

These classes are intentionally conservative for a first pass:
- They store vehicle data in structured db Attributes.
- They expose helper properties for the most common fields.
- They leave movement/combat/ownership systems open for later expansion.

Place this file in your game's `typeclasses/vehicles.py`.
"""

from evennia.objects.objects import DefaultObject


class Vehicle(DefaultObject):
    """
    Base vehicle typeclass.

    Expected db layout after import:

        self.db.catalog = {...}
        self.db.specs = {...}
        self.db.combat = {...}
        self.db.economy = {...}
        self.db.options = [...]
        self.db.weapon_profiles = [...]
        self.db.lore = {...}

    Notes:
        - `db` is persistent.
        - `ndb` is non-persistent and useful for runtime caches/state.
    """

    def at_object_creation(self):
        """Initialize defaults only the first time the object is created."""
        self.db.vehicle_kind = "vehicle"
        self.db.catalog = self.db.catalog or {}
        self.db.specs = self.db.specs or {}
        self.db.combat = self.db.combat or {}
        self.db.economy = self.db.economy or {}
        self.db.options = self.db.options or []
        self.db.weapon_profiles = self.db.weapon_profiles or []
        self.db.lore = self.db.lore or {}

        # Sensible baseline lock policy. Tighten later as your admin/game model evolves.
        self.locks.add("get:false()")
        self.locks.add("puppet:false()")
        self.locks.add("call:true()")

    @property
    def vehicle_id(self):
        return (self.db.catalog or {}).get("vehicle_id")

    @property
    def domain(self):
        return (self.db.specs or {}).get("domain")

    @property
    def vehicle_type(self):
        return (self.db.specs or {}).get("vehicle_type")

    @property
    def crew_required(self):
        return (self.db.specs or {}).get("crew_min")

    @property
    def total_price(self):
        return (self.db.economy or {}).get("total_price_cr")

    @property
    def hp(self):
        return (self.db.combat or {}).get("hp")

    def is_spaceworthy(self):
        return (self.domain or "").lower() == "space"

    def get_vehicle_summary(self):
        specs = self.db.specs or {}
        economy = self.db.economy or {}
        combat = self.db.combat or {}
        return (
            f"{self.key} "
            f"[{specs.get('domain', 'Unknown')} / {specs.get('vehicle_type', 'Unknown')}] | "
            f"crew {specs.get('crew_min', '?')}-{specs.get('crew_std', '?')} | "
            f"hp {combat.get('hp', '?')} | "
            f"price {economy.get('total_price_cr', '?')} cr"
        )

    def return_appearance(self, looker, **kwargs):
        base = super().return_appearance(looker, **kwargs)
        summary = self.get_vehicle_summary()
        return f"{base}\n\n|wVehicle Summary:|n {summary}"


class SurfaceVehicle(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = "surface_vehicle"


class Watercraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = "watercraft"


class Aircraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = "aircraft"


class Spacecraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = "spacecraft"

    def is_spaceworthy(self):
        return True
