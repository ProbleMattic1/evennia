"""
Mining package delivery and undeploy system.

deliver_mining_package(buyer, package_template, site_query)
    Resolves unclaimed site, spawns components, claims site, deploys, starts production.
    Used when deploying from a template (legacy / internal).

deploy_package_from_inventory(buyer, package_obj, claim_obj)
    Consumes claim and package; deploys at the claim's site.
    claim_obj must be a MiningClaim in buyer's inventory.

undeploy_mine_to_package(buyer, site)
    Teardown active operation: rig/storage/hauler to inventory; site stays claimed
    by buyer (idle). Does not create a new package.

reactivate_mine_from_package(buyer, package_obj, site)
    Restart operations at an idle owned site using inventory equipment or spawns.
"""

from evennia import create_object, search_object


def _deploy_profile_for_tier_string(tier_str):
    """Map legacy SKU keys or deploy_profile ids to deploy_profile for matching."""
    from world.bootstrap_mining_packages import MINING_PACKAGES

    if not tier_str:
        return None
    for spec in MINING_PACKAGES:
        if spec["key"] == tier_str:
            return spec.get("deploy_profile") or tier_str
    for spec in MINING_PACKAGES:
        if spec.get("deploy_profile") == tier_str:
            return spec.get("deploy_profile") or tier_str
    return tier_str


def _get_package_spec_by_tier(package_tier):
    """Look up MINING_PACKAGES spec by display key or deploy_profile. Returns None if not found."""
    from world.bootstrap_mining_packages import MINING_PACKAGES

    if not package_tier:
        return None
    for spec in MINING_PACKAGES:
        if spec["key"] == package_tier:
            return spec
    for spec in MINING_PACKAGES:
        if spec.get("deploy_profile") == package_tier:
            return spec
    return None


def _find_unclaimed_site(site_query):
    """
    Find an unclaimed MiningSite by partial room or site key match.
    Returns (site_object, site_room) or (None, None).
    """
    from evennia import search_tag
    sites = search_tag("mining_site", category="mining")
    query = site_query.strip().lower()
    for site in sites:
        if getattr(site.db, "is_claimed", False):
            continue
        site_key_lower = (site.key or "").lower()
        room_key_lower = (site.location.key if site.location else "").lower()
        if query in site_key_lower or query in room_key_lower:
            return site, site.location
    return None, None


def _spawn_rig(spec, site_room, buyer):
    from typeclasses.mining import MiningRig
    rig = create_object(
        MiningRig,
        key=spec["key"],
        location=site_room,
        home=site_room,
    )
    rig.db.desc = spec.get("desc", "A mining extraction platform.")
    rig.db.rig_rating = float(spec.get("rig_rating", 1.0))
    rig.db.owner = buyer
    rig.locks.add("get:false()")
    return rig


def _spawn_storage(spec, site_room, buyer):
    from typeclasses.mining import MiningStorage
    storage = create_object(
        MiningStorage,
        key=spec["key"],
        location=site_room,
        home=site_room,
    )
    storage.db.desc = spec.get("desc", "An ore storage unit.")
    storage.db.capacity_tons = float(spec.get("capacity_tons", 500.0))
    storage.db.owner = buyer
    return storage


def _spawn_hauler(spec, site_room, buyer):
    from typeclasses.vehicles import Hauler
    from typeclasses.haulers import set_hauler_next_cycle
    hauler = create_object(
        Hauler,
        key=spec["key"],
        location=site_room,
        home=site_room,
    )
    hauler.db.desc = spec.get("desc", "An autonomous ore hauler.")
    hauler.db.is_template = False
    hauler.db.owner = buyer
    hauler.db.allowed_boarders = [buyer]
    hauler.db.state = "docked"
    hauler.db.cargo = {}
    hauler.db.cargo_capacity_tons = float(spec.get("cargo_capacity_tons", 50.0))
    hauler.db.hauler_owner = buyer
    hauler.db.hauler_mine_room = None
    hauler.db.hauler_refinery_room = None
    hauler.db.hauler_state = "idle"
    hauler.db.hauler_upgrades = {}
    hauler.db.hauler_base_cycle_hours = float(spec.get("cycle_hours", 4.0))
    # Default: sell raw ore for immediate credits. Use `setdelivery <hauler> process`
    # to queue ore for refining at the plant instead.
    hauler.db.hauler_delivery_mode = "sell"
    hauler.tags.add("autonomous_hauler", category="mining")
    hauler.locks.add("get:false()")
    return hauler


