"""
Four Marcus Killstar fauna pads: full FAUNA_RESOURCE_CATALOG mix, no hazards,
heavy harvester/storage/hauler matching Mining Pro tier scale.

Idempotent: each site tagged marcus_killstar_fauna_supply (category world).

Cold start: after bootstrap_fauna_engine, bootstrap_mining (so hub + plant exist).
Hauler destination prefers Aurnom Fauna Processing Plant, else flora, else ore plant.
"""

import copy

from evennia import create_object, search_object

from typeclasses.characters import CHARACTER_TYPECLASS_PATH, MARCUS_CHARACTER_KEY
from typeclasses.fauna import FAUNA_RESOURCE_CATALOG, FaunaSite
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.npc_bio_colony_deploy import deploy_fauna_colony_site, resolve_plant_room

LOG_PREFIX = "[marcus-fauna]"
DEPLOY_TAG = "marcus_killstar_fauna_supply"
CELL_EXIT_PREFIX = "fauna pad "

STAGING_ROOM_KEY = "Marcus Killstar Fauna Annex"
STAGING_ROOM_DESC = (
    "Private fauna harvest deck: four leased ranges, bulk containment, and dispatch "
    "uplinks to the processing plant."
)
HUB_TO_STAGING_EXIT_KEY = "killstar fauna"
HUB_TO_STAGING_ALIASES = [
    "marcus fauna",
    "killstar fauna annex",
    "killstar fauna pads",
]
STAGING_TO_HUB_EXIT_KEY = "promenade"
STAGING_TO_HUB_ALIASES = ["back", "exit", "out", "plex", "hub"]

MARCUS_FAUNA_DEPOSIT_BASE = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}

MARCUS_FAUNA_PLANT_KEYS = (
    "Aurnom Fauna Processing Plant",
    "Aurnom Flora Processing Plant",
    "Aurnom Ore Processing Plant",
)

MARCUS_FAUNA_COMPONENTS = [
    {
        "type": "harvester",
        "key": "Killstar Fauna Harvester Mk III",
        "desc": "High-throughput harvest rig for the Killstar fauna stack.",
        "rig_rating": 1.25,
    },
    {
        "type": "storage",
        "key": "Killstar Fauna Storage Gamma",
        "desc": "Pressurised bulk containment for mixed fauna manifests.",
        "capacity_tons": 1500.0,
    },
    {
        "type": "hauler",
        "key": "Killstar Mk III Fauna Hauler",
        "desc": "Autonomous hauler on the fauna route.",
        "cargo_capacity_tons": 250.0,
        "cycle_hours": 2.0,
    },
]


def _composition_all_fauna_resources():
    keys = list(FAUNA_RESOURCE_CATALOG.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def _marcus_fauna_deposit():
    d = dict(MARCUS_FAUNA_DEPOSIT_BASE)
    d["composition"] = _composition_all_fauna_resources()
    return d


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
    key = f"Marcus Killstar Fauna Pad {cell_id}"
    desc = (
        f"Killstar fauna range {cell_id}: dedicated harvest and haul routing to the "
        "processing plant."
    )
    cell = _get_or_create_room(key, desc)
    ex_key = f"{CELL_EXIT_PREFIX}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"faunapad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        STAGING_TO_HUB_EXIT_KEY,
        ["annex", "staging", "back"],
        cell,
        staging,
    )
    return cell


def _ensure_fauna_site_in_room(room, site_key: str, deposit: dict):
    for obj in room.contents:
        if getattr(obj.db, "is_fauna_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        FaunaSite,
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = "Killstar lease; full fauna catalog mix."
    site.db.deposit = dict(deposit)
    return site


def _tune_harvester_max_output(harvester):
    pass


def _retune_harvesters_on_site(site):
    for r in site.db.rigs or []:
        if r:
            _tune_harvester_max_output(r)


def _pad_ids():
    return [f"KFa-{i}" for i in range(1, 5)]


def bootstrap_marcus_fauna():
    matches = search_object(MARCUS_CHARACTER_KEY)
    if not matches:
        print(f"{LOG_PREFIX} Character {MARCUS_CHARACTER_KEY!r} not found; skip.")
        return
    char = matches[0]
    if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
        print(f"{LOG_PREFIX} {MARCUS_CHARACTER_KEY!r} is not a Character; skip.")
        return

    deposit = _marcus_fauna_deposit()
    if not deposit.get("composition"):
        print(f"{LOG_PREFIX} FAUNA_RESOURCE_CATALOG empty; skip.")
        return

    if not resolve_plant_room(MARCUS_FAUNA_PLANT_KEYS):
        print(f"{LOG_PREFIX} No processing plant room; skip.")
        return

    components = copy.deepcopy(MARCUS_FAUNA_COMPONENTS)
    staging = _ensure_staging_and_hub_link()

    for grid_cell in _pad_ids():
        cell_room = _ensure_cell_room(staging, grid_cell)
        site_key = f"Marcus Killstar Fauna Pad {grid_cell} Range"
        site = _ensure_fauna_site_in_room(cell_room, site_key, deposit)

        if site.tags.has(DEPLOY_TAG, category="world"):
            _retune_harvesters_on_site(site)
            site.db.deposit = dict(deposit)
            print(f"{LOG_PREFIX} Already deployed: {site.key!r} in {cell_room.key!r}.")
            continue

        if site.db.is_claimed and site.db.owner and site.db.owner != char:
            print(f"{LOG_PREFIX} Site {site.key!r} claimed by another owner; skip.")
            continue

        ok, msg = deploy_fauna_colony_site(char, site, cell_room, components, MARCUS_FAUNA_PLANT_KEYS)
        if ok:
            site.tags.add(DEPLOY_TAG, category="world")
            _retune_harvesters_on_site(site)
            print(f"{LOG_PREFIX} Deployed @ {cell_room.key!r}: {msg.splitlines()[0]}")
        else:
            print(f"{LOG_PREFIX} Deploy failed {grid_cell!r}: {msg}")

    print(f"{LOG_PREFIX} Bootstrap complete.")
