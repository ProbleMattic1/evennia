"""
Bootstrap NPC-owned mining ops per venue industrial subdeck.

Idempotent: site tag from venue industrial spec (category world).
"""

import copy
import os

from evennia import create_object, search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import ABILITY_KEYS, CHARACTER_TYPECLASS_PATH
from typeclasses.packages import _deploy_components_at_site
from world.bootstrap_mining import _get_or_create_exit
from world.bootstrap_mining_packages import MINING_PACKAGES
from world.npc_miner_registry import register_npc_miner_character_id
from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids, apply_venue_metadata, get_venue

CELL_EXIT_PREFIX = "pad "


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


def _ensure_npc_character(account, key: str, desc: str, log_prefix: str):
    matches = search_object(key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"{log_prefix} {key!r} exists but is not a Character; skip.")
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
        print(f"{log_prefix} create_character {key!r} failed: {errs}")
        return None
    char.db.is_npc = True
    char.db.rpg_pointbuy_done = True
    char.db.desc = desc
    _apply_flat_bases(char)
    register_npc_miner_character_id(char.id)
    print(f"{log_prefix} Created NPC {key!r} (#{char.id}).")
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


def _ensure_staging_and_hub_link(venue_id: str, log_prefix: str):
    ind = get_venue(venue_id)["industrial"]
    staging = _get_or_create_room(ind["staging_room_key"], ind["staging_room_desc"])
    apply_venue_metadata(staging, venue_id)
    hub = hub_room_for_venue(venue_id)
    if hub:
        _get_or_create_exit(
            ind["hub_exit_key"],
            ind["hub_exit_aliases"],
            hub,
            staging,
        )
        _get_or_create_exit(
            "promenade",
            ["back", "exit", "out", "plex", "hub"],
            staging,
            hub,
        )
    else:
        print(f"{log_prefix} WARNING: hub missing — no hub link to staging.")
    return staging


def _ensure_cell_room(staging, cell_id: str, venue_id: str, ind: dict):
    key = f"{ind['pad_room_prefix']} {cell_id}"
    desc = ind["pad_desc_template"].format(cell=cell_id)
    cell = _get_or_create_room(key, desc)
    apply_venue_metadata(cell, venue_id)
    ex_key = f"{CELL_EXIT_PREFIX}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"pad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        "promenade",
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


def bootstrap_industrial_miners_for_venue(venue_id: str):
    vspec = get_venue(venue_id)
    ind = vspec["industrial"]
    deploy_tag = ind["deploy_tag"]
    log_prefix = f"[industrial:{venue_id}]"

    account = _target_account()
    if not account:
        print(f"{log_prefix} No admin/superuser account; skip.")
        return

    staging = _ensure_staging_and_hub_link(venue_id, log_prefix)

    for unit in ind["units"]:
        npc = _ensure_npc_character(account, unit["npc_key"], unit["npc_desc"], log_prefix)
        if not npc:
            continue

        for grid_cell in _pads_for_unit(unit["unit_id"]):
            cell_room = _ensure_cell_room(staging, grid_cell, venue_id, ind)
            site_key = ind["site_key_template"].format(cell=grid_cell)

            site = _ensure_site_in_room(cell_room, site_key, DEEP_UNCOMMON_DEPOSIT)
            site.db.hazard_level = 0.0
            if site.tags.has(deploy_tag, category="world"):
                print(f"{log_prefix} Already deployed: {site.key!r} in {cell_room.key!r}.")
                continue
            if site.db.is_claimed and site.db.owner and site.db.owner != npc:
                print(f"{log_prefix} Site {site.key!r} claimed by another owner; skip.")
                continue

            components, tier = _components_for_profile(unit["deploy_profile"])

            ok, msg = _deploy_components_at_site(npc, site, cell_room, components, tier)
            if ok:
                site.tags.add(deploy_tag, category="world")
                print(
                    f"{log_prefix} Deployed {unit['npc_key']!r} @ {cell_room.key!r}: "
                    f"{msg.splitlines()[0]}"
                )
            else:
                print(f"{log_prefix} Deploy fail {unit['npc_key']!r} {grid_cell!r}: {msg}")

    print(f"{log_prefix} Bootstrap complete.")


def bootstrap_npc_nanomega_industrial_miners():
    """Cold-start entry: all venues with industrial specs."""
    for venue_id in all_venue_ids():
        bootstrap_industrial_miners_for_venue(venue_id)