def _take_or_spawn_rig(spec, site_room, buyer):
    """Use a loose rig in buyer inventory, or spawn a new one."""
    for obj in list(buyer.contents):
        if getattr(obj, "destination", None):
            continue
        if obj.tags.has("mining_rig", category="mining") and not getattr(obj.db, "is_installed", False):
            obj.move_to(site_room, quiet=True)
            obj.home = site_room
            obj.db.owner = buyer
            obj.locks.add("get:false()")
            return obj
    return _spawn_rig(spec, site_room, buyer)


def _take_or_spawn_storage(spec, site_room, buyer):
    for obj in list(buyer.contents):
        if getattr(obj, "destination", None):
            continue
        if obj.tags.has("mining_storage", category="mining") and not getattr(obj.db, "site", None):
            obj.move_to(site_room, quiet=True)
            obj.home = site_room
            obj.db.owner = buyer
            return obj
    return _spawn_storage(spec, site_room, buyer)


def _take_or_spawn_hauler(spec, site_room, buyer):
    for obj in list(buyer.contents):
        if getattr(obj, "destination", None):
            continue
        if obj.tags.has("autonomous_hauler", category="mining") and obj.location == buyer:
            obj.move_to(site_room, quiet=True)
            obj.home = site_room
            obj.db.owner = buyer
            obj.db.hauler_owner = buyer
            obj.db.allowed_boarders = [buyer]
            obj.locks.add("get:false()")
            return obj
    return _spawn_hauler(spec, site_room, buyer)


def _deploy_components_at_site(buyer, site, site_room, components, package_tier):
    """Core deployment: spawn rig/storage/hauler, claim site, link, start cycles."""
    from typeclasses.haulers import set_hauler_next_cycle

    refinery_rooms = search_object("Aurnom Ore Processing Plant")
    refinery_room = refinery_rooms[0] if refinery_rooms else None
    if not refinery_room:
        return False, "No processing plant found. Contact an administrator."

    rig = storage = hauler = None
    for comp in components:
        ct = comp.get("type")
        if ct == "rig":
            rig = _spawn_rig(comp, site_room, buyer)
        elif ct == "storage":
            storage = _spawn_storage(comp, site_room, buyer)
        elif ct == "hauler":
            hauler = _spawn_hauler(comp, site_room, buyer)

    if not rig or not storage or not hauler:
        return False, "Package is missing one or more components."

    site.db.is_claimed = True
    site.db.owner = buyer
    site.db.package_tier = package_tier
    owned_sites = buyer.db.owned_sites or []
    if site not in owned_sites:
        owned_sites.append(site)
    buyer.db.owned_sites = owned_sites

    rig.install(site, owner=buyer)
    site.db.active_rig = rig

    site.db.linked_storage = storage
    storage.db.site = site
    storage.db.owner = buyer

    hauler.db.hauler_mine_room = site_room
    hauler.db.hauler_refinery_room = refinery_room
    hauler.db.hauler_state = "at_mine"
    set_hauler_next_cycle(hauler)

    owned_vehicles = buyer.db.owned_vehicles or []
    if hauler not in owned_vehicles:
        owned_vehicles.append(hauler)
    buyer.db.owned_vehicles = owned_vehicles

    site.db.mine_operation_active = True
    site.schedule_next_cycle()

    cycle_h = int(hauler.db.hauler_base_cycle_hours or 4)
    return True, (
        f"Mining operation deployed at {site.key}.\n"
        f"  Site: {site_room.key}\n"
        f"  Rig: {rig.key}  Storage: {storage.key}  Hauler: {hauler.key}\n"
        f"  Mining delivery: UTC 30m grid  Hauler cycle: {cycle_h}h\n"
        f"  Ore will flow to {refinery_room.key} automatically.\n"
        f"  Use mines and haulerstatus to monitor progress."
    )


