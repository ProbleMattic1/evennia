"""
Ensure PropertyHolding for a claimed lot; start operations; install structures.
"""

from evennia import create_object

from typeclasses.property_holdings import PropertyHolding
from typeclasses.property_operation_handlers import OPERATION_HANDLERS
from typeclasses.property_operation_registry import register_property_holding
from typeclasses.property_structures import PropertyStructure

EXTRA_STRUCTURE_SLOT_BASE_CR = 5_000
EXTRA_STRUCTURE_SLOT_GROWTH = 1.35


def ensure_holding_for_claimed_lot(lot, owner):
    existing = getattr(lot.db, "holding_ref", None)
    if existing:
        existing.set_title_owner(owner)
        register_property_holding(existing)
        return existing
    holding = create_object(
        PropertyHolding,
        key=f"Holding: {lot.key}",
        location=lot,
        home=lot,
    )
    holding.bind_lot(lot, owner)
    lot.db.holding_ref = holding
    register_property_holding(holding)
    return holding


def start_operation(holding, *, kind):
    op = dict(holding.db.operation or {})
    op["kind"] = kind
    op["level"] = int(op.get("level") or 0)
    op["paused"] = False
    op["next_tick_at"] = None
    holding.db.operation = op
    register_property_holding(holding)


def install_structure(holding, blueprint_id, *, slot_weight=1):
    assert holding.can_install(slot_weight)
    st = create_object(
        PropertyStructure,
        key=f"{blueprint_id} @ {holding.key}",
        location=holding,
        home=holding,
    )
    st.db.slot_weight = int(slot_weight)
    st.apply_blueprint(blueprint_id)
    return st


def set_operation_paused(holding, paused):
    op = dict(holding.db.operation or {})
    op["paused"] = bool(paused)
    holding.db.operation = op
    register_property_holding(holding)


def retool_operation(holding, new_kind):
    zone = (holding.db.zone or "residential").lower()
    k = (new_kind or "").strip().lower()
    if (zone, k) not in OPERATION_HANDLERS:
        return False, f"Operation {k!r} is not valid for a {zone} parcel."
    op = dict(holding.db.operation or {})
    if not op.get("kind"):
        return False, "This parcel has no active operation to retool."
    if op.get("kind") == k:
        return False, "That is already the active operation type."
    op["kind"] = k
    op["level"] = 0
    op["paused"] = False
    op["next_tick_at"] = None
    holding.db.operation = op
    register_property_holding(holding)
    return True, f"Operation retargeted to {k}."


def next_extra_structure_slot_price_cr(holding):
    n = int((holding.db.operation or {}).get("extra_slots") or 0)
    return int(round(EXTRA_STRUCTURE_SLOT_BASE_CR * (EXTRA_STRUCTURE_SLOT_GROWTH**n)))


def purchase_extra_structure_slot(holding, owner):
    """
    Charge owner and increment operation.extra_slots by 1.
    Returns (ok: bool, message: str).
    """
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."

    from typeclasses.economy import get_economy
    from typeclasses.property_claim_market import (
        collect_property_construction_payment,
        get_construction_builder,
        refund_property_construction_payment,
    )

    price = next_extra_structure_slot_price_cr(holding)
    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(owner)
    econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
    bal = econ.get_character_balance(owner)
    if bal < price:
        return False, f"You need {price:,} cr but only have {bal:,} cr."

    builder = get_construction_builder()
    net_amount = tax_amount = None
    if builder:
        net_amount, tax_amount = collect_property_construction_payment(
            owner,
            price,
            builder,
            tx_type="property_extra_structure_slot",
            withdraw_memo="property extra structure slot",
            record_memo=f"{owner.key} extra structure slot",
        )
    else:
        econ.withdraw(acct, price, memo="property extra structure slot")
        owner.db.credits = econ.get_character_balance(owner)

    op = dict(holding.db.operation or {})
    op["extra_slots"] = int(op.get("extra_slots") or 0) + 1
    holding.db.operation = op
    try:
        register_property_holding(holding)
    except Exception:
        if builder and net_amount is not None:
            refund_property_construction_payment(
                owner, price, builder, net_amount=net_amount, tax_amount=tax_amount
            )
        else:
            econ.deposit(acct, price, memo="Refund: extra slot register failed")
            owner.db.credits = econ.get_character_balance(owner)
        op["extra_slots"] = int(op.get("extra_slots") or 0) - 1
        holding.db.operation = op
        return False, "Could not register extra slot; payment refunded."

    if not builder:
        owner.db.credits = econ.get_character_balance(owner)
    return True, f"Parcel capacity +1 slot ({price:,} cr). Total extra slots: {op['extra_slots']}."
