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
from typeclasses.refining import (
    PROCESSING_FEE_RATE,
    PROCESSING_PLANT_VENDOR_ACCOUNT,
    REFINING_RECIPES,
    execute_refined_payout_from_treasury,
    refined_payout_breakdown,
    restore_miner_output_for_payout,
)


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


def _refinery_candidates_in_room(loc):
    if not loc:
        return []
    return [o for o in loc.contents if o.tags.has("refinery", category="mining")]


def _split_args_at_target(args: str):
    """
    'refined_iron 5 at mk iii' -> ('refined_iron 5', 'mk iii')
    'feedrefinery iron 10 at #104' -> ('feedrefinery iron 10', '#104')
    'at mk iii' -> ('', 'mk iii')  for commands whose only arg is the target
    """
    raw = (args or "").strip()
    lower = raw.lower()
    if lower.startswith("at "):
        return "", raw[3:].strip()
    if " at " not in lower:
        return raw, None
    idx = lower.rfind(" at ")
    if idx < 0:
        return raw, None
    main = raw[:idx].strip()
    target = raw[idx + 4 :].strip()
    return main, target if target else None


def _find_refinery_in_room(caller, target_fragment=None):
    """
    If target_fragment: prefer owned portable whose key/id matches, else plant Refinery key/id.
    Else: prefer caller-owned portable in room, else first Refinery, else any refinery-tagged.
    """
    loc = _effective_location(caller)
    if not loc:
        return None

    candidates = _refinery_candidates_in_room(loc)
    if not candidates:
        return None

    portables = [
        o
        for o in candidates
        if o.is_typeclass("typeclasses.processors.PortableProcessor", exact=False)
    ]
    plants = [
        o
        for o in candidates
        if o.is_typeclass("typeclasses.refining.Refinery", exact=False)
    ]

    frag = (target_fragment or "").strip().lower()
    if frag:
        for o in portables:
            if getattr(o.db, "owner", None) != caller:
                continue
            key = (o.key or "").lower()
            if frag in key or frag == str(o.id) or frag == f"#{o.id}":
                return o
        for o in plants:
            key = (o.key or "").lower()
            if frag in key or frag == str(o.id) or frag == f"#{o.id}":
                return o
        return None

    for o in portables:
        if getattr(o.db, "owner", None) == caller:
            return o
    if plants:
        return plants[0]
    return candidates[0]


def _find_plant_refinery_in_room(caller):
    """For collectrefined / plant miner queues only."""
    loc = _effective_location(caller)
    if not loc:
        return None
    for o in loc.contents:
        if o.is_typeclass("typeclasses.refining.Refinery", exact=False):
            return o
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