def _reactivate_components_at_site(buyer, site, site_room, components, package_tier):
    """Restore rig/storage/hauler at an idle owned site; reuse inventory when possible."""
    from typeclasses.haulers import set_hauler_next_cycle

    refinery_rooms = search_object("Aurnom Ore Processing Plant")
    refinery_room = refinery_rooms[0] if refinery_rooms else None
    if not refinery_room:
        return False, "No processing plant found. Contact an administrator."

    rig = storage = hauler = None
    for comp in components:
        ct = comp.get("type")
        if ct == "rig":
            rig = _take_or_spawn_rig(comp, site_room, buyer)
        elif ct == "storage":
            storage = _take_or_spawn_storage(comp, site_room, buyer)
        elif ct == "hauler":
            hauler = _take_or_spawn_hauler(comp, site_room, buyer)

    if not rig or not storage or not hauler:
        return False, "Could not prepare rig, storage, and hauler. Check your inventory or buy a matching package."

    site.db.package_tier = package_tier
    site.db.mine_operation_active = True

    rig.install(site, owner=buyer)
    site.db.active_rig = rig

    site.db.linked_storage = storage
    storage.db.site = site
    storage.db.owner = buyer

    hauler.db.hauler_owner = buyer
    hauler.db.allowed_boarders = [buyer]
    hauler.db.hauler_mine_room = site_room
    hauler.db.hauler_refinery_room = refinery_room
    hauler.db.hauler_state = "at_mine"
    set_hauler_next_cycle(hauler)

    owned_vehicles = buyer.db.owned_vehicles or []
    if hauler not in owned_vehicles:
        owned_vehicles.append(hauler)
    buyer.db.owned_vehicles = owned_vehicles

    site.schedule_next_cycle()

    cycle_h = int(hauler.db.hauler_base_cycle_hours or 4)
    return True, (
        f"Mining operation reactivated at {site.key}.\n"
        f"  Rig: {rig.key}  Storage: {storage.key}  Hauler: {hauler.key}\n"
        f"  Mining delivery: UTC 30m grid  Hauler cycle: {cycle_h}h\n"
        f"  Ore will flow to {refinery_room.key} automatically."
    )


def deliver_mining_package(buyer, package_template, site_query):
    """
    Resolve unclaimed site, spawn components from template, deploy.
    Returns (success: bool, message: str).
    """
    site, site_room = _find_unclaimed_site(site_query)
    if not site:
        return False, f"No unclaimed mining site matching '{site_query}'. Use |wavailableclaims|n to list options."

    components = package_template.db.package_components or []
    if not components:
        return False, "This package has no components configured. Contact an administrator."

    package_tier = getattr(package_template.db, "package_tier", None) or package_template.key
    return _deploy_components_at_site(buyer, site, site_room, components, package_tier)


def deploy_package_from_inventory(buyer, package_obj, claim_obj):
    """
    Consume claim and package; deploy at the claim's site.
    claim_obj must be a MiningClaim in buyer's inventory.
    Returns (success: bool, message: str).
    """
    if package_obj.location != buyer:
        return False, "You do not have that package in your inventory."
    if claim_obj.location != buyer:
        return False, "You do not have that claim in your inventory."
    if not claim_obj.tags.has("mining_claim", category="mining"):
        return False, "That is not a mining claim."

    site = getattr(claim_obj.db, "site_ref", None)
    if not site or not hasattr(site, "db"):
        return False, "That claim is invalid or expired."
    if getattr(site.db, "is_claimed", False):
        site_name = site.location.key if site.location else site.key
        return False, f"{site_name} is already claimed."

    package_tier = getattr(package_obj.db, "package_tier", None)
    if not package_tier:
        return False, "That item is not a deployable mining package."

    spec = _get_package_spec_by_tier(package_tier)
    if not spec:
        return False, f"Unknown package tier '{package_tier}'. Contact an administrator."

    components = spec.get("components") or []
    if not components:
        return False, "Package has no components configured."

    site_room = site.location
    if not site_room:
        return False, "Claim site has no room."

    allowed = getattr(site.db, "allowed_purposes", None) or ["mining"]
    if "mining" not in allowed:
        return False, "This site cannot be used for mining."

    ok, msg = _deploy_components_at_site(buyer, site, site_room, components, package_tier)
    if ok:
        package_obj.delete()
        claim_obj.delete()
    return ok, msg


def reactivate_mine_inventory_only(buyer, site):
    """
    Restart an idle owned site using rig/storage/hauler already in inventory.
    Returns (success: bool, message: str).
    """
    if not getattr(site.db, "is_claimed", False) or site.db.owner != buyer:
        return False, "You do not own this mining site."
    if getattr(site.db, "mine_operation_active", True):
        return False, "This mine is already operating."

    package_tier = getattr(site.db, "package_tier", None)
    if not package_tier:
        return False, "This site has no recorded package tier."

    spec = _get_package_spec_by_tier(package_tier)
    if not spec:
        return False, f"Unknown package tier '{package_tier}'. Contact an administrator."

    components = spec.get("components") or []
    if not components:
        return False, "Package has no components configured."

    site_room = site.location
    if not site_room:
        return False, "Site has no room."

    return _reactivate_components_at_site(buyer, site, site_room, components, package_tier)


