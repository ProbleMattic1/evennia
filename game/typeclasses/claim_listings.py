"""
Player-listed mining claim deeds (inventory resale), per venue hub escrow.

Script db.listings = [{"claim_id": int, "seller_id": int, "price": int}, ...]
"""

from evennia import create_script, search_object, search_script

from typeclasses.scripts import Script
from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids


class ClaimListingsScript(Script):
    def at_script_creation(self):
        if not self.db.listings:
            self.db.listings = []


def claim_listings_script_key(venue_id: str) -> str:
    if venue_id == "nanomega_core":
        return "claim_listings"
    return f"claim_listings__{venue_id}"


def get_claim_listings_script(venue_id: str, create_missing=False):
    key = claim_listings_script_key(venue_id)
    found = search_script(key)
    if found:
        return found[0]
    if create_missing:
        return create_script(ClaimListingsScript, key=key)
    return None


def _container_for_venue(venue_id: str):
    hub = hub_room_for_venue(venue_id)
    if not hub:
        return None
    for obj in hub.contents:
        if getattr(obj.db, "is_claim_listings_container", False):
            return obj
    return None


def _venue_id_for_claim_container(claim):
    container = claim.location if claim else None
    if not container:
        return None
    hub = container.location
    if not hub:
        return None
    return getattr(hub.db, "venue_id", None)


def claim_is_publicly_listed(claim):
    """True if claim is in escrow and has an active listing entry."""
    vid = _venue_id_for_claim_container(claim)
    if not vid:
        return False
    script = get_claim_listings_script(vid, create_missing=False)
    container = _container_for_venue(vid)
    if not script or not container or claim.location != container:
        return False
    return any(
        ent.get("claim_id") == claim.id for ent in (script.db.listings or [])
    )


def list_claim_for_sale(seller, claim_id, price):
    """
    List a MiningClaim from seller's inventory. Moves claim to escrow container.
    Returns (success: bool, message: str).
    """
    from world.venue_resolve import venue_id_for_object

    try:
        cid = int(claim_id)
    except (TypeError, ValueError):
        return False, "Invalid claim id."

    if price is None:
        return False, "Price must be a non-negative number."
    try:
        price = int(round(float(price)))
    except (TypeError, ValueError):
        return False, "Invalid price."
    if price < 0:
        return False, "Invalid price."

    claim = None
    for obj in seller.contents:
        if obj.id == cid and obj.tags.has("mining_claim", category="mining"):
            claim = obj
            break
    if not claim:
        return False, "You do not have that mining claim in your inventory."

    site = getattr(claim.db, "site_ref", None)
    if not site or not hasattr(site, "db"):
        return False, "That claim is invalid."
    if getattr(site.db, "is_claimed", False):
        return False, "That site is already developed; you cannot list this deed."

    vid = venue_id_for_object(seller) or "nanomega_core"
    script = get_claim_listings_script(vid, create_missing=True)
    container = _container_for_venue(vid)
    if not script or not container:
        return False, "Claim listings are not available."

    listings = list(script.db.listings or [])
    for ent in listings:
        if ent.get("claim_id") == cid:
            return False, "That claim is already listed."

    claim.move_to(container)
    listings.append({"claim_id": cid, "seller_id": seller.id, "price": price})
    script.db.listings = listings
    from world.station_services.contracts import try_complete_contract

    try_complete_contract(seller, "list_claim", venue_id=vid)
    return True, f"{claim.key} listed for {price:,} cr."


