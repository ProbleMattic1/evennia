"""Web entry points for plant refinery (attributed silo queue + collect)."""

from __future__ import annotations

from typeclasses.economy import get_economy
from typeclasses.haulers import get_plant_player_storage
from typeclasses.refining import (
    PROCESSING_FEE_RATE,
    PROCESSING_PLANT_VENDOR_ACCOUNT,
    REFINING_RECIPES,
    Refinery,
    refining_recipe_allowed_for_character,
    execute_refined_payout_from_treasury,
    is_plant_raw_resource_key,
    plant_raw_resource_display_name,
    refined_payout_breakdown,
    restore_miner_output_for_payout,
)
from world.venue_resolve import (
    processing_plant_room_for_venue,
    refinery_room_for_object,
    refinery_room_for_venue,
)


def _main_refinery(room):
    for o in getattr(room, "contents", []) or []:
        if o.is_typeclass(Refinery, exact=False):
            return o
    return None


def resolve_refinery_web_context(char, venue_id: str):
    """
    Refinery object lives in the refinery chamber; plant silos stay on the ore-bay floor.
    Returns (refinery_room, plant_room, error_message).
    """
    ref_target = refinery_room_for_venue(venue_id)
    ref_allowed = refinery_room_for_object(char)
    if not ref_target or not ref_allowed:
        return None, None, "Not allowed for this character and venue."
    if ref_target.id != ref_allowed.id:
        return None, None, "Not allowed for this character and venue."
    plant_room = processing_plant_room_for_venue(venue_id)
    return ref_target, plant_room, None  # plant_room may be None; callers that need silo must check


def feed_silo_to_miner_queue(
    char,
    venue_id: str,
    *,
    resource_key: str | None = None,
    tons: float | None = None,
    move_all: bool = False,
) -> tuple[bool, str]:
    ref_room, plant_room, err = resolve_refinery_web_context(char, venue_id)
    if err:
        return False, err

    ref = _main_refinery(ref_room)
    if not ref:
        return False, "No refinery in this plant."

    if move_all:
        if not plant_room:
            return False, "Ore bay for this venue is not available."
        moved = ref.transfer_owner_plant_silo_to_miner_queue(char, plant_room=plant_room)
        if not moved:
            return False, "Nothing valid to queue from your plant storage."
        lines = [f"Queued at {ref.key} from plant storage:"]
        for key, t in sorted(moved.items()):
            lines.append(f"  {plant_raw_resource_display_name(key)}: {t}t")
        return True, "\n".join(lines)

    if not resource_key or tons is None:
        return False, "Missing resourceKey or tons."

    if not plant_room:
        return False, "Ore bay for this venue is not available."

    silo = get_plant_player_storage(plant_room, char)
    if not silo:
        return False, "You have no assigned plant storage here."

    rk = str(resource_key).strip()
    try:
        tons_req = float(tons)
    except (TypeError, ValueError):
        return False, "Invalid tons."
    if tons_req <= 0:
        return False, "Tons must be positive."

    actual_moved = silo.withdraw(rk, tons_req)
    if actual_moved <= 0:
        return False, "Nothing moved."

    queued = ref.enqueue_miner_ore(char.id, rk, actual_moved)
    name = plant_raw_resource_display_name(rk)
    return True, f"Queued {queued}t of {name} at {ref.key}."


