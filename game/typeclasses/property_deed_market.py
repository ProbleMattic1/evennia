"""
Secondary market for property claim deeds (list / browse / buy), per venue hub escrow.
"""

from evennia import create_script, search_object, search_script

from typeclasses.economy import get_economy
from typeclasses.property_claims import (
    PROPERTY_CLAIM_CATEGORY,
    PROPERTY_CLAIM_TAG,
    strip_property_claim_key_prefix,
)
from typeclasses.property_deed_listings import PropertyDeedListingsScript
from typeclasses.property_title_sync import sync_property_title_from_deed_location
from world.venue_resolve import hub_room_for_venue, venue_id_for_object
from world.venues import all_venue_ids


def property_deed_listings_script_key(venue_id: str) -> str:
    if venue_id == "nanomega_core":
        return "property_deed_listings"
    return f"property_deed_listings__{venue_id}"


def get_property_deed_listings_script(venue_id: str, create_missing=False):
    key = property_deed_listings_script_key(venue_id)
    found = search_script(key)
    if found:
        return found[0]
    if create_missing:
        return create_script(PropertyDeedListingsScript, key=key)
    return None


def _property_deed_container_for_venue(venue_id: str):
    hub = hub_room_for_venue(venue_id)
    if not hub:
        return None
    for obj in hub.contents:
        if getattr(obj.db, "is_property_deed_listings_container", False):
            return obj
    return None


def list_property_deed_for_sale(seller, claim_id, price):
    """
    List a property deed from seller inventory. Moves deed into hub escrow container.
    Returns (success: bool, message: str).
    """
    try:
        cid = int(claim_id)
    except (TypeError, ValueError):
        return False, "Invalid claim id."

    if price is None or (isinstance(price, (int, float)) and price < 0):
        return False, "Price must be a non-negative number."
    price = int(round(float(price)))

    claim = None
    for obj in seller.contents:
        if obj.id == cid and obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY):
            claim = obj
            break
    if not claim:
        return False, "You do not have that property deed in your inventory."

    vid = venue_id_for_object(seller) or "nanomega_core"
    script = get_property_deed_listings_script(vid, create_missing=True)
    if not script:
        return False, "Property deed market is not available."

    container = _property_deed_container_for_venue(vid)
    if not container:
        return False, "Property deed market is not available."

    listings = list(script.db.listings or [])
    for ent in listings:
        if ent.get("claim_id") == cid:
            return False, "That deed is already listed."

    claim.move_to(container)
    listings.append({"claim_id": cid, "seller_id": seller.id, "price": price})
    script.db.listings = listings
    sync_property_title_from_deed_location(claim)
    from world.station_services.contracts import try_complete_contract

    try_complete_contract(seller, "list_property_deed", venue_id=vid)
    try:
        from world.challenges.challenge_signals import emit as _c_emit
        _c_emit(seller, "deed_listed", {"claim_id": cid, "price": price})
    except Exception:
        pass
    return True, f"{strip_property_claim_key_prefix(claim.key)} listed for {price:,} cr."


def _deed_listings_for_venue(venue_id: str):
    script = get_property_deed_listings_script(venue_id, create_missing=False)
    if not script:
        return []

    container = _property_deed_container_for_venue(venue_id)
    if not container:
        return []

    from typeclasses.property_claims import get_property_claim_kind

    result = []
    valid = []
    for ent in script.db.listings or []:
        cid = ent.get("claim_id")
        seller_id = ent.get("seller_id")
        price = ent.get("price", 0)
        claim = None
        for obj in container.contents:
            if obj.id == cid and obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY):
                claim = obj
                break
        if not claim:
            continue
        valid.append(ent)
        seller_key = "?"
        if seller_id:
            found = search_object("#" + str(seller_id))
            if found and hasattr(found[0], "key"):
                seller_key = found[0].key
        result.append(
            {
                "claimId": cid,
                "key": strip_property_claim_key_prefix(claim.key),
                "lotKey": getattr(claim.db, "lot_key", None) or "",
                "kind": get_property_claim_kind(claim),
                "price": int(price),
                "sellerKey": seller_key,
                "venueId": venue_id,
            }
        )
    script.db.listings = valid
    return result


def get_property_deed_listings(venue_id=None):
    """
    Active listings. If venue_id is None, merge all venues.
    """
    if venue_id:
        return _deed_listings_for_venue(venue_id)
    merged = []
    for vid in all_venue_ids():
        merged.extend(_deed_listings_for_venue(vid))
    return merged


def buy_listed_property_deed(buyer, claim_id):
    """
    Pay seller, move deed to buyer, update lot recorded owner, prune listing.
    """
    try:
        cid = int(claim_id)
    except (TypeError, ValueError):
        return False, "Invalid claim id."

    script = None
    container = None
    for vid in all_venue_ids():
        s = get_property_deed_listings_script(vid, create_missing=False)
        c = _property_deed_container_for_venue(vid)
        if not s or not c:
            continue
        for obj in c.contents:
            if obj.id == cid and obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY):
                script = s
                container = c
                break
        if script:
            break

    if not script or not container:
        return False, "Property deed market is not available."

    listings = script.db.listings or []
    entry = None
    claim = None
    for obj in container.contents:
        if obj.id == cid and obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY):
            claim = obj
            break
    if not claim:
        return False, "That deed is not for sale or has been sold."

    for ent in listings:
        if ent.get("claim_id") == cid:
            entry = ent
            break
    if not entry:
        return False, "Listing not found."

    price = int(entry.get("price", 0))
    seller_id = entry.get("seller_id")
    if not seller_id:
        return False, "Invalid listing."

    found = search_object("#" + str(seller_id))
    seller = found[0] if found else None
    if not seller:
        return False, "Seller no longer exists."

    econ = get_economy(create_missing=False)
    if not econ:
        return False, "Economy system unavailable."

    balance = econ.get_character_balance(buyer)
    if balance < price:
        return False, f"You need {price:,} cr but only have {balance:,} cr."

    buyer_acct = econ.get_character_account(buyer)
    seller_acct = econ.get_character_account(seller)
    econ.ensure_account(buyer_acct, opening_balance=int(buyer.db.credits or 0))
    econ.ensure_account(seller_acct, opening_balance=int(seller.db.credits or 0))
    econ.transfer(buyer_acct, seller_acct, price, memo="property deed sale")
    buyer.db.credits = econ.get_character_balance(buyer)
    seller.db.credits = econ.get_character_balance(seller)

    lot = getattr(claim.db, "lot_ref", None)
    if lot:
        lot.db.owner = buyer

    claim.move_to(buyer)
    script.db.listings = [e for e in listings if e.get("claim_id") != cid]
    sync_property_title_from_deed_location(claim)
    try:
        from world.challenges.challenge_signals import emit as _c_emit
        _c_emit(buyer, "deed_purchased", {"claim_id": cid, "price": price})
        _c_emit(seller, "deed_sold", {"claim_id": cid, "price": price})
    except Exception:
        pass
    return True, f"You bought {strip_property_claim_key_prefix(claim.key)} for {price:,} cr."