def reactivate_mine_from_package(buyer, package_obj, site):
    """
    Consume a mining package and restart an idle owned site.
    Returns (success: bool, message: str).
    """
    if package_obj.location != buyer:
        return False, "You do not have that package in your inventory."
    if not getattr(site.db, "is_claimed", False) or site.db.owner != buyer:
        return False, "You do not own this mining site."
    if getattr(site.db, "mine_operation_active", True):
        return False, "This mine is already operating."

    package_tier = getattr(package_obj.db, "package_tier", None)
    if not package_tier:
        return False, "That item is not a deployable mining package."
    site_tier = getattr(site.db, "package_tier", None)
    if _deploy_profile_for_tier_string(package_tier) != _deploy_profile_for_tier_string(site_tier):
        return False, "Package tier does not match this site."

    spec = _get_package_spec_by_tier(package_tier)
    if not spec:
        return False, f"Unknown package tier '{package_tier}'. Contact an administrator."

    components = spec.get("components") or []
    if not components:
        return False, "Package has no components configured."

    site_room = site.location
    if not site_room:
        return False, "Site has no room."

    ok, msg = _reactivate_components_at_site(buyer, site, site_room, components, package_tier)
    if ok:
        package_obj.delete()
    return ok, msg


def _estimated_package_value_from_site(site):
    """
    Compute estimated value for a package based on the site's deposit richness.
    Uses same formula as claimSpecs.estimatedValuePerCycle (value per cycle).
    Returns int (credits).
    """
    from typeclasses.mining import get_commodity_bid

    deposit = site.db.deposit or {}
    richness = float(deposit.get("richness", 0) or 0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)
    comp = deposit.get("composition") or {}
    estimated_value = 0
    total_tons = base_tons * richness
    for k, frac in comp.items():
        price = get_commodity_bid(k)
        estimated_value += total_tons * float(frac) * price
    return int(round(estimated_value))


def undeploy_mine_to_package(buyer, site):
    """
    Stop operations at an owned mine: delete rig, storage, and hauler; recreate
    the deployable package and return it to buyer's inventory.
    Site stays claimed by buyer (idle). Any ore in storage is lost.
    Returns (success: bool, message: str, meta: dict).
    """
    if not getattr(site.db, "is_claimed", False) or site.db.owner != buyer:
        return False, "You do not own this mining site.", None

    package_tier = getattr(site.db, "package_tier", None)
    if not package_tier:
        return False, "This site has no recorded package tier; cannot undeploy.", None

    spec = _get_package_spec_by_tier(package_tier)
    template_key = spec["key"] if spec else package_tier

    if not getattr(site.db, "mine_operation_active", True):
        return False, "This mine is not operating.", None

    rig = site.db.active_rig
    storage = site.db.linked_storage
    hauler = None
    for v in list(buyer.db.owned_vehicles or []):
        obj = v if hasattr(v, "tags") else None
        if not obj:
            continue
        if obj.tags.has("autonomous_hauler", category="mining"):
            if getattr(obj.db, "hauler_mine_room", None) == site.location:
                hauler = obj
                break

    site.db.next_cycle_at = None
    site.db.active_rig = None
    site.db.linked_storage = None
    site.db.mine_operation_active = False

    if rig:
        rig.uninstall()
        rig.delete()
    if storage:
        storage.delete()
    if hauler:
        if hauler in (buyer.db.owned_vehicles or []):
            owned = [v for v in buyer.db.owned_vehicles if v != hauler]
            buyer.db.owned_vehicles = owned
        hauler.delete()

    # Recreate the package from the template so it can be redeployed.
    template_matches = search_object(template_key)
    template = next(
        (
            o for o in template_matches
            if getattr(o.db, "is_template", False) and getattr(o.db, "is_sale_package", False)
        ),
        None,
    )

    new_pkg = None
    if template:
        new_pkg = template.copy(new_key=template.key)
        new_pkg.db.is_template = False
        new_pkg.db.package_tier = getattr(template.db, "package_tier", None) or template.key
        new_pkg.db.owner = buyer
        new_pkg.tags.add("mining_package", category="mining")
        new_pkg.locks.add("get:true();drop:true();give:true()")
        new_pkg.move_to(buyer, quiet=True)

    site_name = site.location.key if site.location else site.key
    meta = {"package_tier": package_tier, "package_id": new_pkg.id if new_pkg else None}

    if new_pkg:
        return True, (
            f"Mine at {site_name} undeployed.\n"
            f"  {new_pkg.key} returned to your inventory.\n"
            f"  Reactivate with deploymine, or list the property on the claims market."
        ), meta
    return True, (
        f"Mine at {site_name} undeployed.\n"
        f"  Warning: could not recreate package (tier '{package_tier}' template not found).\n"
        f"  Contact an administrator."
    ), meta


