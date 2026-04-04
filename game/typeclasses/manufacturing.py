"""
Manufacturing — Phase 2–3.

Workshop objects live on a PropertyHolding (sibling to PropertyStructure).
Recipes consume refined keys from REFINING_RECIPES outputs; products use
MANUFACTURED_CATALOG for valuation and commodity_demand registration.

Phase 3: catalog/recipes load from ``world/data/manufacturing.d/*.json``;
ManufacturingEngine ticks workshops via ``db.registry`` (holding id → workshop ids).
"""

from __future__ import annotations

from evennia import GLOBAL_SCRIPTS, create_object, create_script, search_object, search_script, search_tag
from evennia.objects.objects import DefaultObject
from evennia.utils import logger

from typeclasses.objects import ObjectParent
from typeclasses.refining import REFINING_RECIPES
from typeclasses.scripts import Script
from world.manufacturing_loader import (
    assert_manufacturing_recipes_use_refined_keys,
    assert_salvage_recipes_valid,
    load_manufacturing_tables,
)

_MANU_CAT, _MANU_REC, _MANU_ERR = load_manufacturing_tables()
assert not _MANU_ERR, "manufacturing data: " + "; ".join(_MANU_ERR)
assert set(_MANU_CAT) == set(_MANU_REC), "manufacturing catalog/recipe id mismatch"
assert_manufacturing_recipes_use_refined_keys(_MANU_CAT, _MANU_REC)
assert_salvage_recipes_valid(_MANU_CAT, _MANU_REC)

MANUFACTURED_CATALOG = _MANU_CAT
MANUFACTURING_RECIPES = _MANU_REC

WORKSHOP_TAG = "workshop"
WORKSHOP_TAG_CATEGORY = "industry"

WORKSHOP_BLUEPRINT_IDS = frozenset({"fab_bay_mk1", "assembly_cell"})

BLUEPRINT_STATION_KIND = {
    "fab_bay_mk1": "fabrication_bay",
    "assembly_cell": "machine_shop",
}


def job_queue_for_json(job_queue):
    """
    Plain list[dict] for Django JsonResponse / JSON APIs.

    db.job_queue entries are often Evennia _SaverDict; json.dumps rejects those.
    """
    out = []
    for row in job_queue or []:
        d = dict(row) if row is not None else {}
        out.append(
            {
                "ownerId": int(d.get("owner_id", 0)),
                "recipeKey": str(d.get("recipe_key", "")),
                "runs": int(d.get("runs", 0)),
            }
        )
    return out


def serialize_workshops_for_web(holding):
    """CamelCase workshop rows for property holding JSON (Phase 4)."""
    out = []
    for obj in holding.contents:
        if not obj.is_typeclass(Workshop, exact=False):
            continue
        out.append(
            {
                "workshopId": int(obj.id),
                "key": obj.key,
                "blueprintId": str(obj.db.blueprint_id or ""),
                "stationKind": str(obj.db.station_kind or ""),
                "jobQueue": job_queue_for_json(obj.db.job_queue),
                "inputInventory": dict(obj.db.input_inventory or {}),
                "outputInventory": dict(obj.db.output_inventory or {}),
            }
        )
    return out


def serialize_manufacturing_recipes_for_web():
    """Stable recipe ids for web dropdowns (filter by workshop stationKind on the client)."""
    return [
        {
            "id": rid,
            "name": row["name"],
            "stationKind": row["station_kind"],
        }
        for rid, row in sorted(MANUFACTURING_RECIPES.items(), key=lambda x: x[0])
    ]


def serialize_manufactured_catalog_for_web():
    """Labels for collect dropdown (client filters to workshop outputInventory keys)."""
    return [
        {"id": pk, "name": row["name"]}
        for pk, row in sorted(MANUFACTURED_CATALOG.items(), key=lambda x: x[0])
    ]


def _record_manufactured_supply(product_key: str, units: float) -> None:
    from typeclasses.commodity_demand import get_commodity_demand_engine

    eng = get_commodity_demand_engine(create_missing=False)
    if eng:
        eng.record_supply(product_key, float(units))


def _record_refined_supply(commodity_key: str, units: float) -> None:
    from typeclasses.commodity_demand import get_commodity_demand_engine

    eng = get_commodity_demand_engine(create_missing=False)
    if eng:
        eng.record_supply(str(commodity_key), float(units))


