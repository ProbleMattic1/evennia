"""
Refining system — Pass 3.

Components
----------
REFINING_RECIPES   dict of output_key -> recipe definition
Refinery           Object typeclass; accepts raw ore, produces refined materials

A Refinery has two inventory dicts:
    db.input_inventory   {resource_key: float tons}  — raw ore fed in
    db.output_inventory  {product_key: float units}  — refined products ready

Workers (or commands) call refinery.process_recipe(recipe_key, batches) to
convert inputs to outputs at the defined ratio.

Economy integration:
    Refined products have a base_value_cr (per unit) stored in the recipe.
    The collectproduct command in commands/refining.py sells via grant_character_credits
    (base value only in Pass 3; Pass 4 can add market modifiers).

Transport integration:
    Vehicle cargo can be transferred to db.input_inventory via CmdFeedRefinery
    in commands/refining.py.  Output is collected with CmdCollectProduct.
"""

from evennia.objects.objects import DefaultObject

from .objects import ObjectParent
from typeclasses.mining import RESOURCE_CATALOG


# Fee charged by the global Processing Plant when a miner collects their
# processed output.  Applied to gross refined value at collect time.
PROCESSING_FEE_RATE = 0.10  # 10 %

# ---------------------------------------------------------------------------
# Refining recipes
# ---------------------------------------------------------------------------

REFINING_RECIPES = {
    # Metals
    "refined_iron": {
        "name": "Refined Iron",
        "desc": "Smelted iron ingots ready for fabrication.",
        "inputs": {"iron_ore": 4.0},         # 4 t ore → 1 unit refined
        "output_units": 1,
        "base_value_cr": 520,
        "category": "refined_metal",
    },
    "refined_copper": {
        "name": "Refined Copper",
        "desc": "Pure copper cathodes for electrical components.",
        "inputs": {"copper_ore": 4.5},
        "output_units": 1,
        "base_value_cr": 900,
        "category": "refined_metal",
    },
    "refined_nickel": {
        "name": "Refined Nickel",
        "desc": "High-purity nickel pellets for alloy production.",
        "inputs": {"nickel_ore": 5.0},
        "output_units": 1,
        "base_value_cr": 1400,
        "category": "refined_metal",
    },
    "refined_titanium": {
        "name": "Refined Titanium",
        "desc": "Titanium sponge and billets for aerospace use.",
        "inputs": {"titanium_ore": 6.0},
        "output_units": 1,
        "base_value_cr": 3800,
        "category": "refined_metal",
    },
    "refined_cobalt": {
        "name": "Refined Cobalt",
        "desc": "Cobalt powder and plates for battery technology.",
        "inputs": {"cobalt_ore": 5.5},
        "output_units": 1,
        "base_value_cr": 4200,
        "category": "refined_metal",
    },
    "rare_earth_oxide": {
        "name": "Rare-Earth Oxide Mix",
        "desc": "Separated rare-earth oxides for high-tech manufacturing.",
        "inputs": {"rare_earth_concentrate": 3.0},
        "output_units": 1,
        "base_value_cr": 3800,
        "category": "refined_metal",
    },
    "platinum_bar": {
        "name": "Platinum Bar",
        "desc": "Precious platinum-group metal bar, assay-certified.",
        "inputs": {"platinum_group_ore": 8.0},
        "output_units": 1,
        "base_value_cr": 32000,
        "category": "precious_metal",
    },
    # Gem products
    "cut_opal": {
        "name": "Cut Opal",
        "desc": "Polished play-of-color opal, gem quality.",
        "inputs": {"opal_seam": 2.0},
        "output_units": 1,
        "base_value_cr": 4500,
        "category": "cut_gem",
    },
    "cut_corundum": {
        "name": "Cut Corundum",
        "desc": "Faceted sapphire/ruby corundum, jeweller's grade.",
        "inputs": {"corundum_matrix": 2.5},
        "output_units": 1,
        "base_value_cr": 6800,
        "category": "cut_gem",
    },
    "cut_emerald": {
        "name": "Cut Emerald",
        "desc": "Precision-cut emerald beryl, collector's quality.",
        "inputs": {"emerald_beryl_ore": 3.0},
        "output_units": 1,
        "base_value_cr": 9200,
        "category": "cut_gem",
    },
    "cut_diamond": {
        "name": "Cut Diamond",
        "desc": "Brilliant-cut natural diamond, certified.",
        "inputs": {"diamond_kimberlite": 4.0},
        "output_units": 1,
        "base_value_cr": 18000,
        "category": "cut_gem",
    },
    # Alloys
    "steel_alloy": {
        "name": "Steel Alloy",
        "desc": "Carbon steel alloy billet for structural applications.",
        "inputs": {"iron_ore": 3.0, "lead_zinc_ore": 1.0},
        "output_units": 1,
        "base_value_cr": 680,
        "category": "alloy",
    },
    "titanium_alloy": {
        "name": "Titanium-Aluminum Alloy",
        "desc": "Lightweight structural alloy for aerospace frames.",
        "inputs": {"titanium_ore": 3.0, "aluminum_ore": 2.0},
        "output_units": 1,
        "base_value_cr": 4800,
        "category": "alloy",
    },
}