def _get_package_listings_script():
    """Return the package listings script, or None if not found."""
    from evennia import search_script
    found = search_script("package_listings")
    return found[0] if found else None


def _get_listings_container():
    """Return the container object for listed packages, or None."""
    from evennia import search_object
    from world.bootstrap_hub import get_hub_room
    hub = get_hub_room()
    if not hub:
        return None
    for obj in hub.contents:
        if obj.key == "Package Listings" and getattr(obj.db, "is_listings_container", False):
            return obj
    return None


def list_package_for_sale(seller, package_id, price):
    """
    List a mining package for sale. Package must be in seller's inventory.
    Returns (success: bool, message: str).
    """
    from evennia import search_object

    try:
        pid = int(package_id)
    except (TypeError, ValueError):
        return False, "Invalid package id."

    if price is None or (isinstance(price, (int, float)) and price < 0):
        return False, "Price must be a non-negative number."
    price = int(round(float(price)))

    package = None
    for obj in seller.contents:
        if obj.id == pid and obj.tags.has("mining_package", category="mining"):
            package = obj
            break
    if not package:
        return False, "You do not have that mining package in your inventory."

    script = _get_package_listings_script()
    if not script:
        return False, "Package market is not available."

    container = _get_listings_container()
    if not container:
        return False, "Package market is not available."

    listings = list(script.db.listings or [])
    for ent in listings:
        if ent.get("package_id") == pid:
            return False, "That package is already listed."

    package.move_to(container)
    listings.append({"package_id": pid, "seller_id": seller.id, "price": price})
    script.db.listings = listings
    return True, f"{package.key} listed for {price:,} cr."


def get_package_listings():
    """
    Return list of active package listings.
    Each entry: {package_id, key, estimated_value, price, seller_key}
    """
    script = _get_package_listings_script()
    if not script:
        return []

    result = []
    listings = script.db.listings or []
    container = _get_listings_container()
    if not container:
        return []

    valid = []
    for ent in listings:
        pid = ent.get("package_id")
        seller_id = ent.get("seller_id")
        price = ent.get("price", 0)
        package = None
        for obj in container.contents:
            if obj.id == pid:
                package = obj
                break
        if not package or not package.tags.has("mining_package", category="mining"):
            continue
        valid.append(ent)
        seller_key = "?"
        if seller_id:
            from evennia import search_object
            found = search_object("#" + str(seller_id))
            if found and hasattr(found[0], "key"):
                seller_key = found[0].key
        result.append({
            "packageId": pid,
            "key": package.key,
            "estimatedValue": int(getattr(package.db, "estimated_value", 0) or 0),
            "price": int(price),
            "sellerKey": seller_key,
        })
    script.db.listings = valid
    return result


def buy_listed_package(buyer, package_id):
    """
    Buy a listed mining package. Transfers credits and moves package to buyer.
    Returns (success: bool, message: str).
    """
    from typeclasses.economy import get_economy

    try:
        pid = int(package_id)
    except (TypeError, ValueError):
        return False, "Invalid package id."

    script = _get_package_listings_script()
    if not script:
        return False, "Package market is not available."

    container = _get_listings_container()
    if not container:
        return False, "Package market is not available."

    listings = script.db.listings or []
    entry = None
    package = None
    for obj in container.contents:
        if obj.id == pid and obj.tags.has("mining_package", category="mining"):
            package = obj
            break
    if not package:
        return False, "That package is not for sale or has been sold."

    for ent in listings:
        if ent.get("package_id") == pid:
            entry = ent
            break
    if not entry:
        return False, "Listing not found."

    price = int(entry.get("price", 0))
    seller_id = entry.get("seller_id")
    if not seller_id:
        return False, "Invalid listing."

    from evennia import search_object
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
    econ.transfer(buyer_acct, seller_acct, price, memo="package sale")
    buyer.db.credits = econ.get_character_balance(buyer)
    seller.db.credits = econ.get_character_balance(seller)
    package.move_to(buyer)
    script.db.listings = [e for e in listings if e.get("package_id") != pid]
    return True, f"You bought {package.key} for {price:,} cr."