def feed_recipe_batch_to_miner_queue(char, venue_id: str, recipe_key: str) -> tuple[bool, str]:
    """
    Queue one batch of ``recipe_key``: withdraw all recipe inputs from the character's
    plant silo and enqueue them on the main refinery's miner queue.

    Single request path avoids partial multi-POST state if one resourceKey fails mid-way.
    """
    ref_room, plant_room, err = resolve_refinery_web_context(char, venue_id)
    if err:
        return False, err

    ref = _main_refinery(ref_room)
    if not ref:
        return False, "No refinery in this plant."

    rk = str(recipe_key or "").strip()
    recipe = REFINING_RECIPES.get(rk)
    if not recipe:
        return False, "Unknown recipe."

    ok_gate, gate_msg = refining_recipe_allowed_for_character(char, rk)
    if not ok_gate:
        return False, gate_msg

    inputs = recipe.get("inputs") or {}
    if not inputs:
        return False, "Recipe has no inputs."

    if not plant_room:
        return False, "Ore bay for this venue is not available."

    silo = get_plant_player_storage(plant_room, char)
    if not silo:
        return False, "You have no assigned plant storage here."

    inv = dict(silo.db.inventory or {})
    need: dict[str, float] = {}
    for k, v in inputs.items():
        ks = str(k).strip()
        if not is_plant_raw_resource_key(ks):
            return False, f"Invalid plant raw key in recipe: {ks}."
        try:
            n = float(v)
        except (TypeError, ValueError):
            return False, "Invalid recipe input amount."
        n = round(n, 2)
        if n <= 0:
            return False, "Invalid recipe input amount."
        need[ks] = n

    for ks, n in need.items():
        avail = round(float(inv.get(ks, 0.0)), 2)
        if avail + 1e-9 < n:
            name = plant_raw_resource_display_name(ks)
            return False, f"Not enough {name} in plant silo (need {n}t, have {avail}t)."

    for ks, n in need.items():
        avail = round(float(inv[ks]), 2)
        rem = round(avail - n, 2)
        if rem <= 0:
            inv.pop(ks, None)
        else:
            inv[ks] = rem

    silo.db.inventory = inv

    oid = str(char.id)
    queues = dict(ref.db.miner_ore_queue or {})
    acc = dict(queues.get(oid, {}))
    for ks, n in need.items():
        acc[ks] = round(float(acc.get(ks, 0.0)) + n, 2)
    queues[oid] = acc
    ref.db.miner_ore_queue = queues

    lines = [f"Queued 1× {recipe.get('name', rk)} at {ref.key}:"]
    for ks, n in sorted(need.items()):
        lines.append(f"  {plant_raw_resource_display_name(ks)}: {n}t")
    return True, "\n".join(lines)


def collect_attributed_refined(char, venue_id: str) -> tuple[bool, str]:
    """Mirror CmdCollectRefined payout path for web."""
    ref_room, _plant_room, err = resolve_refinery_web_context(char, venue_id)
    if err:
        return False, err

    ref = _main_refinery(ref_room)
    if not ref:
        return False, "No refinery in this plant."

    gross_pre = ref.get_miner_output_value(char.id)
    if gross_pre <= 0:
        return False, "You have no refined output waiting at this plant."

    bd_pre = refined_payout_breakdown(gross_pre, PROCESSING_FEE_RATE)

    econ = get_economy(create_missing=True)
    treasury_acct = econ.get_treasury_account("alpha-prime")
    plant_acct = PROCESSING_PLANT_VENDOR_ACCOUNT
    owner_acct = econ.get_character_account(char)

    econ.ensure_account(treasury_acct, opening_balance=int(econ.db.tax_pool or 0))
    econ.ensure_account(owner_acct, opening_balance=int(char.db.credits or 0))

    if econ.get_balance(treasury_acct) < bd_pre["required_from_treasury"]:
        return False, (
            "The planetary treasury cannot cover this payout yet "
            f"(needs {bd_pre['required_from_treasury']:,} cr, "
            f"treasury has {econ.get_balance(treasury_acct):,} cr). "
            "Try again later."
        )

    products, gross, fee = ref.collect_miner_output(char.id, fee_rate=PROCESSING_FEE_RATE)
    bd = refined_payout_breakdown(gross, PROCESSING_FEE_RATE)

    if econ.get_balance(treasury_acct) < bd["required_from_treasury"]:
        restore_miner_output_for_payout(ref, str(char.id), products)
        return False, "Payout was aborted; your refined output was restored."

    lines = [f"Refined output collection — {ref.key}"]
    for key, units in products.items():
        recipe = REFINING_RECIPES.get(key, {})
        name = recipe.get("name", key)
        val = int(units * recipe.get("base_value_cr", 0))
        lines.append(f"  {name}: {units:.2f} units  {val:,} cr")
    lines.append(f"  Gross value: {gross:,} cr")
    lines.append(f"  Processing fee: {fee:,} cr")
    lines.append(f"  Net from treasury: {bd['net']:,} cr")

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
            memo_plant=f"Plant fee share from {char.key} at {ref.key}",
            owner=char,
        )
    except Exception:
        restore_miner_output_for_payout(ref, str(char.id), products)
        raise

    char.db.credits = econ.get_character_balance(char)

    from world.station_services.contracts import try_complete_contract

    try_complete_contract(char, "refine_collect")

    lines.append(f"Received {bd['net']:,} cr from treasury. Balance: {char.db.credits:,} cr.")
    return True, "\n".join(lines)