class Workshop(ObjectParent, DefaultObject):
    """
    Fabrication unit bound to one PropertyStructure blueprint install.

    db.bound_structure_id  int   PropertyStructure.id
    db.blueprint_id        str   same as PropertyStructure.db.blueprint_id
    db.station_kind        str   fabrication_bay | machine_shop
    db.holding_id          int   PropertyHolding.id
    """

    def at_object_creation(self):
        self.db.bound_structure_id = None
        self.db.blueprint_id = None
        self.db.station_kind = "fabrication_bay"
        self.db.holding_id = None
        self.db.input_inventory = {}
        self.db.output_inventory = {}
        self.db.job_queue = []
        self.tags.add(WORKSHOP_TAG, category=WORKSHOP_TAG_CATEGORY)
        self.locks.add("control:title_owner();get:false();drop:false()")

    def at_object_delete(self):
        eng = get_manufacturing_engine(create_missing=False)
        if eng:
            hid = int(self.db.holding_id or 0)
            if hid:
                eng.unregister_workshop(hid, int(self.id))
        super().at_object_delete()

    def at_post_move(self, source_location, move_type="move", **kwargs):
        super().at_post_move(source_location, move_type=move_type, **kwargs)
        loc = self.location
        self.db.holding_id = int(loc.id) if loc else 0
        eng = get_manufacturing_engine(create_missing=False)
        if not eng:
            return
        if source_location:
            eng.unregister_workshop(int(source_location.id), int(self.id))
        if loc:
            eng.register_workshop(int(loc.id), int(self.id))

    def feed(self, product_key: str, units: float) -> float:
        """Add refined product units (REFINING_RECIPES keys) to workshop input."""
        if product_key not in REFINING_RECIPES:
            return 0.0
        units = round(float(units), 2)
        if units <= 0:
            return 0.0
        inv = self.db.input_inventory or {}
        inv[product_key] = round(float(inv.get(product_key, 0.0)) + units, 2)
        self.db.input_inventory = inv
        return units

    def feed_manufactured(self, product_key: str, units: float) -> float:
        """Add finished manufactured goods for salvage jobs."""
        pk = str(product_key).strip()
        if pk not in MANUFACTURED_CATALOG:
            return 0.0
        units = round(float(units), 2)
        if units <= 0:
            return 0.0
        inv = self.db.input_inventory or {}
        inv[pk] = round(float(inv.get(pk, 0.0)) + units, 2)
        self.db.input_inventory = inv
        return units

    def can_run(self, recipe_key: str, runs: int = 1) -> int:
        recipe = MANUFACTURING_RECIPES.get(recipe_key)
        if not recipe or recipe["station_kind"] != self.db.station_kind:
            return 0
        possible = int(runs)
        inv = self.db.input_inventory or {}
        kind = str(recipe.get("recipe_kind") or "fabricate").lower()
        if kind == "salvage":
            for key, required in recipe["inputs"].items():
                if key not in MANUFACTURED_CATALOG:
                    return 0
                req = float(required)
                if req <= 0:
                    return 0
                possible = min(possible, int(float(inv.get(key, 0.0)) / req))
            return max(0, possible)
        for key, required in recipe["inputs"].items():
            if key not in REFINING_RECIPES:
                return 0
            possible = min(possible, int(float(inv.get(key, 0.0)) / float(required)))
        return max(0, possible)

    def queue_job(self, caller, recipe_key: str, runs: int = 1) -> dict:
        if not self.access(caller, "control", default=False):
            raise PermissionError("Not your workshop.")
        recipe = MANUFACTURING_RECIPES.get(recipe_key)
        if not recipe:
            raise ValueError("Unknown manufacturing recipe.")
        if recipe["station_kind"] != self.db.station_kind:
            raise ValueError("Wrong station for recipe.")
        row = {
            "owner_id": int(caller.id),
            "recipe_key": recipe_key,
            "runs": int(runs),
        }
        q = list(self.db.job_queue or [])
        q.append(row)
        self.db.job_queue = q
        loc = self.location
        assert loc, "Workshop has no location."
        eng = get_manufacturing_engine(create_missing=True)
        eng.register_workshop(int(loc.id), int(self.id))
        return row

    def process_next_job(self) -> tuple[bool, str]:
        q = list(self.db.job_queue or [])
        if not q:
            return False, "Queue empty."
        job = q[0]
        recipe_key = job["recipe_key"]
        runs = int(job["runs"])
        recipe = MANUFACTURING_RECIPES[recipe_key]
        possible = self.can_run(recipe_key, runs)
        if possible <= 0:
            return False, "Insufficient inputs for queued job."

        inv = dict(self.db.input_inventory or {})
        kind = str(recipe.get("recipe_kind") or "fabricate").lower()

        if kind == "salvage":
            for key, required in recipe["inputs"].items():
                consumed = round(float(required) * possible, 2)
                remaining = round(float(inv.get(key, 0.0)) - consumed, 2)
                if remaining <= 0:
                    inv.pop(key, None)
                else:
                    inv[key] = remaining
            self.db.input_inventory = inv

            out = dict(self.db.output_inventory or {})
            outputs = recipe.get("outputs") or {}
            for out_key, per_run in outputs.items():
                add_u = round(float(per_run) * float(possible), 2)
                if add_u <= 0:
                    continue
                out[out_key] = round(float(out.get(out_key, 0.0)) + add_u, 2)
                _record_refined_supply(str(out_key), add_u)
            self.db.output_inventory = out
            msg = f"Salvaged {possible} run(s): {recipe['name']}."
        else:
            for key, required in recipe["inputs"].items():
                consumed = round(float(required) * possible, 2)
                remaining = round(float(inv.get(key, 0.0)) - consumed, 2)
                if remaining <= 0:
                    inv.pop(key, None)
                else:
                    inv[key] = remaining
            self.db.input_inventory = inv

            out = dict(self.db.output_inventory or {})
            units = int(recipe["output_units"]) * possible
            pk = recipe_key
            out[pk] = round(float(out.get(pk, 0.0)) + float(units), 2)
            self.db.output_inventory = out
            _record_manufactured_supply(pk, float(units))
            msg = f"Produced {units} x {recipe['name']}."

        remaining_runs = int(runs) - int(possible)
        if remaining_runs <= 0:
            q.pop(0)
        else:
            job["runs"] = remaining_runs
            q[0] = job
        self.db.job_queue = q

        return True, msg

    def collect_manufactured(self, caller, product_key: str, units: float | None):
        if not self.access(caller, "control", default=False):
            raise PermissionError("Not your workshop.")
        from typeclasses.commodity_demand import get_commodity_demand_engine
        from typeclasses.economy import grant_character_credits

        pk = str(product_key).strip()
        cat = MANUFACTURED_CATALOG[pk]
        out = dict(self.db.output_inventory or {})
        available = float(out[pk])
        take = available if units is None else min(float(units), available)
        assert take > 0
        remaining = round(available - take, 2)
        if remaining <= 0:
            out.pop(pk)
        else:
            out[pk] = remaining
        self.db.output_inventory = out

        base = int(cat["base_value_cr"])
        eng = get_commodity_demand_engine(create_missing=True)
        mult = eng.get_market_multiplier(pk)
        value = int(take * base * mult)
        eng.record_demand(pk, float(take))
        grant_character_credits(caller, value, memo=f"Manufactured sale {pk}")
        return take, value

    def collect_refined(self, caller, commodity_key: str, units: float | None):
        """Sell refined units held in workshop output (e.g. from salvage)."""
        if not self.access(caller, "control", default=False):
            raise PermissionError("Not your workshop.")
        ck = str(commodity_key).strip()
        if ck not in REFINING_RECIPES:
            raise ValueError("Not a refined commodity key.")
        from typeclasses.commodity_demand import get_commodity_demand_engine
        from typeclasses.economy import grant_character_credits
        from typeclasses.mining import get_commodity_bid

        out = dict(self.db.output_inventory or {})
        available = float(out.get(ck, 0.0))
        if available <= 0:
            raise ValueError("Nothing to collect.")
        take = available if units is None else min(float(units), available)
        take = round(take, 2)
        if take <= 0:
            raise ValueError("Nothing to collect.")
        remaining = round(available - take, 2)
        if remaining <= 0:
            out.pop(ck, None)
        else:
            out[ck] = remaining
        self.db.output_inventory = out

        bid = float(get_commodity_bid(ck))
        eng = get_commodity_demand_engine(create_missing=True)
        mult = eng.get_market_multiplier(ck)
        value = int(take * bid * mult)
        eng.record_demand(ck, float(take))
        grant_character_credits(caller, value, memo=f"Workshop refined sale {ck}")
        return take, value


