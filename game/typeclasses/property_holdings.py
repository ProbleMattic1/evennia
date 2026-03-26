"""
One PropertyHolding per claimed PropertyLot. Lives on the lot (e.g. archive room).

Deed references lot; lot.db.holding_ref points here.
"""

from evennia.utils import logger

from .objects import Object

PROPERTY_HOLDING_TAG = "property_holding"
PROPERTY_HOLDING_CATEGORY = "realty"


class PropertyHolding(Object):
    """
    Runtime state for a titled parcel: lifecycle, economy counters, permissions.
    Structures are child objects (PropertyStructure).
    """

    def at_object_creation(self):
        self.tags.add(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY)
        self.db.lot_ref = None
        self.db.title_owner = None
        self.db.development_state = "idle"
        self.db.size_units = 1
        self.db.zone = "residential"
        self.db.lot_tier = 1
        self.db.operation = {
            "kind": None,
            "level": 0,
            "next_tick_at": None,
            "paused": False,
            "extra_slots": 0,
        }
        self.db.ledger = {
            "credits_accrued": 0,
            "last_tick_iso": None,
        }
        self.db.access = {
            "managers": [],
            "tenants": [],
        }
        self.db.place_state = {
            "mode": "void",
            "root_room_id": None,
            "exit_from_hub_id": None,
        }
        self.db.staff = {"roles": {}}
        self.db.event_queue = []
        self.db.ops_stale_owner_alerted = False
        self.locks.add("control:perm(Admin)")

    def bind_lot(self, lot, owner):
        self.db.lot_ref = lot
        self.db.size_units = int(lot.db.size_units or 1)
        self.db.zone = (lot.db.zone or "residential").lower()
        self.db.lot_tier = int(lot.db.lot_tier or 1)
        self.move_to(lot, quiet=True)
        self.home = lot
        self.set_title_owner(owner)

    def set_title_owner(self, owner):
        self.db.title_owner = owner
        self.db.ops_stale_owner_alerted = False
        if owner:
            self.locks.add(
                "control:perm(Admin) or id({})".format(owner.dbid)
            )
        else:
            self.locks.add("control:perm(Admin)")

    def structure_slots_total(self):
        base = int(self.db.size_units or 1)
        return base + int(self.db.operation.get("extra_slots") or 0)

    def structures(self):
        out = []
        for obj in self.contents:
            if obj.tags.has("property_structure", category=PROPERTY_HOLDING_CATEGORY):
                out.append(obj)
        return out

    def used_structure_slots(self):
        return sum(int(getattr(obj.db, "slot_weight", 1) or 1) for obj in self.structures())

    def can_install(self, slot_weight):
        return self.used_structure_slots() + int(slot_weight) <= self.structure_slots_total()

    def tick_operation(self, now):
        from typeclasses.property_operation_handlers import dispatch_property_tick

        msg = dispatch_property_tick(self, now)
        if msg:
            logger.log_info(f"[property_ops] {self.key}: {msg}")
        return msg
