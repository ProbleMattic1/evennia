"""
Refining commands — Pass 3.

Commands
--------
refinelist       List all available refining recipes.
refinestatus     Show input/output inventory of the refinery in the current room.
feedrefinery     Transfer ore from a nearby mining storage or vehicle cargo
                 into the refinery's input inventory.
refine           Process ore into refined products.
collectproduct   Sell refined products at base price and deposit to ledger.
"""

from commands.command import Command
from typeclasses.refining import PROCESSING_FEE_RATE, REFINING_RECIPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _effective_location(caller):
    """Use exterior when caller is aboard a vehicle."""
    loc = caller.location
    if loc and getattr(loc.db, "is_vehicle", False):
        ext = loc.get_exterior_location()
        if ext:
            return ext
    return loc


def _find_refinery_in_room(caller):
    loc = _effective_location(caller)
    if not loc:
        return None
    for obj in loc.contents:
        if obj.tags.has("refinery", category="mining"):
            return obj
    return None


def _find_mining_storage_in_room(caller):
    loc = _effective_location(caller)
    if not loc:
        return None
    for obj in loc.contents:
        if obj.tags.has("mining_storage", category="mining"):
            return obj
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class CmdRefineList(Command):
    """
    List all available refining recipes.

    Usage:
      refinelist
      recipes
    """

    key = "refinelist"
    aliases = ["recipes", "recipeList"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        lines = ["|wAvailable Refining Recipes|n"]
        by_category = {}
        for key, recipe in REFINING_RECIPES.items():
            cat = recipe.get("category", "other")
            by_category.setdefault(cat, []).append((key, recipe))

        for cat in sorted(by_category):
            lines.append(f"\n  |w{cat.replace('_', ' ').title()}|n")
            for key, recipe in sorted(by_category[cat]):
                inputs_str = ", ".join(
                    f"{v}t {k.replace('_', ' ')}"
                    for k, v in recipe["inputs"].items()
                )
                lines.append(
                    f"    {recipe['name']:<30} "
                    f"← {inputs_str}  →  "
                    f"{recipe.get('output_units', 1)} unit(s)  "
                    f"|y{recipe.get('base_value_cr', 0):,}|n cr/unit"
                )
        caller.msg("\n".join(lines))


class CmdRefineStatus(Command):
    """
    Show the status of the refinery in the current room.

    Usage:
      refinestatus
      refinery
    """

    key = "refinestatus"
    aliases = ["refinery", "refinerystat"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return
        caller.msg(ref.get_status_report())


class CmdFeedRefinery(Command):
    """
    Feed raw ore into the refinery from a nearby storage unit or vehicle.

    Usage:
      feedrefinery <resource> <tons>
      feedrefinery all

    Transfers ore from a mining storage unit in the same room (or from the
    vehicle you are aboard, if docked here) into the refinery's input bin.

    Examples:
      feedrefinery iron 100
      feedrefinery all
    """

    key = "feedrefinery"
    aliases = ["feedore", "loadrefinery"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        # Source: mining storage in room takes priority over vehicle cargo
        storage = _find_mining_storage_in_room(caller)
        vehicle_source = None
        if not storage:
            loc = caller.location
            if loc and getattr(loc.db, "is_vehicle", False):
                vehicle_source = loc

        if not storage and not vehicle_source:
            caller.msg("No mining storage or vehicle cargo found as a source.")
            return

        from typeclasses.mining import RESOURCE_CATALOG

        args = self.args.strip().lower()

        if args == "all":
            if storage:
                contents = storage.withdraw_all()
            else:
                contents = vehicle_source.unload_all_cargo()
            if not contents:
                caller.msg("Source is empty.")
                return
            lines = [f"|wFed into {ref.key}:|n"]
            for key, tons in contents.items():
                actual = ref.feed(key, tons)
                name = RESOURCE_CATALOG.get(key, {}).get("name", key)
                lines.append(f"  {name}: {actual}t")
            caller.msg("\n".join(lines))
            return

        parts = args.split(None, 1)
        if len(parts) < 2:
            caller.msg("Usage: feedrefinery <resource> <tons>  OR  feedrefinery all")
            return
        resource_query, tons_str = parts
        try:
            tons_req = float(tons_str)
        except ValueError:
            caller.msg("Tons must be a number.")
            return

        if storage:
            inventory = storage.db.inventory or {}
        else:
            inventory = vehicle_source.db.cargo or {}

        matched_key = None
        for key in inventory:
            name = RESOURCE_CATALOG.get(key, {}).get("name", key)
            if resource_query in name.lower() or resource_query in key.lower():
                matched_key = key
                break
        if not matched_key:
            caller.msg(f"No resource matching '{resource_query}' in source.")
            return

        if storage:
            actual_moved = storage.withdraw(matched_key, tons_req)
        else:
            actual_moved = vehicle_source.unload_cargo(matched_key, tons_req)

        ref.feed(matched_key, actual_moved)
        name = RESOURCE_CATALOG.get(matched_key, {}).get("name", matched_key)
        caller.msg(f"Fed |w{actual_moved}t|n of {name} into |w{ref.key}|n.")


class CmdRefine(Command):
    """
    Process raw ore in the refinery into refined products.

    Usage:
      refine <product> [batches]

    Uses ore from the refinery's input bin to produce the named product.
    Default batches is 1; increase to process larger quantities at once.

    Use |wrefinelist|n to see available recipes and their input requirements.

    Examples:
      refine refined_iron
      refine refined_copper 10
      refine cut_diamond 5
    """

    key = "refine"
    aliases = ["process", "smelt"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        args = self.args.strip().split(None, 1)
        if not args:
            caller.msg("Usage: refine <product> [batches]  — use |wrefinelist|n to see options.")
            return

        recipe_query = args[0].lower()
        batches = 1
        if len(args) > 1:
            try:
                batches = max(1, int(args[1]))
            except ValueError:
                caller.msg("Batches must be a whole number.")
                return

        # Partial-match recipe key
        matched_key = None
        for key in REFINING_RECIPES:
            name = REFINING_RECIPES[key].get("name", key)
            if recipe_query in key.lower() or recipe_query in name.lower():
                matched_key = key
                break
        if not matched_key:
            caller.msg(
                f"No recipe matching '{recipe_query}'. Use |wrefinelist|n to see options."
            )
            return

        processed, msg = ref.process_recipe(matched_key, batches)
        if processed:
            caller.msg(f"|g{msg}|n\nUse |wcollectproduct {matched_key}|n to sell the output.")
        else:
            caller.msg(f"|r{msg}|n")


class CmdCollectProduct(Command):
    """
    Sell refined products from the refinery at base price.

    Usage:
      collectproduct
      collectproduct <product>

    Without arguments, sells everything in the output bin.
    With a product name, sells only that product.

    Note: Pass-3 action; base prices only.  Future passes will add
    market modifiers, export licensing, and faction pricing.
    """

    key = "collectproduct"
    aliases = ["sellproduct", "harvestproduct"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        out_inv = ref.db.output_inventory or {}
        if not out_inv:
            caller.msg(f"|w{ref.key}|n output bin is empty.")
            return

        product_query = self.args.strip().lower()

        if product_query:
            matched_key = None
            for key in out_inv:
                name = REFINING_RECIPES.get(key, {}).get("name", key)
                if product_query in key.lower() or product_query in name.lower():
                    matched_key = key
                    break
            if not matched_key:
                caller.msg(f"No product matching '{product_query}' in output bin.")
                return
            keys_to_sell = [matched_key]
        else:
            keys_to_sell = list(out_inv.keys())

        total_value = 0
        lines = [f"|wProduct collection — {ref.key}|n"]
        for key in keys_to_sell:
            collected, value = ref.collect_product(key)
            if collected <= 0:
                continue
            recipe = REFINING_RECIPES.get(key, {})
            name = recipe.get("name", key)
            total_value += value
            lines.append(f"  {name:<30} {collected:>8.2f} units   |y{value:>10,}|n cr")

        if total_value == 0:
            caller.msg("Nothing was collected.")
            return

        lines.append(f"  {'Total':<30} {'':>8}        |y{total_value:>10,}|n cr")

        from typeclasses.economy import grant_character_credits
        grant_character_credits(caller, total_value, memo=f"Refined product sale at {ref.key}")

        lines.append(f"\n|gDeposited |y{total_value:,}|g cr to your account.|n")
        lines.append(f"Remaining balance: |y{caller.db.credits:,}|n cr.")
        caller.msg("\n".join(lines))


class CmdCollectRefined(Command):
    """
    Collect your processed ore output from the Processing Plant.

    Usage:
      collectrefined

    When your hauler delivers in 'process' mode, ore is queued here for
    automated refining. Use this command at the Processing Plant to cash
    out your refined output. A 10% processing fee is deducted from the
    gross value; the remainder is deposited to your account.

    See: setdelivery <hauler> process
    """

    key = "collectrefined"
    aliases = ["claimrefined", "pickuprefined"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        products, gross, fee = ref.collect_miner_output(caller.id, fee_rate=PROCESSING_FEE_RATE)
        if not products:
            caller.msg(
                "You have no refined output waiting at this plant.\n"
                "Tip: use |wsetdelivery <hauler> process|n to queue ore for refining."
            )
            return

        net = gross - fee
        lines = [f"|wRefined Output Collection — {ref.key}|n"]
        for key, units in products.items():
            recipe = REFINING_RECIPES.get(key, {})
            name = recipe.get("name", key)
            val = int(units * recipe.get("base_value_cr", 0))
            lines.append(f"  {name:<30} {units:>8.2f} units   |y{val:>10,}|n cr")
        lines.append(f"  {'Gross value':<30}            |y{gross:>10,}|n cr")
        lines.append(
            f"  {'Processing fee ({:.0%})'.format(PROCESSING_FEE_RATE):<30}"
            f"            |r{fee:>10,}|n cr"
        )
        lines.append(f"  {'Net payout':<30}            |g{net:>10,}|n cr")

        from typeclasses.economy import get_economy
        econ = get_economy(create_missing=True)
        owner_acct = econ.get_character_account(caller)
        if fee > 0:
            plant_acct = "vendor:processing-plant"
            econ.ensure_account(plant_acct, opening_balance=0)
            econ.deposit(plant_acct, fee, memo=f"Processing fee from {caller.key}")
        econ.deposit(owner_acct, net, memo=f"Refined output collection at {ref.key}")
        caller.db.credits = econ.get_character_balance(caller)

        lines.append(f"\n|gDeposited |y{net:,}|g cr to your account.|n")
        lines.append(f"Balance: |y{caller.db.credits:,}|n cr.")
        caller.msg("\n".join(lines))
