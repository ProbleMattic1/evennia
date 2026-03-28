"""
Four Marcus Killstar mining pads: full RESOURCE_CATALOG mix, hazard_level 0,
Mining Pro–tier deploy, rigs tuned to max output multipliers.

Idempotent: each site tagged marcus_killstar_supply (category world).

Cold start: run after bootstrap_mining, bootstrap_haulers, bootstrap_mining_packages
so the processing plant exists and mining_pro components are defined.
"""

import copy

from evennia import create_object, search_object

from typeclasses.characters import CHARACTER_TYPECLASS_PATH, MARCUS_CHARACTER_KEY
from typeclasses.mining import RESOURCE_CATALOG
from typeclasses.packages import _deploy_components_at_site
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.bootstrap_mining_packages import MINING_PACKAGES
from world.npc_miner_registry import register_npc_miner_character_id

LOG_PREFIX = "[marcus-mines]"
DEPLOY_TAG = "marcus_killstar_supply"
CELL_EXIT_PREFIX = "pad "

STAGING_ROOM_KEY = "Marcus Killstar Mining Annex"
STAGING_ROOM_DESC = (
    "Private extraction deck: four leased pads, ore hoppers, and plant dispatch "
    "for the Killstar commodity stack."
)
HUB_TO_STAGING_EXIT_KEY = "killstar mines"
HUB_TO_STAGING_ALIASES = ["marcus mines", "killstar annex", "killstar pads"]
STAGING_TO_HUB_EXIT_KEY = "promenade"
STAGING_TO_HUB_ALIASES = ["back", "exit", "out", "plex", "hub"]

# Match industrial NPC Deep-tier throughput (richness × base_output_tons × rig modifiers).
MARCUS_DEPOSIT_BASE = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}


def _composition_all_resources():
    keys = list(RESOURCE_CATALOG.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def _marcus_deposit():
    d = dict(MARCUS_DEPOSIT_BASE)
    d["composition"] = _composition_all_resources()
    return d


def _components_for_profile(deploy_profile: str):
    for spec in MINING_PACKAGES:
        if spec.get("deploy_profile") == deploy_profile and spec.get(
            "includes_random_claim", True
        ):
            tier = spec.get("key", deploy_profile)
            return copy.deepcopy(spec["components"]), tier
    raise ValueError(f"No MINING_PACKAGES entry for deploy_profile={deploy_profile!r}")


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
    key = f"Marcus Killstar Pad {cell_id}"
    desc = (
        f"Killstar pad {cell_id}: dedicated extraction and haul routing to the "
        "processing plant."
    )
    cell = _get_or_create_room(key, desc)
    ex_key = f"{CELL_EXIT_PREFIX}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"pad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        STAGING_TO_HUB_EXIT_KEY,
        ["annex", "staging", "back"],
        cell,
        staging,
    )
    return cell


def _ensure_site_in_room(room, site_key: str, deposit: dict):
    for obj in room.contents:
        if getattr(obj.db, "is_mining_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        "typeclasses.mining.MiningSite",
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = "Killstar lease; catalog-wide feedstock mix."
    site.db.deposit = dict(deposit)
    site.db.hazard_level = 0.0
    return site


def _tune_rig_max_output(rig):
    rig.db.mode = "overdrive"
    rig.db.power_level = "high"
    rig.db.target_family = "mixed"
    rig.db.purity_cutoff = "low"
    rig.db.maintenance_level = "premium"


def _retune_rigs_on_site(site):
    for r in site.db.rigs or []:
        if r:
            _tune_rig_max_output(r)


def _pad_ids():
    return [f"K-{i}" for i in range(1, 5)]


def bootstrap_marcus_mines():
    matches = search_object(MARCUS_CHARACTER_KEY)
    if not matches:
        print(f"{LOG_PREFIX} Character {MARCUS_CHARACTER_KEY!r} not found; skip.")
        return
    char = matches[0]
    if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
        print(f"{LOG_PREFIX} {MARCUS_CHARACTER_KEY!r} is not a Character; skip.")
        return

    # Same registry industrial NPCs use for automatic plant settlement (optional).
    register_npc_miner_character_id(char.id)

    deposit = _marcus_deposit()
    if not deposit.get("composition"):
        print(f"{LOG_PREFIX} RESOURCE_CATALOG empty; skip.")
        return

    try:
        components, tier = _components_for_profile("mining_pro")
    except ValueError as e:
        print(f"{LOG_PREFIX} {e}")
        return

    staging = _ensure_staging_and_hub_link()

    for grid_cell in _pad_ids():
        cell_room = _ensure_cell_room(staging, grid_cell)
        site_key = f"Marcus Killstar Pad {grid_cell} Deposit"
        site = _ensure_site_in_room(cell_room, site_key, deposit)
        site.db.hazard_level = 0.0

        if site.tags.has(DEPLOY_TAG, category="world"):
            _retune_rigs_on_site(site)
            print(f"{LOG_PREFIX} Already deployed: {site.key!r} in {cell_room.key!r}.")
            continue

        if site.db.is_claimed and site.db.owner and site.db.owner != char:
            print(f"{LOG_PREFIX} Site {site.key!r} claimed by another owner; skip.")
            continue

        ok, msg = _deploy_components_at_site(char, site, cell_room, components, tier)
        if ok:
            site.tags.add(DEPLOY_TAG, category="world")
            _retune_rigs_on_site(site)
            print(f"{LOG_PREFIX} Deployed @ {cell_room.key!r}: {msg.splitlines()[0]}")
        else:
            print(f"{LOG_PREFIX} Deploy failed {grid_cell!r}: {msg}")

    print(f"{LOG_PREFIX} Bootstrap complete.")
