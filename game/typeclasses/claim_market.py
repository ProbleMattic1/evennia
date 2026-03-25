"""
Listed mining-site claim deeds: pricing and purchase for the claims market UI.

Deed purchase grants a MiningClaim in inventory; mine ownership is applied via
deploy_package_from_inventory / mine/deploy (package + claim).
"""

from evennia import search_object, search_script, search_tag

from typeclasses.characters import NANOMEGA_REALTY_CHARACTER_KEY


def _first_object(key):
    found = search_object(key)
    return found[0] if found else None


def _get_claims_vendor():
    """CatalogVendor in Aurnom Mining Outfitters, if present."""
    room = _first_object("Aurnom Mining Outfitters")
    if not room:
        return None
    for obj in room.contents:
        if obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            return obj
    return None


def get_primary_deed_broker():
    """NanoMegaPlex broker character, if present in the world."""
    return _first_object(NANOMEGA_REALTY_CHARACTER_KEY)


def outfitters_claims_tax_rate():
    """
    Sales tax rate for primary deed sales, from the Outfitters catalog vendor.
    Matches CatalogVendor.record_sale clamping.
    """
    vendor = _get_claims_vendor()
    if not vendor:
        return 0.0
    tax_rate = getattr(vendor.db, "tax_rate", None)
    if tax_rate is None or not isinstance(tax_rate, (int, float)):
        tax_rate = 0.0
    return max(0.0, min(1.0, float(tax_rate)))


def collect_primary_deed_sale(
    buyer,
    price,
    broker,
    *,
    tx_type="primary_deed_sale",
    memo=None,
    withdraw_memo=None,
    tax_rate=None,
):
    """
    Withdraw ``price`` from buyer; net to broker character ledger; tax to alpha-prime treasury.
    Uses the same tax split as CatalogVendor.record_sale: tax = int(round(price * rate)).

    Returns (net_amount, tax_amount), same tuple shape as record_sale.
    """
    from typeclasses.economy import get_economy

    if tax_rate is None:
        tax_rate = outfitters_claims_tax_rate()
    tax_rate = max(0.0, min(1.0, float(tax_rate)))
    tax_amount = int(round(price * tax_rate))
    net_amount = int(price) - tax_amount

    econ = get_economy(create_missing=True)
    player_account = econ.get_character_account(buyer)
    broker_account = econ.get_character_account(broker)
    treasury_account = econ.get_treasury_account("alpha-prime")

    econ.ensure_account(player_account, opening_balance=int(buyer.db.credits or 0))
    econ.ensure_account(broker_account, opening_balance=int(broker.db.credits or 0))
    econ.ensure_account(treasury_account, opening_balance=int(econ.db.tax_pool or 0))

    w_memo = withdraw_memo or "Primary deed purchase"
    econ.withdraw(player_account, int(price), memo=w_memo)
    econ.deposit(broker_account, net_amount, memo=f"Broker revenue ({broker.key})")

    if tax_amount > 0:
        econ.deposit(treasury_account, tax_amount, memo="Sales tax (primary deed)")

    econ.record_transaction(
        tx_type=tx_type,
        amount=int(price),
        from_account=player_account,
        to_account=broker_account,
        memo=memo or f"{buyer.key} primary deed purchase",
        extra={
            "tax_amount": tax_amount,
            "treasury_account": treasury_account,
            "broker_account": broker_account,
        },
    )

    buyer.db.credits = econ.get_balance(player_account)
    broker.db.credits = econ.get_balance(broker_account)
    econ.db.tax_pool = econ.get_balance(treasury_account)

    return net_amount, tax_amount


def _get_property_listings_script():
    found = search_script("property_listings")
    return found[0] if found else None


def is_site_id_property_listed(site_id):
    script = _get_property_listings_script()
    if not script:
        return False
    for ent in script.db.listings or []:
        if ent.get("site_id") == site_id:
            return True
    return False