def _rows_for_venue(venue_id: str):
    from typeclasses.mining import _resource_rarity_tier, _volume_tier

    script = get_claim_listings_script(venue_id, create_missing=False)
    container = _container_for_venue(venue_id)
    if not script or not container:
        return []

    valid = []
    result = []
    listings = list(script.db.listings or [])

    for ent in listings:
        cid = ent.get("claim_id")
        seller_id = ent.get("seller_id")
        price = int(ent.get("price", 0) or 0)
        claim = None
        for obj in container.contents:
            if obj.id == cid and obj.tags.has("mining_claim", category="mining"):
                claim = obj
                break
        if not claim:
            continue

        site = getattr(claim.db, "site_ref", None)
        if not site or not hasattr(site, "db"):
            continue

        valid.append(ent)

        seller_key = "?"
        if seller_id:
            found = search_object("#" + str(seller_id))
            if found and hasattr(found[0], "key"):
                seller_key = found[0].key

        room = site.location
        room_key = room.key if room else "unknown"
        deposit = site.db.deposit or {}
        comp = deposit.get("composition", {})
        families = ", ".join(sorted(comp.keys())) if comp else "unknown"
        richness = float(deposit.get("richness", 0.0))
        hazard = float(site.db.hazard_level or 0.0)
        base_tons = float(deposit.get("base_output_tons", 0) or 0)
        volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
        resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(comp)
        if hazard <= 0.20:
            hazard_label = "Low"
        elif hazard <= 0.50:
            hazard_label = "Medium"
        else:
            hazard_label = "High"

        result.append({
            "claimId": cid,
            "claimKey": claim.key,
            "siteKey": site.key,
            "roomKey": room_key,
            "resources": families,
            "richness": round(richness, 2),
            "volumeTier": volume_tier,
            "volumeTierCls": volume_tier_cls,
            "resourceRarityTier": resource_rarity_tier,
            "resourceRarityTierCls": resource_rarity_tier_cls,
            "hazardLevel": round(hazard, 2),
            "hazardLabel": hazard_label,
            "baseOutputTons": base_tons,
            "listingPriceCr": price,
            "purchasable": True,
            "playerListing": True,
            "listingKind": "deed",
            "sellerKey": seller_key,
            "venueId": venue_id,
        })

    script.db.listings = valid
    return result


def get_claim_listings_rows(venue_id=None):
    """
    Rows merged into claims-market JSON. If venue_id is None, merge all venues.
    """
    if venue_id:
        return _rows_for_venue(venue_id)
    merged = []
    for vid in all_venue_ids():
        merged.extend(_rows_for_venue(vid))
    return merged


def buy_listed_claim(buyer, claim_id):
    """Transfer credits; move claim from escrow to buyer. Returns (success, message)."""
    from typeclasses.economy import get_economy

    try:
        cid = int(claim_id)
    except (TypeError, ValueError):
        return False, "Invalid claim id."

    script = None
    container = None
    vid_found = None
    for vid in all_venue_ids():
        s = get_claim_listings_script(vid, create_missing=False)
        c = _container_for_venue(vid)
        if not s or not c:
            continue
        for obj in c.contents:
            if obj.id == cid and obj.tags.has("mining_claim", category="mining"):
                script = s
                container = c
                vid_found = vid
                break
        if script:
            break

    if not script or not container:
        return False, "Claim listings are not available."

    claim = None
    for obj in container.contents:
        if obj.id == cid and obj.tags.has("mining_claim", category="mining"):
            claim = obj
            break
    if not claim:
        return False, "That claim is not for sale or has been sold."

    listings = list(script.db.listings or [])
    entry = None
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

    if getattr(seller, "id", None) == getattr(buyer, "id", None):
        return False, "You cannot buy your own listing."

    site = getattr(claim.db, "site_ref", None)
    if not site or getattr(site.db, "is_claimed", False):
        return False, "That claim is no longer valid."

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
    econ.transfer(buyer_acct, seller_acct, price, memo="mining claim sale")
    buyer.db.credits = econ.get_character_balance(buyer)
    seller.db.credits = econ.get_character_balance(seller)

    claim.move_to(buyer)
    script.db.listings = [e for e in listings if e.get("claim_id") != cid]
    return True, f"You bought {claim.key} for {price:,} cr."
