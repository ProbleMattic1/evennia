"""
Bootstrap NPC-owned mining ops — NanoMegaPlex industrial subdeck.

Mirrors Ashfall industrial bootstrap: hub -> staging -> one room per pad.
Five units × four pads; deposits Deep volume + Uncommon rarity tier.

Idempotent: site tag npc_nanomega_industrial_supply (category world).
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

STAGING_ROOM_KEY = "NanoMegaPlex Industrial Subdeck"
STAGING_ROOM_DESC = (
    "Below-deck contractor grid for multiplex build-out: leased pads, "
    "ore hoppers, and dispatch uplinks to the central processing plant."
)

HUB_TO_STAGING_EXIT_KEY = "nanomega industrial"
HUB_TO_STAGING_ALIASES = [
    "plex industrial",
    "nanomega mines",
    "contractor subdeck",
    "industrial subdeck",
]

STAGING_TO_HUB_EXIT_KEY = "promenade"
STAGING_TO_HUB_ALIASES = ["back", "exit", "out", "plex", "hub"]

CELL_EXIT_PREFIX = "pad "

# Deep: richness * base_output_tons >= 20 (_volume_tier).
# Uncommon: weighted rarity avg in [0.6, 1.5) — here avg = 1.0 (_resource_rarity_tier).
DEEP_UNCOMMON_DEPOSIT = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "composition": {
        "cobalt_ore": 1.0 / 3,
        "tungsten_ore": 1.0 / 3,
        "rare_earth_concentrate": 1.0 / 3,
    },
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}

DEPLOY_TAG = "npc_nanomega_industrial_supply"
LOG_PREFIX = "[npc-nanomega-industrial]"


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
            print(f"{LOG_PREFIX} {key!r} exists but is not a Character; skip.")
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
        print(f"{LOG_PREFIX} create_character {key!r} failed: {errs}")
        return None
    char.db.is_npc = True
    char.db.rpg_pointbuy_done = True
    char.db.desc = desc
    _apply_flat_bases(char)
    register_npc_miner_character_id(char.id)
    print(f"{LOG_PREFIX} Created NPC {key!r} (#{char.id}).")
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
        print(f"{LOG_PREFIX} WARNING: hub missing — no hub link to staging.")
    return staging


def _ensure_cell_room(staging, cell_id: str):
    key = f"NanoMegaPlex Industrial Pad {cell_id}"
    desc = (
        f"NanoMegaPlex lease pad {cell_id}: contracted extraction feeding "
        "multiplex construction and fab lines."
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
        ["grid", "subdeck", "staging", "back"],
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
    site.db.desc = (
        "Industrial lease; Deep/Uncommon tier feedstock for the processing plant."
    )
    site.db.deposit = dict(deposit)
    site.db.hazard_level = 0.0
    return site


def _pads_for_unit(unit_id: str):
    return [f"{unit_id}-{i}" for i in range(1, 5)]


NPC_NANOMEGA_INDUSTRIAL_UNITS = [
    {
        "unit_id": "N1",
        "npc_key": "NanoMegaPlex Mining Unit Foxtrot",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N2",
        "npc_key": "NanoMegaPlex Mining Unit Golf",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N3",
        "npc_key": "NanoMegaPlex Mining Unit Hotel",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N4",
        "npc_key": "NanoMegaPlex Mining Unit India",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
    {
        "unit_id": "N5",
        "npc_key": "NanoMegaPlex Mining Unit Juliet",
        "npc_desc": "Multiplex contractor; ore routed under standard plant tariffs.",
        "deploy_profile": "mining_starter",
    },
]


def bootstrap_npc_nanomega_industrial_miners():
    account = _target_account()
    if not account:
        print(f"{LOG_PREFIX} No admin/superuser account; skip.")
        return

    staging = _ensure_staging_and_hub_link()

    for unit in NPC_NANOMEGA_INDUSTRIAL_UNITS:
        npc = _ensure_npc_character(account, unit["npc_key"], unit["npc_desc"])
        if not npc:
            continue

        for grid_cell in _pads_for_unit(unit["unit_id"]):
            cell_room = _ensure_cell_room(staging, grid_cell)
            site_key = f"NanoMegaPlex Pad {grid_cell} Deposit"

            site = _ensure_site_in_room(cell_room, site_key, DEEP_UNCOMMON_DEPOSIT)
            site.db.hazard_level = 0.0
            if site.tags.has(DEPLOY_TAG, category="world"):
                print(
                    f"{LOG_PREFIX} Already deployed: {site.key!r} in {cell_room.key!r}."
                )
                continue
            if site.db.is_claimed and site.db.owner and site.db.owner != npc:
                print(f"{LOG_PREFIX} Site {site.key!r} claimed by another owner; skip.")
                continue

            components, tier = _components_for_profile(unit["deploy_profile"])

            ok, msg = _deploy_components_at_site(npc, site, cell_room, components, tier)
            if ok:
                site.tags.add(DEPLOY_TAG, category="world")
                print(
                    f"{LOG_PREFIX} Deployed {unit['npc_key']!r} @ {cell_room.key!r}: "
                    f"{msg.splitlines()[0]}"
                )
            else:
                print(
                    f"{LOG_PREFIX} Deploy failed {unit['npc_key']!r} {grid_cell!r}: {msg}"
                )

    print(f"{LOG_PREFIX} Bootstrap complete.")