def workshop_for_structure(structure):
    for w in search_tag(WORKSHOP_TAG, category=WORKSHOP_TAG_CATEGORY):
        if int(getattr(w.db, "bound_structure_id", 0) or 0) == int(structure.id):
            return w
    return None


def spawn_workshop_for_structure(structure):
    existing = workshop_for_structure(structure)
    if existing:
        return existing
    holding = structure.location
    if not holding:
        return None
    bp = str(structure.db.blueprint_id or "")
    station = BLUEPRINT_STATION_KIND.get(bp, "fabrication_bay")
    w = create_object(
        Workshop,
        key=f"Workshop:{bp}:{structure.id}",
        location=holding,
        home=holding,
    )
    w.db.bound_structure_id = int(structure.id)
    w.db.blueprint_id = bp
    w.db.station_kind = station
    w.db.holding_id = int(holding.id)
    eng = get_manufacturing_engine(create_missing=True)
    eng.register_workshop(int(holding.id), int(w.id))
    return w


def maybe_spawn_workshop_on_install(structure):
    bp = str(structure.db.blueprint_id or "")
    if bp in WORKSHOP_BLUEPRINT_IDS:
        spawn_workshop_for_structure(structure)


MANUFACTURING_ENGINE_INTERVAL = 600
MANUFACTURING_STAGGER_MOD = 4
MANUFACTURING_ENGINE_KEY = "manufacturing_engine"