class CmdFeedProcessorFromStorage(Command):
    """
    Move ore from your assigned storage in this room into your personal processor.

    Usage:
      feedprocessor <resource> <tons>
      feedprocessor all
      feedprocessor <resource> <tons> at <processor name or #dbref>

    Requires your PortableProcessor in the same room. Haulers deliver to your
    assigned storage first; use this to distribute ore into the processor.
    """

    key = "feedprocessor"
    aliases = ["feedfromstorage", "storagetoprocessor"]
    help_category = "Refining"

    def func(self):
        from typeclasses.haulers import get_player_destination_storage

        caller = self.caller
        main, target = _split_args_at_target(self.args)
        loc = _effective_location(caller)
        if not loc:
            caller.msg("You have no location.")
            return

        proc = _find_refinery_in_room(caller, target_fragment=target)
        if not proc or not proc.is_typeclass(
            "typeclasses.processors.PortableProcessor", exact=False
        ):
            caller.msg(
                "No personal processor here that you own. Deploy one in this room, "
                "or use |wfeedprocessor ... at <name>|n if several are present."
            )
            return
        if getattr(proc.db, "owner", None) != caller:
            caller.msg("That processor is not yours.")
            return

        storage = get_player_destination_storage(loc, caller)
        if not storage:
            caller.msg("No assigned storage for you in this room.")
            return

        from typeclasses.mining import RESOURCE_CATALOG

        args = main.strip().lower()

        def _return_overflow(key, overflow):
            if overflow <= 0:
                return
            inv = storage.db.inventory or {}
            inv[key] = round(float(inv.get(key, 0)) + overflow, 2)
            storage.db.inventory = inv

        if args == "all":
            inv = dict(storage.db.inventory or {})
            if not inv:
                caller.msg("Your assigned storage is empty.")
                return
            lines = [f"|wFed into {proc.key} from {storage.key}:|n"]
            for key, tons in list(inv.items()):
                tons = float(tons)
                if tons <= 0:
                    continue
                removed = storage.withdraw(key, tons)
                if removed <= 0:
                    continue
                fed = proc.feed(key, removed)
                overflow = round(removed - fed, 2)
                _return_overflow(key, overflow)
                name = RESOURCE_CATALOG.get(key, {}).get("name", key)
                lines.append(f"  {name}: {fed}t")
            caller.msg("\n".join(lines))
            return

        parts = args.split(None, 1)
        if len(parts) < 2:
            caller.msg("Usage: feedprocessor <resource> <tons>  OR  feedprocessor all")
            return
        resource_query, tons_str = parts
        try:
            tons_req = float(tons_str)
        except ValueError:
            caller.msg("Tons must be a number.")
            return

        inventory = storage.db.inventory or {}
        matched_key = None
        for key in inventory:
            name = RESOURCE_CATALOG.get(key, {}).get("name", key)
            if resource_query in name.lower() or resource_query in key.lower():
                matched_key = key
                break
        if not matched_key:
            caller.msg(f"No resource matching '{resource_query}' in your assigned storage.")
            return

        removed = storage.withdraw(matched_key, tons_req)
        if removed <= 0:
            caller.msg("Nothing moved.")
            return
        fed = proc.feed(matched_key, removed)
        overflow = round(removed - fed, 2)
        _return_overflow(matched_key, overflow)
        name = RESOURCE_CATALOG.get(matched_key, {}).get("name", matched_key)
        caller.msg(f"Fed |w{fed}t|n of {name} into |w{proc.key}|n (from assigned storage).")

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
      refinestatus at <target>

    Optional |wat <target>|n chooses which refinery when several are present
    (name fragment, or #dbref). Default: your portable if you own one here, else the plant.
    """

    key = "refinestatus"
    aliases = ["refinery", "refinerystat"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        main, target = _split_args_at_target(self.args)
        ref = _find_refinery_in_room(caller, target_fragment=target)
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
      ... at <target>

    Transfers ore from a mining storage unit in the same room (or from the
    vehicle you are aboard, if docked here) into the refinery's input bin.

    Examples:
      feedrefinery iron 100
      feedrefinery all
      feedrefinery iron 100 at ore processor
    """

    key = "feedrefinery"
    aliases = ["feedore", "loadrefinery"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        main, target = _split_args_at_target(self.args)
        ref = _find_refinery_in_room(caller, target_fragment=target)
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

        from typeclasses.haulers import PLANT_PLAYER_STORAGE_CATEGORY, PLANT_PLAYER_STORAGE_TAG

        if storage and ref.is_typeclass("typeclasses.refining.Refinery", exact=False):
            if storage.tags.has(PLANT_PLAYER_STORAGE_TAG, category=PLANT_PLAYER_STORAGE_CATEGORY):
                if getattr(storage.db, "owner", None) == caller:
                    caller.msg(
                        "Ore in your assigned plant storage is ingested automatically into your "
                        "refining queue. Use |wcollectrefined|n here when output is ready. "
                        "To move ore into a personal processor, use |wfeedprocessor|n in the room "
                        "where that processor is deployed."
                    )
                    return

        from typeclasses.mining import RESOURCE_CATALOG

        args = main.strip().lower()

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
      refine <product> [batches] at <target>

    Uses ore from the refinery's input bin to produce the named product.
    Default batches is 1; increase to process larger quantities at once.

    Use |wrefinelist|n to see available recipes and their input requirements.

    Examples:
      refine refined_iron
      refine refined_copper 10
      refine cut_diamond 5
      refine refined_iron 5 at ore processor
    """

    key = "refine"
    aliases = ["process", "smelt"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        main, target = _split_args_at_target(self.args)
        ref = _find_refinery_in_room(caller, target_fragment=target)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        args = main.strip().split(None, 1)
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
      collectproduct <product> at <target>
      collectproduct at <target>

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
        main, target = _split_args_at_target(self.args)
        ref = _find_refinery_in_room(caller, target_fragment=target)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        out_inv = ref.db.output_inventory or {}
        if not out_inv:
            caller.msg(f"|w{ref.key}|n output bin is empty.")
            return

        product_query = main.strip().lower()

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

    Your hauler delivers ore into your assigned storage at the plant; the plant
    moves it into your refining queue and produces attributed output. Use this
    command at the Processing Plant to cash out. Payout is funded from the planetary
    treasury (transfers only): a 10%% processing fee is split between the plant vendor
    and the treasury; the net is transferred to you. If the treasury cannot cover
    the payout, collection is refused or your output is restored.
    """

    key = "collectrefined"
    aliases = ["claimrefined", "pickuprefined"]
    help_category = "Refining"

    def func(self):
        caller = self.caller
        ref = _find_plant_refinery_in_room(caller)
        if not ref:
            caller.msg("There is no refinery here.")
            return

        gross_pre = ref.get_miner_output_value(caller.id)
        if gross_pre <= 0:
            caller.msg(
                "You have no refined output waiting at this plant.\n"
                "Ore must reach your assigned storage here (hauler delivery); the plant "
                "refinery cycle then fills your queue."
            )
            return

        bd_pre = refined_payout_breakdown(gross_pre, PROCESSING_FEE_RATE)

        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        treasury_acct = econ.get_treasury_account("alpha-prime")
        plant_acct = PROCESSING_PLANT_VENDOR_ACCOUNT
        owner_acct = econ.get_character_account(caller)

        econ.ensure_account(treasury_acct, opening_balance=int(econ.db.tax_pool or 0))
        econ.ensure_account(plant_acct, opening_balance=0)
        econ.ensure_account(owner_acct, opening_balance=int(caller.db.credits or 0))

        if econ.get_balance(treasury_acct) < bd_pre["required_from_treasury"]:
            caller.msg(
                f"The planetary treasury cannot cover this payout yet "
                f"(needs |y{bd_pre['required_from_treasury']:,}|n cr, "
                f"treasury has |y{econ.get_balance(treasury_acct):,}|n cr). "
                f"Try again later."
            )
            return

        products, gross, fee = ref.collect_miner_output(caller.id, fee_rate=PROCESSING_FEE_RATE)
        bd = refined_payout_breakdown(gross, PROCESSING_FEE_RATE)

        if econ.get_balance(treasury_acct) < bd["required_from_treasury"]:
            restore_miner_output_for_payout(ref, str(caller.id), products)
            caller.msg(
                "Payout was aborted: treasury balance changed. Your refined output was restored. "
                "Please try again."
            )
            return

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
        lines.append(
            f"  {'  (plant / treasury fee)':<30}"
            f"            |y{bd['plant_fee']:>5,}|n / |y{bd['treasury_fee']:>5,}|n cr"
        )
        lines.append(f"  {'Net from treasury':<30}            |g{bd['net']:>10,}|n cr")

        try:
            execute_refined_payout_from_treasury(
                econ,
                treasury_account=treasury_acct,
                plant_vendor_account=plant_acct,
                miner_account=owner_acct,
                net=bd["net"],
                plant_fee=bd["plant_fee"],
                gross=gross,
                fee=fee,
                treasury_fee=bd["treasury_fee"],
                memo_miner=f"Refined output collection at {ref.key}",
                memo_plant=f"Plant fee share from {caller.key} at {ref.key}",
            )
        except Exception:
            restore_miner_output_for_payout(ref, str(caller.id), products)
            caller.msg("Payout failed; your refined output was restored. Please contact staff.")
            raise

        caller.db.credits = econ.get_character_balance(caller)

        lines.append(f"\n|gReceived |y{bd['net']:,}|g cr from treasury.|n")
        lines.append(f"Balance: |y{caller.db.credits:,}|n cr.")
        caller.msg("\n".join(lines))