def get_property_listing_for_site_id(site_id):
    script = _get_property_listings_script()
    if not script:
        return None
    for ent in script.db.listings or []:
        if ent.get("site_id") == site_id:
            return ent
    return None


def list_property_for_sale(seller, site_id, price):
    """Release an idle owned site and add a player-priced claims-market listing."""
    try:
        sid = int(site_id)
    except (TypeError, ValueError):
        return False, "Invalid site id."

    site = None
    for s in search_tag("mining_site", category="mining"):
        if s.id == sid:
            site = s
            break
    if not site:
        return False, "Site not found."
    if not getattr(site.db, "is_claimed", False) or site.db.owner != seller:
        return False, "You do not own that mining site."
    if (site.db.rigs or []) or site.db.mine_operation_active:
        return False, "Undeploy the mine before listing the property."

    script = _get_property_listings_script()
    if not script:
        return False, "Property market is not available."
    if is_site_id_property_listed(sid):
        return False, "That property is already listed."

    try:
        price = int(round(float(price)))
    except (TypeError, ValueError):
        return False, "Invalid price."
    if price < 0:
        return False, "Invalid price."

    listings = list(script.db.listings or [])
    listings.append({"site_id": sid, "seller_id": seller.id, "price": price})
    script.db.listings = listings

    owned = seller.db.owned_sites or []
    seller.db.owned_sites = [x for x in owned if x != site]
    site.db.is_claimed = False
    site.db.owner = None
    site.db.package_tier = None

    return True, f"Property listed for {price:,} cr."


def purchase_property_listing(buyer, site):
    """
    Buyer pays the listed seller; listing removed; MiningClaim granted.
    Returns (success, message, claim_or_none).
    """
    from typeclasses.claim_utils import create_claim_for_site
    from typeclasses.economy import get_economy

    if not site:
        return False, "Site not found.", None

    script = _get_property_listings_script()
    if not script:
        return False, "Property market is not available.", None

    listings = list(script.db.listings or [])
    ent = None
    for e in listings:
        if e.get("site_id") == site.id:
            ent = e
            break
    if not ent:
        return False, "No active listing for this property.", None

    seller_id = ent.get("seller_id")
    price = int(ent.get("price", 0) or 0)
    seller = None
    if seller_id:
        found = search_object("#" + str(seller_id))
        if found:
            seller = found[0]
    if not seller:
        listings = [e for e in listings if e.get("site_id") != site.id]
        script.db.listings = listings
        return False, "Seller is no longer available; listing was removed.", None

    if getattr(seller, "id", None) == getattr(buyer, "id", None):
        return False, "You cannot buy your own listing.", None

    econ = get_economy(create_missing=True)
    credits = econ.get_character_balance(buyer)
    if credits < price:
        return False, f"This property costs {price:,} cr. You have {credits:,} cr.", None

    ok, err = _validate_site_purchasable(site, buyer)
    if not ok:
        return False, err, None

    buyer_acc = econ.get_character_account(buyer)
    seller_acc = econ.get_character_account(seller)
    econ.ensure_account(buyer_acc, opening_balance=int(buyer.db.credits or 0))
    econ.ensure_account(seller_acc, opening_balance=int(seller.db.credits or 0))
    try:
        econ.transfer(buyer_acc, seller_acc, price, memo=f"Property sale: {site.key}")
    except ValueError:
        return False, "Insufficient credits.", None
    econ.sync_character_balance(buyer)
    econ.sync_character_balance(seller)

    ok, err = _validate_site_purchasable(site, buyer)
    if not ok:
        try:
            econ.transfer(seller_acc, buyer_acc, price, memo="Rollback property sale")
            econ.sync_character_balance(buyer)
            econ.sync_character_balance(seller)
        except ValueError:
            pass
        return False, err, None

    listings = [e for e in listings if e.get("site_id") != site.id]
    script.db.listings = listings

    if getattr(site.db, "is_claimed", False):
        try:
            econ.transfer(seller_acc, buyer_acc, price, memo="Rollback property sale")
            econ.sync_character_balance(buyer)
            econ.sync_character_balance(seller)
        except ValueError:
            pass
        script.db.listings = list(script.db.listings or []) + [ent]
        return False, "That site is already claimed.", None

    claim = create_claim_for_site(site, buyer, is_jackpot=False)
    msg = f"Purchased claim deed {claim.key} for {price:,} cr from {seller.key}."
    return True, msg, claim


