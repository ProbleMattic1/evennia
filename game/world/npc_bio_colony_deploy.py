"""
Shared NPC colony flora/fauna site deploy (Marcus-scale gear and hauler wiring).

Used by bootstrap_marcus_flora / bootstrap_marcus_fauna and resource colony bootstraps.
"""

from __future__ import annotations

from evennia import create_object, search_object

from typeclasses.flora import FloraHarvester, FloraStorage
from typeclasses.fauna import FaunaHarvester, FaunaStorage
from typeclasses.haulers import set_hauler_next_cycle
from typeclasses.vehicles import Hauler
from world.deploy_component_keys import prepare_deploy_components


def resolve_plant_room(ordered_room_keys: tuple[str, ...] | list[str]):
    """First existing room key wins."""
    for room_key in ordered_room_keys:
        hits = search_object(room_key)
        if hits:
            return hits[0]
    return None


def deploy_flora_colony_site(owner, site, site_room, components: list, plant_room_keys) -> tuple[bool, str]:
    """
    Claim site, spawn FloraHarvester + FloraStorage + flora-tagged Hauler.
    plant_room_keys: ordered list/tuple of refinery room key strings to search.
    """
    from typeclasses.haulers import HAULER_ENGINE_INTERVAL
    from world.time import FLORA_HAULER_PICKUP_OFFSET_SEC
    from world.venue_resolve import processing_plant_room_for_npc_autonomous_supply

    if getattr(owner.db, "is_npc", False):
        refinery_room = processing_plant_room_for_npc_autonomous_supply()
    else:
        refinery_room = resolve_plant_room(plant_room_keys)
    if not refinery_room:
        return False, "No processing plant room found (flora plant key list exhausted)."

    components = prepare_deploy_components(
        components, owner, site, ("harvester", "storage", "hauler")
    )

    harvester = storage = hauler = None
    for comp in components:
        ct = comp.get("type")
        if ct == "harvester":
            harvester = create_object(
                FloraHarvester,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            harvester.db.desc = comp.get("desc", "")
            harvester.db.rig_rating = float(comp.get("rig_rating", 1.0))
            harvester.db.owner = owner
            harvester.locks.add("get:false()")
        elif ct == "storage":
            storage = create_object(
                FloraStorage,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            storage.db.desc = comp.get("desc", "")
            storage.db.capacity_tons = float(comp.get("capacity_tons", 500.0))
            storage.db.owner = owner
        elif ct == "hauler":
            hauler = create_object(
                Hauler,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            hauler.db.desc = comp.get("desc", "Autonomous flora hauler.")
            hauler.db.is_template = False
            hauler.db.owner = owner
            hauler.db.allowed_boarders = [owner]
            hauler.db.state = "docked"
            hauler.db.cargo = {}
            hauler.db.cargo_capacity_tons = float(comp.get("cargo_capacity_tons", 50.0))
            hauler.db.hauler_owner = owner
            hauler.db.hauler_mine_room = None
            hauler.db.hauler_refinery_room = None
            hauler.db.hauler_state = "idle"
            hauler.db.hauler_upgrades = {}
            hauler.db.hauler_base_cycle_hours = float(comp.get("cycle_hours", 4.0))
            hauler.tags.add("autonomous_hauler", category="flora")
            hauler.locks.add("get:false()")

    if not harvester or not storage or not hauler:
        return False, "Flora package is missing harvester, storage, or hauler."

    site.db.is_claimed = True
    site.db.owner = owner
    owned = owner.db.owned_sites or []
    if site not in owned:
        owned.append(site)
    owner.db.owned_sites = owned

    harvester.install(site, owner=owner)
    site.db.linked_storage = storage
    storage.db.site = site
    storage.db.owner = owner

    site.schedule_next_cycle()

    hauler.db.hauler_mine_room = site_room
    hauler.db.hauler_refinery_room = refinery_room
    hdr = getattr(owner.db, "haul_destination_room", None)
    if hdr:
        hauler.db.hauler_destination_room = hdr
    hauler.db.hauler_state = "at_mine"
    set_hauler_next_cycle(hauler)

    vehicles = owner.db.owned_vehicles or []
    if hauler not in vehicles:
        vehicles.append(hauler)
    owner.db.owned_vehicles = vehicles

    return True, (
        f"Flora operation deployed at {site.key}.\n"
        f"  Site: {site_room.key}\n"
        f"  Harvester: {harvester.key}  Storage: {storage.key}  Hauler: {hauler.key}\n"
        f"  Harvest delivery: UTC 1h grid  Hauler pickup: {FLORA_HAULER_PICKUP_OFFSET_SEC // 60}m after each deposit; "
        f"autonomous dispatch every {HAULER_ENGINE_INTERVAL // 60}m.\n"
        f"  Destination: {refinery_room.key}."
    )


def deploy_fauna_colony_site(owner, site, site_room, components: list, plant_room_keys) -> tuple[bool, str]:
    """
    Claim site, spawn FaunaHarvester + FaunaStorage + fauna-tagged Hauler.
    """
    from typeclasses.haulers import HAULER_ENGINE_INTERVAL
    from world.time import FLORA_HAULER_PICKUP_OFFSET_SEC
    from world.venue_resolve import processing_plant_room_for_npc_autonomous_supply

    if getattr(owner.db, "is_npc", False):
        refinery_room = processing_plant_room_for_npc_autonomous_supply()
    else:
        refinery_room = resolve_plant_room(plant_room_keys)
    if not refinery_room:
        return False, "No processing plant room found (fauna plant key list exhausted)."

    components = prepare_deploy_components(
        components, owner, site, ("harvester", "storage", "hauler")
    )

    harvester = storage = hauler = None
    for comp in components:
        ct = comp.get("type")
        if ct == "harvester":
            harvester = create_object(
                FaunaHarvester,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            harvester.db.desc = comp.get("desc", "")
            harvester.db.rig_rating = float(comp.get("rig_rating", 1.0))
            harvester.db.owner = owner
            harvester.locks.add("get:false()")
        elif ct == "storage":
            storage = create_object(
                FaunaStorage,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            storage.db.desc = comp.get("desc", "")
            storage.db.capacity_tons = float(comp.get("capacity_tons", 500.0))
            storage.db.owner = owner
        elif ct == "hauler":
            hauler = create_object(
                Hauler,
                key=comp["key"],
                location=site_room,
                home=site_room,
            )
            hauler.db.desc = comp.get("desc", "Autonomous fauna hauler.")
            hauler.db.is_template = False
            hauler.db.owner = owner
            hauler.db.allowed_boarders = [owner]
            hauler.db.state = "docked"
            hauler.db.cargo = {}
            hauler.db.cargo_capacity_tons = float(comp.get("cargo_capacity_tons", 50.0))
            hauler.db.hauler_owner = owner
            hauler.db.hauler_mine_room = None
            hauler.db.hauler_refinery_room = None
            hauler.db.hauler_state = "idle"
            hauler.db.hauler_upgrades = {}
            hauler.db.hauler_base_cycle_hours = float(comp.get("cycle_hours", 4.0))
            hauler.tags.add("autonomous_hauler", category="fauna")
            hauler.locks.add("get:false()")

    if not harvester or not storage or not hauler:
        return False, "Fauna package is missing harvester, storage, or hauler."

    site.db.is_claimed = True
    site.db.owner = owner
    owned = owner.db.owned_sites or []
    if site not in owned:
        owned.append(site)
    owner.db.owned_sites = owned

    harvester.install(site, owner=owner)
    site.db.linked_storage = storage
    storage.db.site = site
    storage.db.owner = owner

    site.schedule_next_cycle()

    hauler.db.hauler_mine_room = site_room
    hauler.db.hauler_refinery_room = refinery_room
    hdr = getattr(owner.db, "haul_destination_room", None)
    if hdr:
        hauler.db.hauler_destination_room = hdr
    hauler.db.hauler_state = "at_mine"
    set_hauler_next_cycle(hauler)

    vehicles = owner.db.owned_vehicles or []
    if hauler not in vehicles:
        vehicles.append(hauler)
    owner.db.owned_vehicles = vehicles

    return True, (
        f"Fauna operation deployed at {site.key}.\n"
        f"  Site: {site_room.key}\n"
        f"  Harvester: {harvester.key}  Storage: {storage.key}  Hauler: {hauler.key}\n"
        f"  Harvest delivery: UTC 1h grid  Hauler pickup: {FLORA_HAULER_PICKUP_OFFSET_SEC // 60}m after each deposit; "
        f"autonomous dispatch every {HAULER_ENGINE_INTERVAL // 60}m.\n"
        f"  Destination: {refinery_room.key}."
    )
