"""
Four Marcus Killstar flora pads: full FLORA_RESOURCE_CATALOG mix, no hazards,
heavy harvester/storage/hauler matching Mining Pro tier scale.

Idempotent: each site tagged marcus_killstar_flora_supply (category world).

Cold start: after bootstrap_marcus_killstar, bootstrap_flora_engine, bootstrap_mining
(so hub + at least one processing plant room exist). Hauler destination prefers
Aurnom Flora Processing Plant, else Aurnom Ore Processing Plant.
"""

import copy

from evennia import create_object, search_object

from typeclasses.characters import CHARACTER_TYPECLASS_PATH, MARCUS_CHARACTER_KEY
from typeclasses.flora import FLORA_RESOURCE_CATALOG, FloraHarvester, FloraSite, FloraStorage
from typeclasses.haulers import set_hauler_next_cycle
from typeclasses.vehicles import Hauler
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.npc_miner_registry import register_npc_miner_character_id

LOG_PREFIX = "[marcus-flora]"
DEPLOY_TAG = "marcus_killstar_flora_supply"
CELL_EXIT_PREFIX = "flora pad "

STAGING_ROOM_KEY = "Marcus Killstar Flora Annex"
STAGING_ROOM_DESC = (
    "Private harvest deck: four leased stands, bulk bins, and dispatch uplinks "
    "to the processing plant."
)
HUB_TO_STAGING_EXIT_KEY = "killstar flora"
HUB_TO_STAGING_ALIASES = [
    "marcus flora",
    "killstar flora annex",
    "killstar flora pads",
]
STAGING_TO_HUB_EXIT_KEY = "promenade"
STAGING_TO_HUB_ALIASES = ["back", "exit", "out", "plex", "hub"]

MARCUS_FLORA_DEPOSIT_BASE = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}

# Mining Pro–scale gear (tonnage/capacity), flora typeclasses + flora-tagged hauler.
MARCUS_FLORA_COMPONENTS = [
    {
        "type": "harvester",
        "key": "Killstar Flora Harvester Mk III",
        "desc": "High-throughput harvest head for the Killstar botanical stack.",
        "rig_rating": 1.25,
    },
    {
        "type": "storage",
        "key": "Killstar Flora Storage Gamma",
        "desc": "Pressurised bulk bin for mixed harvest manifests.",
        "capacity_tons": 1500.0,
    },
    {
        "type": "hauler",
        "key": "Killstar Mk III Flora Hauler",
        "desc": "Autonomous hauler on the flora route.",
        "cargo_capacity_tons": 250.0,
        "cycle_hours": 2.0,
    },
]


def _composition_all_flora_resources():
    keys = list(FLORA_RESOURCE_CATALOG.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def _marcus_flora_deposit():
    d = dict(MARCUS_FLORA_DEPOSIT_BASE)
    d["composition"] = _composition_all_flora_resources()
    return d


def _resolve_flora_hauler_destination_room():
    for room_key in ("Aurnom Flora Processing Plant", "Aurnom Ore Processing Plant"):
        hits = search_object(room_key)
        if hits:
            return hits[0]
    return None


def _deploy_flora_components_at_site(owner, site, site_room, components):
    """
    Claim site, spawn FloraHarvester + FloraStorage + Hauler (autonomous_hauler category flora only).
    Mirrors packages._deploy_components_at_site routing semantics for Marcus-scale gear.
    """
    from typeclasses.haulers import HAULER_ENGINE_INTERVAL
    from world.time import FLORA_HAULER_PICKUP_OFFSET_SEC

    refinery_room = _resolve_flora_hauler_destination_room()
    if not refinery_room:
        return False, "No processing plant room found (flora or ore)."

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


def _get_or_create_room(key: str, desc: str):
    matches = search_object(key)
    for o in matches:
        if hasattr(o, "contents"):
            if desc and not (getattr(o.db, "desc", None) or "").strip():
                o.db.desc = desc
            return o
    room = create_object("typeclasses.rooms.Room", key=key)
    room.db.desc = desc
    return room


def _ensure_staging_and_hub_link():
    staging = _get_or_create_room(STAGING_ROOM_KEY, STAGING_ROOM_DESC)
    hub = get_hub_room()
    if hub:
        _get_or_create_exit(
            HUB_TO_STAGING_EXIT_KEY,
            HUB_TO_STAGING_ALIASES,
            hub,
            staging,
        )
        _get_or_create_exit(
            STAGING_TO_HUB_EXIT_KEY,
            STAGING_TO_HUB_ALIASES,
            staging,
            hub,
        )
    else:
        print(f"{LOG_PREFIX} WARNING: hub missing — no hub link to staging.")
    return staging


def _ensure_cell_room(staging, cell_id: str):
    key = f"Marcus Killstar Flora Pad {cell_id}"
    desc = (
        f"Killstar flora stand {cell_id}: dedicated harvest and haul routing to the "
        "processing plant."
    )
    cell = _get_or_create_room(key, desc)
    ex_key = f"{CELL_EXIT_PREFIX}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"florapad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        STAGING_TO_HUB_EXIT_KEY,
        ["annex", "staging", "back"],
        cell,
        staging,
    )
    return cell