# ---------------------------------------------------------------------------
# Refinery typeclass
# ---------------------------------------------------------------------------

class Refinery(ObjectParent, DefaultObject):
    """
    An ore processing facility.

    db.input_inventory   {resource_key: float tons}  raw ore in
    db.output_inventory  {product_key: float units}  refined goods out
    db.owner             character ref (or None for public/station facility)

    Players feed raw ore (from storage or vehicle cargo) into input_inventory,
    then call process_recipe() to convert it.  Output accumulates in
    output_inventory until collected.
    """

    def at_object_creation(self):
        self.db.is_refinery = True
        self.db.owner = None
        self.db.input_inventory = {}
        self.db.output_inventory = {}
        # Per-miner queues for "process" delivery mode at the global plant.
        # keyed by str(character.id).
        self.db.miner_ore_queue = {}   # {owner_id: {resource_key: tons}}
        self.db.miner_output = {}      # {owner_id: {product_key: units}}
        self.tags.add("refinery", category="mining")
        self.locks.add("get:false()")

    # ------------------------------------------------------------------

    def feed(self, resource_key, tons):
        """Add raw ore to input inventory. Returns actual tons added."""
        if resource_key not in RESOURCE_CATALOG:
            return 0.0
        tons = round(float(tons), 2)
        if tons <= 0:
            return 0.0
        inv = self.db.input_inventory or {}
        inv[resource_key] = round(float(inv.get(resource_key, 0.0)) + tons, 2)
        self.db.input_inventory = inv
        return tons

    def process_recipe(self, recipe_key, batches=1):
        """
        Process `batches` runs of recipe_key.

        Returns (batches_processed, message).
        Partial processing: runs as many full batches as inputs allow.
        """
        recipe = REFINING_RECIPES.get(recipe_key)
        if not recipe:
            return 0, f"Unknown recipe '{recipe_key}'."

        batches = max(1, int(batches))
        inv = self.db.input_inventory or {}

        # How many full batches can we run?
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

        # Consume inputs
        for res_key, required_per_batch in recipe["inputs"].items():
            consumed = round(float(required_per_batch) * possible, 2)
            remaining = round(float(inv.get(res_key, 0.0)) - consumed, 2)
            if remaining <= 0:
                inv.pop(res_key, None)
            else:
                inv[res_key] = remaining
        self.db.input_inventory = inv

        # Produce outputs
        out_inv = self.db.output_inventory or {}
        units_produced = recipe.get("output_units", 1) * possible
        out_inv[recipe_key] = round(float(out_inv.get(recipe_key, 0.0)) + units_produced, 2)
        self.db.output_inventory = out_inv

        return possible, (
            f"Processed {possible} batch(es) of {recipe['name']}. "
            f"Produced {units_produced} unit(s)."
        )

    def collect_product(self, product_key, units=None):
        """
        Remove product(s) from output inventory.
        Returns (units_collected, base_value_cr).
        """
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

    def get_miner_output(self, owner_id):
        """Return {product_key: units} for the given owner (str id). Empty dict if none."""
        return dict((self.db.miner_output or {}).get(str(owner_id), {}))

    def get_miner_ore_queued_tons(self, owner_id):
        """Return total tons of ore queued for this miner."""
        q = (self.db.miner_ore_queue or {}).get(str(owner_id), {})
        return round(sum(float(v) for v in q.values()), 2)

    def get_miner_output_value(self, owner_id):
        """Return total credit value of miner's output at base recipe prices."""
        total = 0
        for key, units in self.get_miner_output(owner_id).items():
            recipe = REFINING_RECIPES.get(key, {})
            total += int(units * recipe.get("base_value_cr", 0))
        return total

    def collect_miner_output(self, owner_id, fee_rate=0.0):
        """
        Remove and return all output for a miner.
        Returns (products_dict, gross_value_cr, fee_cr).
        """
        owner_id = str(owner_id)
        output = dict(self.db.miner_output or {})
        miner_out = dict(output.pop(owner_id, {}))
        if not miner_out:
            return {}, 0, 0
        self.db.miner_output = output
        gross = 0
        for key, units in miner_out.items():
            recipe = REFINING_RECIPES.get(key, {})
            gross += int(units * recipe.get("base_value_cr", 0))
        fee = int(gross * fee_rate)
        return miner_out, gross, fee

    def get_status_report(self):
        owner_str = self.db.owner.key if self.db.owner else "public facility"
        lines = [f"|wRefinery: {self.key}|n", f"  Owner: {owner_str}"]

        # Input inventory
        inv_in = self.db.input_inventory or {}
        if inv_in:
            lines.append("  Raw inputs:")
            for key in sorted(inv_in):
                tons = float(inv_in[key])
                name = RESOURCE_CATALOG.get(key, {}).get("name", key)
                lines.append(f"    {name:<28} {tons:>8.2f} t")
        else:
            lines.append("  Raw inputs  : empty")

        # Output inventory
        inv_out = self.db.output_inventory or {}
        if inv_out:
            lines.append("  Refined outputs:")
            total_value = 0
            for key in sorted(inv_out):
                units = float(inv_out[key])
                recipe = REFINING_RECIPES.get(key, {})
                name = recipe.get("name", key)
                value = int(units * recipe.get("base_value_cr", 0))
                total_value += value
                lines.append(f"    {name:<28} {units:>8.2f} units   |y{value:>10,}|n cr")
            lines.append(f"    {'Total output value':<28} {'':>8}        |y{total_value:>10,}|n cr")
        else:
            lines.append("  Refined outputs: empty")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# RefineryEngine — global automation script
