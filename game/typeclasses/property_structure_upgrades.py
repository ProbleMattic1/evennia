"""
Purchase structure upgrades (credits -> structure.db.upgrades).
"""

from typeclasses.economy import get_economy
from typeclasses.property_claim_market import (
    collect_property_construction_payment,
    get_construction_builder,
    refund_property_construction_payment,
)
from typeclasses.property_holdings import PROPERTY_HOLDING_CATEGORY
from world.property_structure_upgrade_registry import (
    blueprint_allows_upgrade,
    next_upgrade_level_cost_cr,
    upgrade_def,
)


def purchase_structure_upgrade(owner, holding, structure_dbid, upgrade_key):
    """
    Returns (ok: bool, message: str).
    structure_dbid: int Evennia #id of PropertyStructure on this holding.
    """
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."

    key = (upgrade_key or "").strip().lower()
    d = upgrade_def(key)
    if not d:
        return False, "Unknown upgrade."

    st = None
    for obj in holding.structures():
        if obj.id == int(structure_dbid):
            st = obj
            break
    if not st or not st.tags.has("property_structure", category=PROPERTY_HOLDING_CATEGORY):
        return False, "That structure is not on this parcel."

    bid = st.db.blueprint_id
    if not blueprint_allows_upgrade(d, bid):
        return False, "That upgrade is not available for this structure type."

    ups = dict(st.db.upgrades or {})
    cur = int(ups.get(key) or 0)
    nxt, price = next_upgrade_level_cost_cr(key, cur)
    if nxt is None or price is None:
        return False, "That upgrade is already at max level."

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
            tx_type="property_structure_upgrade",
            withdraw_memo=f"property upgrade {key} L{nxt}",
            record_memo=f"{owner.key} upgrade {key} L{nxt}",
        )
    else:
        econ.withdraw(acct, price, memo=f"property upgrade {key} L{nxt}")
        owner.db.credits = econ.get_character_balance(owner)

    ups[key] = nxt
    try:
        st.db.upgrades = ups
    except Exception:
        if builder and net_amount is not None:
            refund_property_construction_payment(
                owner, price, builder, net_amount=net_amount, tax_amount=tax_amount
            )
        else:
            econ.deposit(acct, price, memo="Refund: upgrade apply failed")
            owner.db.credits = econ.get_character_balance(owner)
        return False, "Could not apply upgrade; payment refunded."

    if not builder:
        owner.db.credits = econ.get_character_balance(owner)
    return True, f"{st.key}: {key} -> level {nxt} ({price:,} cr)."