def _ensure_flora_site_in_room(room, site_key: str, deposit: dict):
    for obj in room.contents:
        if getattr(obj.db, "is_flora_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        FloraSite,
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = "Killstar lease; full flora catalog mix."
    site.db.deposit = dict(deposit)
    return site


def _tune_harvester_max_output(harvester):
    """Flora has no mode/power; max throughput is rig_rating (set in components)."""
    pass


def _retune_harvesters_on_site(site):
    for r in site.db.rigs or []:
        if r:
            _tune_harvester_max_output(r)


def _pad_ids():
    return [f"KF-{i}" for i in range(1, 5)]


def bootstrap_marcus_flora():
    matches = search_object(MARCUS_CHARACTER_KEY)
    if not matches:
        print(f"{LOG_PREFIX} Character {MARCUS_CHARACTER_KEY!r} not found; skip.")
        return
    char = matches[0]
    if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
        print(f"{LOG_PREFIX} {MARCUS_CHARACTER_KEY!r} is not a Character; skip.")
        return

    register_npc_miner_character_id(char.id)

    deposit = _marcus_flora_deposit()
    if not deposit.get("composition"):
        print(f"{LOG_PREFIX} FLORA_RESOURCE_CATALOG empty; skip.")
        return

    if not _resolve_flora_hauler_destination_room():
        print(f"{LOG_PREFIX} No processing plant room; skip.")
        return

    components = copy.deepcopy(MARCUS_FLORA_COMPONENTS)
    staging = _ensure_staging_and_hub_link()

    for grid_cell in _pad_ids():
        cell_room = _ensure_cell_room(staging, grid_cell)
        site_key = f"Marcus Killstar Flora Pad {grid_cell} Stand"
        site = _ensure_flora_site_in_room(cell_room, site_key, deposit)

        if site.tags.has(DEPLOY_TAG, category="world"):
            _retune_harvesters_on_site(site)
            site.db.deposit = dict(deposit)
            print(f"{LOG_PREFIX} Already deployed: {site.key!r} in {cell_room.key!r}.")
            continue

        if site.db.is_claimed and site.db.owner and site.db.owner != char:
            print(f"{LOG_PREFIX} Site {site.key!r} claimed by another owner; skip.")
            continue

        ok, msg = _deploy_flora_components_at_site(char, site, cell_room, components)
        if ok:
            site.tags.add(DEPLOY_TAG, category="world")
            _retune_harvesters_on_site(site)
            print(f"{LOG_PREFIX} Deployed @ {cell_room.key!r}: {msg.splitlines()[0]}")
        else:
            print(f"{LOG_PREFIX} Deploy failed {grid_cell!r}: {msg}")

    print(f"{LOG_PREFIX} Bootstrap complete.")
