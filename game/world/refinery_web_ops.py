"""Web entry points for plant refinery (attributed silo queue + collect)."""

from __future__ import annotations

from typeclasses.economy import get_economy
from typeclasses.haulers import get_plant_player_storage
from typeclasses.refining import (
    PROCESSING_FEE_RATE,
    PROCESSING_PLANT_VENDOR_ACCOUNT,
    REFINING_RECIPES,
    Refinery,
    execute_refined_payout_from_treasury,
    plant_raw_resource_display_name,
    refined_payout_breakdown,
    restore_miner_output_for_payout,
)
from world.venue_resolve import processing_plant_room_for_object, processing_plant_room_for_venue


def _main_refinery(room):
    for o in getattr(room, "contents", []) or []:
        if o.is_typeclass(Refinery, exact=False):
            return o
    return None


def resolve_plant_room_for_web_action(char, venue_id: str):
    """
    Character may only act on the processing plant for their resolved venue.
    """
    target = processing_plant_room_for_venue(venue_id)
    allowed = processing_plant_room_for_object(char)
    if not target or not allowed:
        return None, "Not allowed for this character and venue."
    if target.id != allowed.id:
        return None, "Not allowed for this character and venue."
    return target, None


def feed_silo_to_miner_queue(
    char,
    venue_id: str,
    *,
    resource_key: str | None = None,
    tons: float | None = None,
    move_all: bool = False,
) -> tuple[bool, str]:
    room, err = resolve_plant_room_for_web_action(char, venue_id)
    if err:
        return False, err

    ref = _main_refinery(room)
    if not ref:
        return False, "No refinery in this plant."

    if move_all:
        moved = ref.transfer_owner_plant_silo_to_miner_queue(char)
        if not moved:
            return False, "Nothing valid to queue from your plant storage."
        lines = [f"Queued at {ref.key} from plant storage:"]
        for key, t in sorted(moved.items()):
            lines.append(f"  {plant_raw_resource_display_name(key)}: {t}t")
        return True, "\n".join(lines)

    if not resource_key or tons is None:
        return False, "Missing resourceKey or tons."

    silo = get_plant_player_storage(room, char)
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


def collect_attributed_refined(char, venue_id: str) -> tuple[bool, str]:
    """Mirror CmdCollectRefined payout path for web."""
    room, err = resolve_plant_room_for_web_action(char, venue_id)
    if err:
        return False, err

    ref = _main_refinery(room)
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
