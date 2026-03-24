"""
Mining package delivery and undeploy system.

deliver_mining_package(buyer, package_template, site_query)
    Resolves unclaimed site, spawns components, claims site, deploys, starts production.
    Used when deploying from a template (legacy / internal).

deploy_package_from_inventory(buyer, package_obj, claim_obj)
    Consumes claim and package; deploys at the claim's site.
    claim_obj must be a MiningClaim in buyer's inventory.

undeploy_mine_to_package(buyer, site)
    Full teardown of an owned mine; creates a fresh package and adds to inventory.
"""

from evennia import create_object, search_object


def _get_package_spec_by_tier(package_tier):
    """Look up MINING_PACKAGES spec by tier key. Returns None if not found."""
    from world.bootstrap_mining_packages import MINING_PACKAGES
    for spec in MINING_PACKAGES:
        if spec["key"] == package_tier:
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

    site.schedule_next_cycle()

    cycle_h = int(hauler.db.hauler_base_cycle_hours or 4)
    return True, (
        f"Mining operation deployed at {site.key}.\n"
        f"  Site: {site_room.key}\n"
        f"  Rig: {rig.key}  Storage: {storage.key}  Hauler: {hauler.key}\n"
        f"  Mining cycle: 12h  Hauler cycle: {cycle_h}h\n"
        f"  Ore will flow to {refinery_room.key} automatically.\n"
        f"  Use mines and haulerstatus to monitor progress."
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

    ok, msg = _deploy_components_at_site(buyer, site, site_room, components, package_tier)
    if ok:
        package_obj.delete()
        claim_obj.delete()
    return ok, msg


def undeploy_mine_to_package(buyer, site):
    """
    Full teardown of owned mine: remove rig, storage, hauler; free site;
    create a fresh package and add to buyer's inventory.
    Returns (success: bool, message: str, package_obj or None).
    """
    if not getattr(site.db, "is_claimed", False) or site.db.owner != buyer:
        return False, "You do not own this mining site.", None

    package_tier = getattr(site.db, "package_tier", None)
    if not package_tier:
        return False, "This site has no recorded package tier; cannot undeploy.", None

    spec = _get_package_spec_by_tier(package_tier)
    if not spec:
        return False, f"Unknown package tier '{package_tier}'; cannot create package.", None

    rig = site.db.active_rig
    storage = site.db.linked_storage
    owned_vehicles = buyer.db.owned_vehicles or []
    hauler = None
    for v in list(owned_vehicles):
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
    site.db.is_claimed = False
    site.db.owner = None
    site.db.package_tier = None

    owned_sites = buyer.db.owned_sites or []
    if site in owned_sites:
        owned_sites = [s for s in owned_sites if s != site]
        buyer.db.owned_sites = owned_sites

    if rig:
        rig.uninstall()
        rig.delete()
    if storage:
        storage.db.site = None
        storage.db.owner = None
        storage.delete()
    if hauler:
        hauler.db.hauler_owner = None
        hauler.db.hauler_mine_room = None
        hauler.db.hauler_refinery_room = None
        hauler.db.hauler_state = "idle"
        hauler.tags.remove("autonomous_hauler", category="mining")
        owned_vehicles = [v for v in (buyer.db.owned_vehicles or []) if v != hauler]
        buyer.db.owned_vehicles = owned_vehicles
        hauler.delete()

    package = create_object("typeclasses.objects.Object", key=spec["key"], location=buyer, home=buyer)
    package.db.desc = spec.get("desc", "A mining operation package.")
    package.db.is_template = False
    package.db.package_tier = package_tier
    package.tags.add("mining_package", category="mining")
    package.locks.add("get:true();drop:true();give:true()")

    site_name = site.location.key if site.location else site.key
    return True, (
        f"Mine at {site_name} undeployed.\n"
        f"  {package.key} returned to your inventory. "
        f"Deploy again with deploymine {package.key} <claim>."
    ), package
