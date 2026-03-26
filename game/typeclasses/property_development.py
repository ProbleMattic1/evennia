"""
Ensure PropertyHolding for a claimed lot; start operations; install structures.
"""

from evennia import create_object

from typeclasses.property_holdings import PropertyHolding
from typeclasses.property_operation_registry import register_property_holding
from typeclasses.property_structures import PropertyStructure


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
