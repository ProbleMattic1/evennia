"""
Portable Ore Processor — personal refining equipment.

A PortableProcessor is purchased at Mining Outfitters and stored in
inventory until a player base is available to install it.

Once placed in a base room (future feature), the processor can:
- Accept ore fed from a storage unit or hauler (same as the global plant)
- Run REFINING_RECIPES with an efficiency multiplier (mk-level bonus)
- Have its output collected by the owner

db fields
---------
db.processor_mk       int     1 / 2 / 3 — model tier
db.capacity_tons      float   max input inventory (200 / 500 / 1000 t)
db.efficiency         float   output units multiplier (1.0 / 1.05 / 1.12)
db.input_inventory    dict    {resource_key: tons}  raw ore waiting
db.output_inventory   dict    {product_key: units}  refined output ready
db.owner              obj     character owner
db.is_installed       bool    True when placed in a base room
"""

from evennia.objects.objects import DefaultObject

from typeclasses.commodity_demand import get_commodity_demand_engine

from .objects import ObjectParent
from .mining import RESOURCE_CATALOG
from .refining import REFINING_RECIPES


class PortableProcessor(ObjectParent, DefaultObject):
    """
    A personal ore processor that can be placed in a player base.

    Purchased as a standalone item from Mining Outfitters.
    Stored in inventory until bases are implemented; at that point
    the hauler's refinery_room can be set to the base room containing
    this processor.
    """

    def at_object_creation(self):
        self.db.processor_mk = 1
        self.db.capacity_tons = 200.0
        self.db.efficiency = 1.0
        self.db.input_inventory = {}
        self.db.output_inventory = {}
        self.db.owner = None
        self.db.is_installed = False
        self.tags.add("portable_processor", category="mining")
        self.tags.add("refinery", category="mining")  # so haulers can find it via get_refinery_in_room
        self.locks.add("get:true();drop:true()")

    def _parcel_allows_install(self, char, room):
        """True if room is this character's titled parcel interior."""
        holding = getattr(room.db, "holding_ref", None)
        if not holding or getattr(holding.db, "title_owner", None) != char:
            return False
        if getattr(self.db, "owner", None) not in (None, char):
            return False
        return True

    def at_get(self, getter, **kwargs):
        super().at_get(getter, **kwargs)
        self.db.is_installed = False

    def at_drop(self, dropper, **kwargs):
        super().at_drop(dropper, **kwargs)
        loc = self.location
        if loc and self._parcel_allows_install(dropper, loc):
            self.db.is_installed = True
        else:
            self.db.is_installed = False

    def feed(self, resource_key, tons):
        """Add raw ore to input. Returns actual tons added (capped by remaining capacity)."""
        if resource_key not in RESOURCE_CATALOG:
            return 0.0
        tons = round(float(tons), 2)
        if tons <= 0:
            return 0.0
        inv = self.db.input_inventory or {}
        used = round(sum(float(v) for v in inv.values()), 2)
        cap = float(self.db.capacity_tons or 200.0)
        space = max(0.0, cap - used)
        actual = round(min(tons, space), 2)
        if actual <= 0:
            return 0.0
        inv[resource_key] = round(float(inv.get(resource_key, 0.0)) + actual, 2)
        self.db.input_inventory = inv
        return actual

    def process_recipe(self, recipe_key, batches=1):
        """
        Same contract as typeclasses.refining.Refinery.process_recipe.
        Applies db.efficiency to produced units (portable Mk bonus).
        """
        demand_eng = get_commodity_demand_engine(create_missing=False)
        recipe = REFINING_RECIPES.get(recipe_key)
        if not recipe:
            return 0, f"Unknown recipe '{recipe_key}'."

        batches = max(1, int(batches))
        inv = self.db.input_inventory or {}

        possible = batches
        for res_key, required_per_batch in recipe["inputs"].items():
            available = float(inv.get(res_key, 0.0))
            max_from_this = int(available / float(required_per_batch))
            possible = min(possible, max_from_this)

        if possible <= 0:
            needed = {
                RESOURCE_CATALOG.get(k, {}).get("name", k): v * batches
                for k, v in recipe["inputs"].items()
            }
            return 0, (
                f"Insufficient inputs for {recipe['name']}. "
                f"Need: {', '.join(f'{v}t {k}' for k, v in needed.items())}."
            )

        for res_key, required_per_batch in recipe["inputs"].items():
            consumed = round(float(required_per_batch) * possible, 2)
            remaining = round(float(inv.get(res_key, 0.0)) - consumed, 2)
            if remaining <= 0:
                inv.pop(res_key, None)
            else:
                inv[res_key] = remaining
        self.db.input_inventory = inv

        efficiency = float(self.db.efficiency or 1.0)
        out_inv = self.db.output_inventory or {}
        base_units = recipe.get("output_units", 1) * possible
        units_produced = round(float(base_units) * efficiency, 2)
        out_inv[recipe_key] = round(float(out_inv.get(recipe_key, 0.0)) + units_produced, 2)
        self.db.output_inventory = out_inv

        if demand_eng:
            demand_eng.record_supply(recipe_key, float(units_produced))

        return possible, (
            f"Processed {possible} batch(es) of {recipe['name']}. "
            f"Produced {units_produced} unit(s) (efficiency {efficiency:.2f}x)."
        )

    def collect_product(self, product_key, units=None):
        """Same as Refinery.collect_product — for collectproduct command."""
        out_inv = self.db.output_inventory or {}
        available = float(out_inv.get(product_key, 0.0))
        if available <= 0:
            return 0.0, 0

        if units is None:
            collected = available
        else:
            collected = round(min(float(units), available), 2)

        remaining = round(available - collected, 2)
        if remaining <= 0:
            out_inv.pop(product_key, None)
        else:
            out_inv[product_key] = remaining
        self.db.output_inventory = out_inv

        recipe = REFINING_RECIPES.get(product_key, {})
        value = int(collected * recipe.get("base_value_cr", 0))
        return collected, value

    def process_all(self):
        """
        Run all REFINING_RECIPES until no more batches are possible.
        Applies efficiency multiplier to output units.
        Returns total batches processed.
        """
        efficiency = float(self.db.efficiency or 1.0)
        inv = self.db.input_inventory or {}
        out_inv = self.db.output_inventory or {}
        total_batches = 0

        for recipe_key, recipe in REFINING_RECIPES.items():
            while True:
                possible = None
                for res_key, req in recipe["inputs"].items():
                    avail = float(inv.get(res_key, 0.0))
                    n = int(avail / float(req))
                    possible = n if possible is None else min(possible, n)
                if not possible:
                    break
                for res_key, req in recipe["inputs"].items():
                    consumed = round(float(req) * possible, 2)
                    remaining = round(float(inv.get(res_key, 0.0)) - consumed, 2)
                    if remaining <= 0:
                        inv.pop(res_key, None)
                    else:
                        inv[res_key] = remaining
                units = round(recipe.get("output_units", 1) * possible * efficiency, 2)
                out_inv[recipe_key] = round(float(out_inv.get(recipe_key, 0.0)) + units, 2)
                total_batches += possible

        self.db.input_inventory = inv
        self.db.output_inventory = out_inv
        return total_batches

    def collect_output(self, product_key=None):
        """
        Collect output. If product_key is None, collect all.
        Returns (collected_dict, total_base_value_cr).
        """
        out_inv = self.db.output_inventory or {}
        if not out_inv:
            return {}, 0

        if product_key:
            if product_key not in out_inv:
                return {}, 0
            collected = {product_key: out_inv.pop(product_key)}
        else:
            collected = dict(out_inv)
            out_inv.clear()

        self.db.output_inventory = out_inv
        total = 0
        for key, units in collected.items():
            recipe = REFINING_RECIPES.get(key, {})
            total += int(units * recipe.get("base_value_cr", 0))
        return collected, total

    def get_status_report(self):
        mk = int(self.db.processor_mk or 1)
        cap = float(self.db.capacity_tons or 200.0)
        eff = float(self.db.efficiency or 1.0)
        installed = "installed" if self.db.is_installed else "in inventory"
        lines = [
            f"|wOre Processor Mk {mk}|n — {installed}",
            f"  Capacity: {cap:.0f} t   Efficiency: {eff:.2f}x",
        ]
        inv = self.db.input_inventory or {}
        if inv:
            lines.append("  Input:")
            for key, tons in sorted(inv.items()):
                name = RESOURCE_CATALOG.get(key, {}).get("name", key)
                lines.append(f"    {name:<28} {float(tons):>8.2f} t")
        else:
            lines.append("  Input: empty")
        out_inv = self.db.output_inventory or {}
        if out_inv:
            lines.append("  Output:")
            total_val = 0
            for key, units in sorted(out_inv.items()):
                recipe = REFINING_RECIPES.get(key, {})
                name = recipe.get("name", key)
                val = int(units * recipe.get("base_value_cr", 0))
                total_val += val
                lines.append(f"    {name:<28} {float(units):>8.2f} units   |y{val:>10,}|n cr")
            lines.append(f"    {'Total value':<28} {'':>8}        |y{total_val:>10,}|n cr")
        else:
            lines.append("  Output: empty")
        return "\n".join(lines)