# ---------------------------------------------------------------------------

REFINERY_ENGINE_INTERVAL = 1800   # 30 min tick


def _process_miner_queues(refinery):
    """
    Process per-miner ore queues and write output to miner_output.
    Called each RefineryEngine tick for the global plant.
    """
    queues = dict(refinery.db.miner_ore_queue or {})
    output = dict(refinery.db.miner_output or {})
    changed = False

    for owner_id in list(queues.keys()):
        ore_inv = dict(queues[owner_id])
        if not ore_inv:
            del queues[owner_id]
            changed = True
            continue
        miner_out = dict(output.get(owner_id, {}))

        for recipe_key, recipe in REFINING_RECIPES.items():
            while True:
                possible = None
                for res_key, req in recipe["inputs"].items():
                    avail = float(ore_inv.get(res_key, 0.0))
                    n = int(avail / float(req))
                    possible = n if possible is None else min(possible, n)
                if not possible:
                    break
                for res_key, req in recipe["inputs"].items():
                    consumed = round(float(req) * possible, 2)
                    remaining = round(float(ore_inv.get(res_key, 0.0)) - consumed, 2)
                    if remaining <= 0:
                        ore_inv.pop(res_key, None)
                    else:
                        ore_inv[res_key] = remaining
                units = recipe.get("output_units", 1) * possible
                miner_out[recipe_key] = round(
                    float(miner_out.get(recipe_key, 0.0)) + units, 2
                )
                changed = True

        if ore_inv:
            queues[owner_id] = ore_inv
        else:
            queues.pop(owner_id, None)
        if miner_out:
            output[owner_id] = miner_out

    if changed:
        refinery.db.miner_ore_queue = queues
        refinery.db.miner_output = output


def _process_refinery(refinery):
    """Move ore from receiving storage and run all possible recipes."""
    from evennia.utils import logger

    room = refinery.location
    if not room:
        return

    # Drain Ore Receiving Bay (MiningStorage) into shared input_inventory (sell-mode ore)
    for obj in room.contents:
        if not obj.tags.has("mining_storage", category="mining"):
            continue
        obj_key_lower = obj.key.lower()
        if "receiving" not in obj_key_lower and "bay" not in obj_key_lower:
            continue
        ore_inv = obj.db.inventory or {}   # MiningStorage uses db.inventory
        if not ore_inv:
            continue
        in_inv = refinery.db.input_inventory or {}
        for ore_key, tons in list(ore_inv.items()):
            tons = float(tons)
            if tons <= 0:
                continue
            in_inv[ore_key] = round(float(in_inv.get(ore_key, 0.0)) + tons, 2)
            logger.log_info(
                f"[RefineryEngine] {tons:.1f}t {ore_key} → {refinery.key} from {obj.key}"
            )
        refinery.db.input_inventory = in_inv
        obj.db.inventory = {}

    # Run all shared recipes until no more batches are possible
    for recipe_key in REFINING_RECIPES:
        while True:
            batches, _ = refinery.process_recipe(recipe_key, batches=1)
            if batches == 0:
                break

    # Process per-miner queues (process-mode deliveries)
    _process_miner_queues(refinery)


from .scripts import Script as _Script  # noqa: E402 — must follow Refinery definition


class RefineryEngine(_Script):
    """
    Global persistent script that automatically feeds and processes ore.

    Every tick (30 min):
      1. Finds all Refinery objects.
      2. Per refinery, locates the "Ore Receiving Bay" MiningStorage in the same
         room and drains it into the refinery's input_inventory.
      3. Runs all REFINING_RECIPES for as many batches as inputs allow.
    """

    def at_script_creation(self):
        self.key = "refinery_engine"
        self.desc = "Automatically feeds and processes ore at all refineries."
        self.interval = REFINERY_ENGINE_INTERVAL
        self.persistent = True
        self.start_delay = True

    def at_repeat(self):
        from evennia import search_tag
        from evennia.utils import logger

        refineries = search_tag("refinery", category="mining")
        for refinery in refineries:
            try:
                _process_refinery(refinery)
            except Exception as exc:
                logger.log_err(f"[RefineryEngine] Error on {refinery}: {exc}")
