"""
Vehicle typeclass skeletons for an Evennia-based RPG vehicle catalog.

This version includes a lightweight interaction layer:
- vehicles can be boarded and exited
- a pilot can control movement
- ownership and guest access are checked in one place
- vehicles act as containers/locations for passengers
"""

from evennia.objects.objects import DefaultObject
from typeclasses.economy import get_price as economy_get_price


class Vehicle(DefaultObject):
    """Base vehicle typeclass with interaction hooks."""

    def at_object_creation(self):
        self.db.is_vehicle = True
        self.db.vehicle_kind = self.db.vehicle_kind or 'vehicle'
        self.db.catalog = self.db.catalog or {}
        self.db.specs = self.db.specs or {}
        self.db.combat = self.db.combat or {}
        self.db.economy = self.db.economy or {}
        self.db.options = self.db.options or []
        self.db.weapon_profiles = self.db.weapon_profiles or []
        self.db.lore = self.db.lore or {}
        self.db.owner = self.db.owner or None
        self.db.allowed_boarders = self.db.allowed_boarders or []
        self.db.pilot = self.db.pilot or None
        self.db.exterior_location = self.db.exterior_location or None
        self.db.state = self.db.state or 'docked'
        self.db.registration_id = self.db.registration_id or None
        self.db.fuel = self.db.fuel if self.db.fuel is not None else 100
        self.db.max_fuel = self.db.max_fuel if self.db.max_fuel is not None else 100
        # Cargo hold (mining / freight integration)
        self.db.cargo = self.db.cargo or {}
        self.db.cargo_capacity_tons = self.db.cargo_capacity_tons if self.db.cargo_capacity_tons is not None else 0

        self.locks.add('get:false()')
        self.locks.add('puppet:false()')
        self.locks.add('call:true()')
        self.locks.add('enter:all()')

    @property
    def vehicle_id(self):
        return (self.db.catalog or {}).get('vehicle_id')

    @property
    def domain(self):
        specs = self.db.specs or {}
        return specs.get('domain_slug') or specs.get('domain')

    @property
    def vehicle_type(self):
        specs = self.db.specs or {}
        return specs.get('vehicle_type_slug') or specs.get('vehicle_type')

    @property
    def crew_required(self):
        return (self.db.specs or {}).get('crew_min')

    @property
    def total_price(self):
        return (self.db.economy or {}).get('total_price_cr')

    @property
    def hp(self):
        return (self.db.combat or {}).get('hp')

    def is_spaceworthy(self):
        return (self.domain or '').lower() == 'space'

    def get_vehicle_summary(self):
        specs = self.db.specs or {}
        economy = self.db.economy or {}
        combat = self.db.combat or {}
        is_autonomous = (
            hasattr(self, "tags")
            and self.tags.has("autonomous_hauler", category="mining")
        )
        base = (
            f"{self.key} "
            f"[{specs.get('domain', specs.get('domain_slug', 'Unknown'))} / {specs.get('vehicle_type', specs.get('vehicle_type_slug', 'Unknown'))}]"
        )
        if is_autonomous:
            return base
        return (
            f"{base} | "
            f"crew {specs.get('crew_min', '?')}-{specs.get('crew_std', '?')} | "
            f"hp {combat.get('hp', '?')} | "
            f"price {economy.get('total_price_cr', economy.get('base_price_cr', '?'))} cr"
        )

    def get_market_price(self, location=None, market_type='normal', transaction_type='buy', standing='neutral'):
        return economy_get_price(
            self,
            location=location,
            market_type=market_type,
            transaction_type=transaction_type,
            standing=standing,
        )

    # -----------------------------
    # Access / ownership helpers
    # -----------------------------

    def is_owner(self, obj):
        owner = self.db.owner
        if not owner or not obj:
            return False
        return owner == obj or getattr(owner, 'id', None) == getattr(obj, 'id', None)

    def is_allowed_boarder(self, obj):
        if self.is_owner(obj):
            return True
        allowed = self.db.allowed_boarders or []
        obj_id = getattr(obj, 'id', None)
        for entry in allowed:
            if entry == obj or entry == obj_id:
                return True
            if hasattr(entry, 'id') and entry.id == obj_id:
                return True
        return False

    def can_board(self, obj):
        if not obj:
            return False, 'No boarder was specified.'
        if not self.access(obj, 'enter'):
            return False, 'You cannot enter that vehicle.'
        if not self.location:
            return False, 'That vehicle is not currently deployed anywhere.'
        if obj.location != self.location:
            return False, 'You need to be next to the vehicle to board it.'
        if not self.is_allowed_boarder(obj):
            return False, 'You do not have permission to board this vehicle.'
        return True, None

    def can_pilot(self, obj):
        if not obj:
            return False, 'No pilot was specified.'
        if obj.location != self:
            return False, 'You must be inside the vehicle to pilot it.'
        if not self.is_owner(obj):
            return False, 'Only the owner can pilot this vehicle right now.'
        return True, None

    def can_travel(self, obj, destination):
        ok, reason = self.can_pilot(obj)
        if not ok:
            return ok, reason
        if not destination:
            return False, 'No destination was specified.'
        if destination == self:
            return False, 'You cannot travel into the vehicle itself.'
        fuel = self.db.fuel if isinstance(self.db.fuel, (int, float)) else 100
        if fuel <= 0:
            return False, 'This vehicle is out of fuel.'
        return True, None

    # -----------------------------
    # Interior / exterior helpers
    # -----------------------------

    def get_exterior_location(self):
        return self.location or self.db.exterior_location

    def get_interior_appearance(self, looker=None):
        occupants = [obj.key for obj in self.contents if obj != looker]
        occupants_text = ', '.join(occupants) if occupants else 'No one else is aboard.'
        pilot = self.db.pilot.key if self.db.pilot else 'No active pilot'
        exterior = self.location.key if self.location else 'Unknown exterior location'
        return (
            f'|w{self.key} Interior|n\n'
            f'{self.get_vehicle_summary()}\n'
            f'Pilot: {pilot}\n'
            f'Exterior location: {exterior}\n'
            f'Occupants: {occupants_text}'
        )

    def get_status_report(self, looker=None):
        exterior = self.location.key if self.location else 'Nowhere'
        pilot = self.db.pilot.key if self.db.pilot else 'none'
        owner = self.db.owner.key if self.db.owner else 'unassigned'
        fuel = self.db.fuel if self.db.fuel is not None else '?'
        max_fuel = self.db.max_fuel if self.db.max_fuel is not None else '?'
        occupants = ', '.join(obj.key for obj in self.contents) or 'none'
        return (
            f'|wVehicle Status|n\n'
            f'Name: {self.key}\n'
            f'Owner: {owner}\n'
            f'Pilot: {pilot}\n'
            f'State: {self.db.state or "docked"}\n'
            f'Exterior location: {exterior}\n'
            f'Fuel: {fuel}/{max_fuel}\n'
            f'Occupants: {occupants}\n'
            f'Summary: {self.get_vehicle_summary()}'
        )

    # -----------------------------
    # Runtime hooks
    # -----------------------------

    def at_board(self, boarder, old_location=None):
        self.db.last_boarded_by = boarder.key if boarder else None
        self.db.exterior_location = old_location or self.location

    def at_disembark(self, boarder, new_location=None):
        self.db.last_disembarked_by = boarder.key if boarder else None
        if new_location:
            self.db.exterior_location = new_location

    def at_travel(self, pilot, origin=None, destination=None):
        self.db.state = 'docked'
        self.db.last_travel = {
            'pilot': pilot.key if pilot else None,
            'origin': origin.key if origin else None,
            'destination': destination.key if destination else None,
        }
        fuel = self.db.fuel if isinstance(self.db.fuel, (int, float)) else 100
        self.db.fuel = max(0, fuel - 1)
        self.db.exterior_location = destination or self.location

    # -----------------------------
    # Cargo hold helpers
    # -----------------------------

    def cargo_total_mass(self):
        """Return total tonnes currently loaded."""
        return round(sum(float(v) for v in (self.db.cargo or {}).values()), 2)

    def cargo_space_available(self):
        cap = float(self.db.cargo_capacity_tons or 0)
        return max(0.0, cap - self.cargo_total_mass())

    def load_cargo(self, resource_key, tons):
        """
        Load up to `tons` of resource_key.  Returns actual tonnes loaded.
        Raises ValueError if no cargo capacity is configured on this vehicle.
        """
        cap = float(self.db.cargo_capacity_tons or 0)
        if cap <= 0:
            raise ValueError(f"{self.key} has no cargo hold.")
        space = self.cargo_space_available()
        loaded = round(min(float(tons), space), 2)
        if loaded <= 0:
            return 0.0
        cargo = self.db.cargo or {}
        cargo[resource_key] = round(float(cargo.get(resource_key, 0.0)) + loaded, 2)
        self.db.cargo = cargo
        return loaded

    def unload_cargo(self, resource_key, tons):
        """
        Remove up to `tons` of resource_key.  Returns actual tonnes removed.
        """
        cargo = self.db.cargo or {}
        available = float(cargo.get(resource_key, 0.0))
        removed = round(min(available, float(tons)), 2)
        remaining = round(available - removed, 2)
        if remaining <= 0:
            cargo.pop(resource_key, None)
        else:
            cargo[resource_key] = remaining
        self.db.cargo = cargo
        return removed

    def unload_all_cargo(self):
        """Empty cargo hold; return copy of contents."""
        contents = dict(self.db.cargo or {})
        self.db.cargo = {}
        return contents

    def get_cargo_report(self):
        from typeclasses.mining import RESOURCE_CATALOG
        cap = float(self.db.cargo_capacity_tons or 0)
        cargo = self.db.cargo or {}
        used = self.cargo_total_mass()
        if cap <= 0:
            return f"|w{self.key}|n has no cargo hold configured."
        if not cargo:
            return f"|w{self.key} Cargo Hold|n — empty  [{used:.1f}/{cap:.0f} t]"
        pct = int(used / cap * 100) if cap else 0
        cap_color = "|g" if pct < 70 else "|y" if pct < 90 else "|r"
        lines = [f"|w{self.key} Cargo Hold|n  [{cap_color}{used:.1f}/{cap:.0f} t  {pct}%|n]"]
        for key in sorted(cargo):
            tons = float(cargo[key])
            info = RESOURCE_CATALOG.get(key, {})
            name = info.get("name", key)
            lines.append(f"  {name:<28} {tons:>8.2f} t")
        return "\n".join(lines)

    def return_appearance(self, looker, **kwargs):
        base = super().return_appearance(looker, **kwargs)
        summary = self.get_vehicle_summary()
        if looker and looker.location == self:
            return f"{base}\n\n|wVehicle Summary:|n {summary}\n\n{self.get_interior_appearance(looker)}"
        return f"{base}\n\n|wVehicle Summary:|n {summary}"


class SurfaceVehicle(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = 'surface_vehicle'


class Watercraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = 'watercraft'


class Aircraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = 'aircraft'


class Spacecraft(Vehicle):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = 'spacecraft'

    def is_spaceworthy(self):
        return True


class Hauler(Vehicle):
    """Autonomous ore hauler for mine-to-refinery routes."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.vehicle_kind = 'hauler'
