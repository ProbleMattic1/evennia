"""
Primary market: property lots and deeds (Real Estate Office).

Economy pattern matches mining primary deeds (broker + treasury tax).
"""

import random

from evennia import create_object, search_object

from typeclasses.characters import (
    NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
    NANOMEGA_REALTY_CHARACTER_KEY,
)
from typeclasses.property_claims import (
    CLAIM_TITLE_PREFIX_BY_ZONE,
    CLAIM_TYPECLASS_BY_ZONE,
)
from typeclasses.property_development import ensure_holding_for_claimed_lot
from typeclasses.property_lot_registry import (
    get_listable_lots_from_registry,
    move_lot_to_claimed_archive,
    unregister_listable_property_lot,
)


def _first_object(key):
    found = search_object(key)
    return found[0] if found else None


def get_realty_broker():
    return _first_object(NANOMEGA_REALTY_CHARACTER_KEY)


def get_construction_builder():
    return _first_object(NANOMEGA_CONSTRUCTION_CHARACTER_KEY)


def lot_listing_price(lot):
    from typeclasses.property_lots import TIER_LIST_PRICES, ZONE_MULTIPLIERS

    tier = int(lot.db.lot_tier or 1)
    zone = lot.db.zone or "residential"
    base = TIER_LIST_PRICES.get(tier, 5_000)
    mult = ZONE_MULTIPLIERS.get(zone, 1.00)
    return int(round(base * mult))


def lot_is_market_listable(lot):
    if not lot or not lot.tags.has("property_lot", category="realty"):
        return False
    return not getattr(lot.db, "is_claimed", False)


def collect_primary_property_sale(buyer, price, broker, *, tx_type="primary_property_sale", memo=None):
    from typeclasses.claim_market import outfitters_claims_tax_rate
    from typeclasses.economy import get_economy

    tax_rate   = outfitters_claims_tax_rate()
    tax_amount = int(round(price * tax_rate))
    net_amount = int(price) - tax_amount

    econ = get_economy(create_missing=True)
    pa   = econ.get_character_account(buyer)
    ba   = econ.get_character_account(broker)
    ta   = econ.get_treasury_account("alpha-prime")

    econ.ensure_account(pa, opening_balance=int(buyer.db.credits or 0))
    econ.ensure_account(ba, opening_balance=int(broker.db.credits or 0))
    econ.ensure_account(ta, opening_balance=int(econ.db.tax_pool or 0))

    econ.withdraw(pa, int(price),    memo=memo or "Property deed purchase")
    econ.deposit(ba,  net_amount,    memo=f"Broker revenue — property ({broker.key})")
    if tax_amount > 0:
        econ.deposit(ta, tax_amount, memo="Sales tax (property deed)")

    econ.record_transaction(
        tx_type=tx_type,
        amount=int(price),
        from_account=pa,
        to_account=ba,
        memo=memo or f"{buyer.key} property purchase",
        extra={"tax_amount": tax_amount, "treasury_account": ta},
    )

    buyer.db.credits  = econ.get_balance(pa)
    broker.db.credits = econ.get_balance(ba)
    econ.db.tax_pool  = econ.get_balance(ta)

    return net_amount, tax_amount


def collect_property_construction_payment(
    buyer,
    price,
    builder,
    *,
    tx_type="property_construction",
    withdraw_memo="Property construction",
    record_memo=None,
):
    """
    Same tax split as primary deed sales: net to builder, tax to alpha-prime treasury.
    """
    from typeclasses.claim_market import outfitters_claims_tax_rate
    from typeclasses.economy import get_economy

    price = int(price)
    tax_rate = outfitters_claims_tax_rate()
    tax_amount = int(round(price * tax_rate))
    net_amount = price - tax_amount

    econ = get_economy(create_missing=True)
    pa = econ.get_character_account(buyer)
    ba = econ.get_character_account(builder)
    ta = econ.get_treasury_account("alpha-prime")

    econ.ensure_account(pa, opening_balance=int(buyer.db.credits or 0))
    econ.ensure_account(ba, opening_balance=int(builder.db.credits or 0))
    econ.ensure_account(ta, opening_balance=int(econ.db.tax_pool or 0))

    econ.withdraw(pa, price, memo=withdraw_memo)
    econ.deposit(ba, net_amount, memo=f"Construction revenue ({builder.key})")
    if tax_amount > 0:
        econ.deposit(ta, tax_amount, memo="Sales tax (property construction)")

    econ.record_transaction(
        tx_type=tx_type,
        amount=price,
        from_account=pa,
        to_account=ba,
        memo=record_memo or f"{buyer.key} property construction",
        extra={"tax_amount": tax_amount, "treasury_account": ta},
    )

    buyer.db.credits = econ.get_balance(pa)
    builder.db.credits = econ.get_balance(ba)
    econ.db.tax_pool = econ.get_balance(ta)

    return net_amount, tax_amount