class ManufacturingEngine(Script):
    def at_script_creation(self):
        self.key = MANUFACTURING_ENGINE_KEY
        self.desc = "Processes workshop job queues."
        self.interval = MANUFACTURING_ENGINE_INTERVAL
        self.persistent = True
        self.start_delay = True
        self.repeats = 0
        self.db.registry = {}

    def register_workshop(self, holding_id: int, workshop_id: int) -> None:
        reg = dict(self.db.registry or {})
        key = str(int(holding_id))
        ids = [int(x) for x in reg.get(key, []) if int(x) != int(workshop_id)]
        ids.append(int(workshop_id))
        reg[key] = ids
        self.db.registry = reg

    def unregister_workshop(self, holding_id: int, workshop_id: int) -> None:
        reg = dict(self.db.registry or {})
        key = str(int(holding_id))
        ids = [int(x) for x in reg.get(key, []) if int(x) != int(workshop_id)]
        if ids:
            reg[key] = ids
        else:
            reg.pop(key, None)
        self.db.registry = reg

    def at_repeat(self, **kwargs):
        self.ndb.stagger_tick = int(self.ndb.stagger_tick or 0) + 1
        tick = self.ndb.stagger_tick
        reg = dict(self.db.registry or {})
        for hid_str, wids in list(reg.items()):
            if int(hid_str) % MANUFACTURING_STAGGER_MOD != tick % MANUFACTURING_STAGGER_MOD:
                continue
            alive = []
            for wid in wids:
                found = search_object(f"#{wid}")
                if not found:
                    continue
                ws = found[0]
                while ws.db.job_queue:
                    ok, msg = ws.process_next_job()
                    logger.log_info(f"[manufacturing_engine] {ws.key}: {msg}")
                    if not ok:
                        break
                if ws.db.job_queue:
                    alive.append(int(wid))
            if alive:
                reg[hid_str] = alive
            else:
                reg.pop(hid_str, None)
        self.db.registry = reg


def get_manufacturing_engine(create_missing=True):
    try:
        eng = GLOBAL_SCRIPTS.manufacturing_engine
        if eng:
            return eng
    except Exception:
        pass
    found = search_script(MANUFACTURING_ENGINE_KEY)
    if found:
        return found[0]
    if create_missing:
        return create_script("typeclasses.manufacturing.ManufacturingEngine", key=MANUFACTURING_ENGINE_KEY)
    return None