def _existing_deed_for_site(site):
    """Another MiningClaim already bound to this site (any owner)."""
    if not site:
        return None
    sid = site.id
    for obj in search_tag("mining_claim", category="mining"):
        ref = getattr(obj.db, "site_ref", None)
        if ref is None:
            continue
        try:
            if ref.id == sid:
                return obj
        except Exception:
            continue
    return None


def site_is_claims_market_listable(site):
    """True if the site may appear on the claims market / mine deploy site list."""
    if not site or not site.tags.has("mining_site", category="mining"):
        return False
    if getattr(site.db, "is_claimed", False):
        return False
    if _existing_deed_for_site(site) is not None:
        return False
    if is_site_id_property_listed(site.id):
        return False
    return True


def listing_price_cr(site):
    """
    Deterministic listing from deposit value and hazard (buyer-agnostic).
    Mirrors dashboard estimated value logic, scaled with a hazard factor.
    """
    from typeclasses.mining import get_commodity_bid

    deposit = site.db.deposit or {}
    comp = deposit.get("composition") or {}
    richness = float(deposit.get("richness", 0) or 0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)
    hazard = float(site.db.hazard_level or 0)
    total_tons = base_tons * richness
    ev = 0.0
    for k, frac in comp.items():
        ev += total_tons * float(frac) * float(get_commodity_bid(k))
    hazard_factor = max(0.55, min(1.0, 1.0 - 0.35 * hazard))
    return int(max(500, round(ev * 4 * hazard_factor)))


def claims_market_row_extras(site):
    """
    Fields merged into each claims-market JSON row (only listable sites are serialized).

    Primary (sovereign) listings are attributed to the NanoMegaPlex broker character
    for display; purchase settlement routes net proceeds to that broker (when present)
    and sales tax to the treasury, using the Outfitters vendor tax rate.
    """
    return {
        "listingPriceCr": listing_price_cr(site),
        "purchasable": True,
        "sellerKey": NANOMEGA_REALTY_CHARACTER_KEY,
        "listingKind": "npc",
    }


def _refund_claim_deed_purchase(
    buyer,
    price,
    *,
    net_amount=None,
    tax_amount=None,
    broker=None,
    vendor=None,
):
    """
    Reverse payment after a failed post-pay step.
    Refund full ``price`` to buyer; claw back net from broker or vendor ledger; claw back tax from treasury.
    Raw-withdraw path: pass broker=vendor=None and net_amount=None (buyer-only refund).
    """
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    pa = econ.get_character_account(buyer)
    econ.deposit(pa, int(price), memo="Refund: claim deed purchase rolled back")
    econ.sync_character_balance(buyer)

    if broker is not None and net_amount is not None:
        ba = econ.get_character_account(broker)
        try:
            econ.withdraw(ba, int(net_amount), memo="Refund clawback broker")
        except ValueError:
            pass
        econ.sync_character_balance(broker)
    elif vendor is not None and net_amount is not None:
        vid = getattr(vendor.db, "vendor_id", None) or "vendor"
        va = econ.get_vendor_account(vid)
        try:
            econ.withdraw(va, int(net_amount), memo="Refund clawback vendor")
        except ValueError:
            pass
        vendor.db.credits = econ.get_balance(va)

    if tax_amount and int(tax_amount) > 0:
        ta = econ.get_treasury_account("alpha-prime")
        try:
            econ.withdraw(ta, int(tax_amount), memo="Refund clawback tax")
        except ValueError:
            pass
        econ.db.tax_pool = econ.get_balance(ta)