def _refund_property_purchase(buyer, price, broker=None, net_amount=None, tax_amount=None):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    pa   = econ.get_character_account(buyer)
    econ.deposit(pa, int(price), memo="Refund: property purchase rolled back")
    econ.sync_character_balance(buyer)

    if broker is not None and net_amount is not None:
        ba = econ.get_character_account(broker)
        try:
            econ.withdraw(ba, int(net_amount), memo="Refund clawback broker (property)")
        except ValueError:
            pass
        econ.sync_character_balance(broker)

    if tax_amount and int(tax_amount) > 0:
        ta = econ.get_treasury_account("alpha-prime")
        try:
            econ.withdraw(ta, int(tax_amount), memo="Refund clawback tax (property)")
        except ValueError:
            pass
        econ.db.tax_pool = econ.get_balance(ta)


def refund_property_construction_payment(
    buyer, price, builder=None, net_amount=None, tax_amount=None
):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    pa = econ.get_character_account(buyer)
    econ.deposit(pa, int(price), memo="Refund: property construction rolled back")
    econ.sync_character_balance(buyer)

    if builder is not None and net_amount is not None:
        ba = econ.get_character_account(builder)
        try:
            econ.withdraw(ba, int(net_amount), memo="Refund clawback construction (property)")
        except ValueError:
            pass
        econ.sync_character_balance(builder)

    if tax_amount and int(tax_amount) > 0:
        ta = econ.get_treasury_account("alpha-prime")
        try:
            econ.withdraw(ta, int(tax_amount), memo="Refund clawback tax (property construction)")
        except ValueError:
            pass
        econ.db.tax_pool = econ.get_balance(ta)


def create_property_claim_for_lot(lot, owner):
    zone = (lot.db.zone or "residential").lower()
    tc_path = CLAIM_TYPECLASS_BY_ZONE.get(zone)
    if not tc_path:
        zone = "residential"
        tc_path = CLAIM_TYPECLASS_BY_ZONE["residential"]

    prefix = CLAIM_TITLE_PREFIX_BY_ZONE.get(zone, "Property claim")
    stem   = f"{prefix}: {lot.key}"
    claim = create_object(
        tc_path,
        key=stem,
        location=owner,
        home=owner,
    )
    claim.key         = f"{stem} #{claim.id}"
    claim.db.lot_ref  = lot
    claim.db.lot_key  = lot.key
    claim.db.lot_tier = int(lot.db.lot_tier or 1)
    claim.db.desc     = (
        f"Deed for {lot.zone_label} property at {lot.key} (Tier {lot.db.lot_tier})."
    )
    claim.move_to(owner, quiet=True)
    return claim


