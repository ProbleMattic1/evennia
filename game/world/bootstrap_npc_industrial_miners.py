"""
Bootstrap NPC-owned mining ops — Ashfall industrial grid.

Topology: Hub -> Ashfall Industrial Grid (staging) -> one room per pad.
Each NPC unit owns 4 pads (4 sites, 4 rigs, 4 storages, 4 haulers).
Deposits tuned for Deep volume + Rare resource tier (mining.py helpers).

Idempotent: site tag npc_industrial_supply (category world).
"""

import copy
import os

from evennia import create_object, search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import ABILITY_KEYS, CHARACTER_TYPECLASS_PATH
from typeclasses.packages import _deploy_components_at_site
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.bootstrap_mining_packages import MINING_PACKAGES
from world.npc_miner_registry import register_npc_miner_character_id

STAGING_ROOM_KEY = "Ashfall Industrial Grid"
STAGING_ROOM_DESC = (
    "A service deck for contracted extraction pads: pressure doors, "
    "pad telemetry, and hauler dispatch to the coreward plant."
)

HUB_TO_STAGING_EXIT_KEY = "ashfall industrial"
HUB_TO_STAGING_ALIASES = ["ashfall grid", "industrial grid", "contract pads", "pads"]

STAGING_TO_HUB_EXIT_KEY = "promenade"
STAGING_TO_HUB_ALIASES = ["back", "exit", "out", "plex", "hub"]

CELL_EXIT_PREFIX = "pad "

# Deep: richness * base_output_tons >= 20 (_volume_tier).
# Rare: weighted RESOURCE_CATALOG rarity avg >= 1.5 (_resource_rarity_tier).
DEEP_RARE_DEPOSIT = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "composition": {
        "platinum_group_ore": 0.5,
        "diamond_kimberlite": 0.5,
    },
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}


def _components_for_profile(deploy_profile: str) -> tuple[list, str]:
    for spec in MINING_PACKAGES:
        if spec.get("deploy_profile") == deploy_profile and spec.get("includes_random_claim", True):
            tier = spec.get("key", deploy_profile)
            return copy.deepcopy(spec["components"]), tier
    raise ValueError(f"No MINING_PACKAGES entry for deploy_profile={deploy_profile!r}")


def _target_account():
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    return AccountDB.objects.filter(is_superuser=True).order_by("id").first()


def _apply_flat_bases(char, base: int = 14):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = base
            trait.mod = 0
            trait.mult = 1.0


def _ensure_npc_character(account, key: str, desc: str):
    matches = search_object(key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"[npc-industrial] {key!r} exists but is not a Character; skip.")
            return None
        if char not in account.characters:
            account.characters.add(char)
        char.db.is_npc = True
        char.db.desc = desc
        _apply_flat_bases(char)
        register_npc_miner_character_id(char.id)
        return char

    char, errs = account.create_character(key=key, typeclass=CHARACTER_TYPECLASS_PATH)
    if errs:
        print(f"[npc-industrial] create_character {key!r} failed: {errs}")
        return None
    char.db.is_npc = True
    char.db.rpg_pointbuy_done = True
    char.db.desc = desc
    _apply_flat_bases(char)
    register_npc_miner_character_id(char.id)
    print(f"[npc-industrial] Created NPC {key!r} (#{char.id}).")
    return char


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
        print("[npc-industrial] WARNING: hub missing — no hub link to staging.")
    return staging


def _ensure_cell_room(staging, cell_id: str):
    key = f"Ashfall Industrial Pad {cell_id}"
    desc = (
        f"Leased pad {cell_id}: drill mast, ore hopper, and a dedicated "
        "haul lane to the processing plant."
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
        ["grid", "staging", "back"],
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
    site.db.desc = "Industrial lease; Deep/Rare tier feedstock for the processing plant."
    site.db.deposit = dict(deposit)
    site.db.hazard_level = 0.0
    return site


def _pads_for_unit(unit_id: str):
    """Four pad cell ids per NPC unit (expand by changing range or list)."""
    return [f"{unit_id}-{i}" for i in range(1, 5)]


# Each entry: one NPC, four pads. Add units by extending this list.
NPC_INDUSTRIAL_UNITS = [
    {
        "unit_id": "A1",
        "npc_key": "Industrial Mining Unit Alpha",
        "npc_desc": "Automated lease operator; ore is contracted to the plant.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "A2",
        "npc_key": "Industrial Mining Unit Bravo",
        "npc_desc": "Automated lease operator; ore is contracted to the plant.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "A3",
        "npc_key": "Industrial Mining Unit Charlie",
        "npc_desc": "Automated lease operator; ore is contracted to the plant.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "A4",
        "npc_key": "Industrial Mining Unit Delta",
        "npc_desc": "Automated lease operator; ore is contracted to the plant.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "A5",
        "npc_key": "Industrial Mining Unit Echo",
        "npc_desc": "Automated lease operator; ore is contracted to the plant.",
        "deploy_profile": "mining_starter",
    },
]


def bootstrap_npc_industrial_miners():
    account = _target_account()
    if not account:
        print("[npc-industrial] No admin/superuser account; skip.")
        return

    staging = _ensure_staging_and_hub_link()

    for unit in NPC_INDUSTRIAL_UNITS:
        npc = _ensure_npc_character(account, unit["npc_key"], unit["npc_desc"])
        if not npc:
            continue

        for grid_cell in _pads_for_unit(unit["unit_id"]):
            cell_room = _ensure_cell_room(staging, grid_cell)
            site_key = f"Ashfall Pad {grid_cell} Deposit"

            site = _ensure_site_in_room(cell_room, site_key, DEEP_RARE_DEPOSIT)
            site.db.hazard_level = 0.0
            if site.tags.has("npc_industrial_supply", category="world"):
                print(f"[npc-industrial] Already deployed: {site.key!r} in {cell_room.key!r}.")
                continue
            if site.db.is_claimed and site.db.owner and site.db.owner != npc:
                print(f"[npc-industrial] Site {site.key!r} claimed by another owner; skip.")
                continue

            components, tier = _components_for_profile(unit["deploy_profile"])

            ok, msg = _deploy_components_at_site(npc, site, cell_room, components, tier)
            if ok:
                site.tags.add("npc_industrial_supply", category="world")
                print(
                    f"[npc-industrial] Deployed {unit['npc_key']!r} @ {cell_room.key!r}: "
                    f"{msg.splitlines()[0]}"
                )
            else:
                print(f"[npc-industrial] Deploy failed {unit['npc_key']!r} {grid_cell!r}: {msg}")

    print("[npc-industrial] Bootstrap complete.")