def _validate_site_purchasable(site, buyer):
    """Return (ok, error_message)."""
    if not site or not site.tags.has("mining_site", category="mining"):
        return False, "That is not a valid mining site."
    if getattr(site.db, "is_claimed", False):
        return False, "That site is already claimed."
    existing = _existing_deed_for_site(site)
    if existing:
        if getattr(existing.location, "id", None) == getattr(buyer, "id", None):
            return False, "You already hold a claim deed for this site."
        return False, "This site already has an outstanding claim deed."
    return True, None


def _resolve_mining_site_by_key(site_key):
    key = (site_key or "").strip()
    if not key:
        return None
    for obj in search_object(key):
        if obj.tags.has("mining_site", category="mining"):
            return obj
    return None


def purchase_site_claim_deed(buyer, site_key):
    """
    Charge the buyer and grant a MiningClaim for the listed unclaimed site.

    Returns (success: bool, message: str, claim_or_none).
    """
    from typeclasses.claim_utils import create_claim_for_site
    from typeclasses.economy import get_economy

    site = _resolve_mining_site_by_key(site_key)
    if not site:
        return False, f"No mining site matching '{site_key}'.", None

    ok, err = _validate_site_purchasable(site, buyer)
    if not ok:
        return False, err, None

    price = listing_price_cr(site)
    econ = get_economy(create_missing=True)
    credits = econ.get_character_balance(buyer)
    if credits < price:
        return False, f"This deed costs {price:,} cr. You have {credits:,} cr.", None

    ok, err = _validate_site_purchasable(site, buyer)
    if not ok:
        return False, err, None

    broker = get_primary_deed_broker()
    vendor = _get_claims_vendor()
    net_amount = tax_amount = None
    payment_broker = None
    payment_vendor = None

    if broker:
        net_amount, tax_amount = collect_primary_deed_sale(
            buyer,
            price,
            broker,
            tx_type="claim_deed_purchase",
            memo=f"{buyer.key} purchased claim deed for {site.key}",
            withdraw_memo="Claim deed purchase",
        )
        payment_broker = broker
    elif vendor:
        net_amount, tax_amount = vendor.record_sale(
            buyer,
            price,
            tx_type="claim_deed_purchase",
            memo=f"{buyer.key} purchased claim deed for {site.key}",
            withdraw_memo="Claim deed purchase",
        )
        payment_vendor = vendor
    else:
        account = econ.get_character_account(buyer)
        econ.ensure_account(account, opening_balance=int(buyer.db.credits or 0))
        try:
            econ.withdraw(account, price, memo="Claim deed purchase")
        except ValueError:
            return False, "Insufficient credits.", None
        econ.sync_character_balance(buyer)

    ok, err = _validate_site_purchasable(site, buyer)
    if not ok:
        _refund_claim_deed_purchase(
            buyer,
            price,
            net_amount=net_amount,
            tax_amount=tax_amount,
            broker=payment_broker,
            vendor=payment_vendor,
        )
        return False, err, None

    if getattr(site.db, "is_claimed", False):
        _refund_claim_deed_purchase(
            buyer,
            price,
            net_amount=net_amount,
            tax_amount=tax_amount,
            broker=payment_broker,
            vendor=payment_vendor,
        )
        return False, "That site is already claimed.", None

    existing = _existing_deed_for_site(site)
    if existing:
        _refund_claim_deed_purchase(
            buyer,
            price,
            net_amount=net_amount,
            tax_amount=tax_amount,
            broker=payment_broker,
            vendor=payment_vendor,
        )
        if getattr(existing.location, "id", None) == getattr(buyer, "id", None):
            return False, "You already hold a claim deed for this site.", None
        return False, "This site already has an outstanding claim deed.", None

    claim = create_claim_for_site(site, buyer, is_jackpot=False)
    msg = f"Purchased claim deed {claim.key} for {price:,} cr."
    if broker or vendor:
        msg += f" Remaining balance: {econ.get_character_balance(buyer):,} cr."
    return True, msg, claim