def purchase_property_deed(buyer, lot_key):
    from typeclasses.economy import get_economy

    lots = [
        obj for obj in search_object(lot_key)
        if obj.tags.has("property_lot", category="realty")
    ]
    if not lots:
        return False, f"No property lot matching '{lot_key}'.", None

    lot = lots[0]

    if getattr(lot.db, "is_claimed", False):
        return False, "That lot is already claimed.", None

    price   = lot_listing_price(lot)
    econ    = get_economy(create_missing=True)
    credits = econ.get_character_balance(buyer)
    if credits < price:
        return False, f"This deed costs {price:,} cr. You have {credits:,} cr.", None

    if getattr(lot.db, "is_claimed", False):
        return False, "That lot was just claimed by someone else.", None

    broker     = get_realty_broker()
    net_amount = tax_amount = None

    if broker:
        net_amount, tax_amount = collect_primary_property_sale(
            buyer, price, broker,
            tx_type="property_deed_purchase",
            memo=f"{buyer.key} purchased property deed for {lot.key}",
        )
    else:
        acct = econ.get_character_account(buyer)
        econ.ensure_account(acct, opening_balance=int(buyer.db.credits or 0))
        try:
            econ.withdraw(acct, price, memo="Property deed purchase")
        except ValueError:
            return False, "Insufficient credits.", None
        econ.sync_character_balance(buyer)

    if getattr(lot.db, "is_claimed", False):
        _refund_property_purchase(buyer, price, broker=broker,
                                  net_amount=net_amount, tax_amount=tax_amount)
        return False, "That lot was claimed during checkout. Refunded.", None

    claim = create_property_claim_for_lot(lot, buyer)
    lot.db.is_claimed = True
    lot.db.owner = buyer
    ensure_holding_for_claimed_lot(lot, buyer)
    unregister_listable_property_lot(lot)
    move_lot_to_claimed_archive(lot)
    msg = f"Purchased {claim.key} for {price:,} cr."
    return True, msg, claim


def purchase_random_property_deed_by_zone(buyer, zone):
    """
    Prefer a random existing listable lot in ``zone``; if none, mint one like the
    discovery engine (subject to global listable cap), then run the normal deed sale.
    """
    from typeclasses.property_exchange_limits import MAX_LISTABLE_PROPERTY_LOTS
    from typeclasses.property_lot_generation import generate_market_property_lot

    z = (zone or "").strip().lower()
    allowed = frozenset({"commercial", "residential", "industrial"})
    if z not in allowed:
        return False, "Invalid zone.", None

    candidates = [
        lot
        for lot in get_listable_lots_from_registry()
        if lot_is_market_listable(lot) and (lot.db.zone or "residential").lower() == z
    ]

    if not candidates:
        if len(get_listable_lots()) >= MAX_LISTABLE_PROPERTY_LOTS:
            return (
                False,
                "The property exchange is at capacity; try again after parcels sell or the next restock.",
                None,
            )
        lot = generate_market_property_lot(z)
        return purchase_property_deed(buyer, lot.key)

    random.shuffle(candidates)
    for lot in candidates:
        success, msg, claim = purchase_property_deed(buyer, lot.key)
        if success:
            return True, msg, claim

    if len(get_listable_lots()) >= MAX_LISTABLE_PROPERTY_LOTS:
        return (
            False,
            "No deeds could be sold right now and the exchange is at capacity.",
            None,
        )

    lot = generate_market_property_lot(z)
    return purchase_property_deed(buyer, lot.key)


def get_listable_lots():
    return get_listable_lots_from_registry()


def serialize_lot_row(lot):
    from typeclasses.property_lots import TIER_LABELS, ZONE_LABELS

    tier = int(lot.db.lot_tier or 1)
    zone = lot.db.zone or "residential"
    return {
        "lotKey":         lot.key,
        "lotId":          lot.id,
        "tier":           tier,
        "tierLabel":      TIER_LABELS.get(tier, "Unknown"),
        "zone":           zone,
        "zoneLabel":      ZONE_LABELS.get(zone, "Unknown"),
        "sizeUnits":      int(lot.db.size_units or 1),
        "listingPriceCr": lot_listing_price(lot),
        "purchasable":    True,
        "sellerKey":      NANOMEGA_REALTY_CHARACTER_KEY,
    }


def serialize_property_lot_detail(lot):
    """
    Full parcel payload for property-claim detail API (owner view).

    Includes sovereign reference list price (same formula as the office) for
    analytics and future resale UX; ``purchasable`` reflects current market state.
    """
    if not lot or not lot.tags.has("property_lot", category="realty"):
        return None

    row = dict(serialize_lot_row(lot))
    row["purchasable"] = lot_is_market_listable(lot)
    row["description"] = lot.db.desc or ""
    row["isClaimed"] = bool(getattr(lot.db, "is_claimed", False))
    owner = getattr(lot.db, "owner", None)
    row["ownerKey"] = owner.key if owner else None
    row["ownerId"] = owner.id if owner else None
    row["roomKey"] = lot.location.key if lot.location else None
    row["referenceListPriceCr"] = lot_listing_price(lot)
    return row
