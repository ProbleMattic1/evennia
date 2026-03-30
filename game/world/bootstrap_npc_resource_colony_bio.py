"""
Idempotent flora/fauna pads for Resource Colonies (venue industrial + core grid).

Four FloraSite and four FaunaSite per colony. Owners: first four NPC mine employees in
each unit list; the fifth employee remains mining-only.

Cold start: after bootstrap_flora_engine, bootstrap_fauna_engine, bootstrap_haulers,
bootstrap_npc_industrial_miners, bootstrap_npc_nanomega_industrial_miners.
"""

from __future__ import annotations

import copy

from evennia import create_object, search_object

from typeclasses.fauna import FAUNA_RESOURCE_CATALOG, FaunaSite
from typeclasses.flora import FLORA_RESOURCE_CATALOG, FloraSite
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.bootstrap_npc_industrial_miners import _ensure_npc_character, _target_account
from world.industrial_colony_constants import NPC_INDUSTRIAL_UNITS
from world.npc_bio_colony_deploy import (
    deploy_fauna_colony_site,
    deploy_flora_colony_site,
    resolve_plant_room,
)
from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids, apply_venue_metadata, get_venue

CORE_RESOURCE_BIO_VENUE_ID = "nanomega_core"

CORE_RESOURCE_BIO = {
    "colony_label": "Industrial Resource Colony",
    "flora_staging_room_key": "Industrial Resource Colony Flora Annex",
    "flora_staging_room_desc": (
        "Flora harvest annex for the Industrial Resource Colony: leased stands, "
        "bulk bins, and dispatch to core processing."
    ),
    "flora_hub_exit_key": "industrial colony flora",
    "flora_hub_exit_aliases": [
        "resource colony flora",
        "industrial flora annex",
        "colony flora",
    ],
    "fauna_staging_room_key": "Industrial Resource Colony Fauna Annex",
    "fauna_staging_room_desc": (
        "Fauna harvest annex for the Industrial Resource Colony: leased ranges, "
        "containment, and dispatch to core processing."
    ),
    "fauna_hub_exit_key": "industrial colony fauna",
    "fauna_hub_exit_aliases": [
        "resource colony fauna",
        "industrial fauna annex",
        "colony fauna",
    ],
    "flora_pad_prefix": "Industrial Resource Colony Flora Pad",
    "fauna_pad_prefix": "Industrial Resource Colony Fauna Pad",
    "flora_cell_desc_template": (
        "Industrial Resource Colony flora stand {cell}: harvest and haul routing "
        "to the processing plant."
    ),
    "fauna_cell_desc_template": (
        "Industrial Resource Colony fauna range {cell}: harvest and haul routing "
        "to the processing plant."
    ),
    "flora_site_suffix": "Stand",
    "fauna_site_suffix": "Range",
    "flora_deploy_tag": "npc_industrial_resource_colony_flora",
    "fauna_deploy_tag": "npc_industrial_resource_colony_fauna",
    "flora_plant_keys": (
        "Aurnom Flora Processing Plant",
        "Aurnom Ore Processing Plant",
    ),
    "fauna_plant_keys": (
        "Aurnom Fauna Processing Plant",
        "Aurnom Flora Processing Plant",
        "Aurnom Ore Processing Plant",
    ),
}


def _composition_even(catalog: dict) -> dict:
    keys = list(catalog.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def _deposit_flora():
    d = {
        "richness": 1.0,
        "base_output_tons": 20.0,
        "depletion_rate": 0.002,
        "richness_floor": 0.12,
        "composition": _composition_even(FLORA_RESOURCE_CATALOG),
    }
    return d


def _deposit_fauna():
    d = {
        "richness": 1.0,
        "base_output_tons": 20.0,
        "depletion_rate": 0.002,
        "richness_floor": 0.12,
        "composition": _composition_even(FAUNA_RESOURCE_CATALOG),
    }
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


def _flora_components(colony_label: str, cell: str) -> list:
    return [
        {
            "type": "harvester",
            "key": f"{colony_label} Flora Harvester {cell}",
            "desc": f"High-throughput harvest head for {colony_label}.",
            "rig_rating": 1.25,
        },
        {
            "type": "storage",
            "key": f"{colony_label} Flora Storage {cell}",
            "desc": f"Pressurised bulk bin for {colony_label} mixed harvest manifests.",
            "capacity_tons": 1500.0,
        },
        {
            "type": "hauler",
            "key": f"{colony_label} Flora Hauler {cell}",
            "desc": f"Autonomous hauler on the {colony_label} flora route.",
            "cargo_capacity_tons": 250.0,
            "cycle_hours": 2.0,
        },
    ]


def _fauna_components(colony_label: str, cell: str) -> list:
    return [
        {
            "type": "harvester",
            "key": f"{colony_label} Fauna Harvester {cell}",
            "desc": f"High-throughput harvest rig for {colony_label}.",
            "rig_rating": 1.25,
        },
        {
            "type": "storage",
            "key": f"{colony_label} Fauna Storage {cell}",
            "desc": f"Pressurised bulk containment for {colony_label} mixed fauna manifests.",
            "capacity_tons": 1500.0,
        },
        {
            "type": "hauler",
            "key": f"{colony_label} Fauna Hauler {cell}",
            "desc": f"Autonomous hauler on the {colony_label} fauna route.",
            "cargo_capacity_tons": 250.0,
            "cycle_hours": 2.0,
        },
    ]


def _ensure_bio_cell_room(
    staging,
    hub,
    venue_id: str,
    cell_id: str,
    pad_prefix: str,
    desc: str,
    exit_prefix: str,
    back_aliases: list[str],
):
    key = f"{pad_prefix} {cell_id}"
    cell = _get_or_create_room(key, desc)
    apply_venue_metadata(cell, venue_id)
    ex_key = f"{exit_prefix}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"pad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        "promenade",
        back_aliases,
        cell,
        staging,
    )
    return cell


def _ensure_flora_site(room, site_key: str, deposit: dict, colony_label: str):
    for obj in room.contents:
        if getattr(obj.db, "is_flora_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        FloraSite,
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = f"{colony_label} lease; full flora catalog mix."
    site.db.deposit = dict(deposit)
    return site


def _ensure_fauna_site(room, site_key: str, deposit: dict, colony_label: str):
    for obj in room.contents:
        if getattr(obj.db, "is_fauna_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        FaunaSite,
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = f"{colony_label} lease; full fauna catalog mix."
    site.db.deposit = dict(deposit)
    return site


def _link_hub_staging(hub, staging, exit_key: str, exit_aliases: list[str], venue_id: str):
    apply_venue_metadata(staging, venue_id)
    if hub:
        _get_or_create_exit(exit_key, exit_aliases, hub, staging)
        _get_or_create_exit(
            "promenade",
            ["back", "exit", "out", "plex", "hub"],
            staging,
            hub,
        )
    else:
        print(f"[resource-colony-bio] WARNING: hub missing for {venue_id!r} — no staging link.")


def _bootstrap_flora_track(venue_id: str, bio: dict, owners: list, log_prefix: str):
    hub = hub_room_for_venue(venue_id) or get_hub_room()
    staging = _get_or_create_room(
        bio["flora_staging_room_key"],
        bio["flora_staging_room_desc"],
    )
    _link_hub_staging(
        hub,
        staging,
        bio["flora_hub_exit_key"],
        list(bio["flora_hub_exit_aliases"]),
        venue_id,
    )

    plant_keys = bio["flora_plant_keys"]
    if not resolve_plant_room(plant_keys):
        print(f"{log_prefix} No flora processing destination; skip flora.")
        return

    deposit = _deposit_flora()
    if not deposit.get("composition"):
        print(f"{log_prefix} FLORA_RESOURCE_CATALOG empty; skip flora.")
        return

    tag = bio["flora_deploy_tag"]
    colony_label = bio["colony_label"]
    back_aliases = ["grid", "subdeck", "staging", "back"]

    for i in range(1, 5):
        cell = f"F-{i}"
        owner = owners[i - 1]
        desc = bio["flora_cell_desc_template"].format(cell=cell)
        cell_room = _ensure_bio_cell_room(
            staging,
            hub,
            venue_id,
            cell,
            bio["flora_pad_prefix"],
            desc,
            "flora pad ",
            back_aliases,
        )
        site_key = f"{bio['flora_pad_prefix']} {cell} {bio['flora_site_suffix']}"
        site = _ensure_flora_site(cell_room, site_key, deposit, colony_label)

        if site.tags.has(tag, category="world"):
            site.db.deposit = dict(deposit)
            print(f"{log_prefix} Flora already deployed: {site.key!r} in {cell_room.key!r}.")
            continue
        if site.db.is_claimed and site.db.owner and site.db.owner != owner:
            print(f"{log_prefix} Flora site {site.key!r} claimed by another owner; skip.")
            continue

        components = copy.deepcopy(_flora_components(colony_label, cell))
        ok, msg = deploy_flora_colony_site(owner, site, cell_room, components, plant_keys)
        if ok:
            site.tags.add(tag, category="world")
            print(f"{log_prefix} Flora deployed @ {cell_room.key!r}: {msg.splitlines()[0]}")
        else:
            print(f"{log_prefix} Flora deploy fail {cell!r}: {msg}")


def _bootstrap_fauna_track(venue_id: str, bio: dict, owners: list, log_prefix: str):
    hub = hub_room_for_venue(venue_id) or get_hub_room()
    staging = _get_or_create_room(
        bio["fauna_staging_room_key"],
        bio["fauna_staging_room_desc"],
    )
    _link_hub_staging(
        hub,
        staging,
        bio["fauna_hub_exit_key"],
        list(bio["fauna_hub_exit_aliases"]),
        venue_id,
    )

    plant_keys = bio["fauna_plant_keys"]
    if not resolve_plant_room(plant_keys):
        print(f"{log_prefix} No fauna processing destination; skip fauna.")
        return

    deposit = _deposit_fauna()
    if not deposit.get("composition"):
        print(f"{log_prefix} FAUNA_RESOURCE_CATALOG empty; skip fauna.")
        return

    tag = bio["fauna_deploy_tag"]
    colony_label = bio["colony_label"]
    back_aliases = ["grid", "subdeck", "staging", "back"]

    for i in range(1, 5):
        cell = f"Fa-{i}"
        owner = owners[i - 1]
        desc = bio["fauna_cell_desc_template"].format(cell=cell)
        cell_room = _ensure_bio_cell_room(
            staging,
            hub,
            venue_id,
            cell,
            bio["fauna_pad_prefix"],
            desc,
            "fauna pad ",
            back_aliases,
        )
        site_key = f"{bio['fauna_pad_prefix']} {cell} {bio['fauna_site_suffix']}"
        site = _ensure_fauna_site(cell_room, site_key, deposit, colony_label)

        if site.tags.has(tag, category="world"):
            site.db.deposit = dict(deposit)
            print(f"{log_prefix} Fauna already deployed: {site.key!r} in {cell_room.key!r}.")
            continue
        if site.db.is_claimed and site.db.owner and site.db.owner != owner:
            print(f"{log_prefix} Fauna site {site.key!r} claimed by another owner; skip.")
            continue

        components = copy.deepcopy(_fauna_components(colony_label, cell))
        ok, msg = deploy_fauna_colony_site(owner, site, cell_room, components, plant_keys)
        if ok:
            site.tags.add(tag, category="world")
            print(f"{log_prefix} Fauna deployed @ {cell_room.key!r}: {msg.splitlines()[0]}")
        else:
            print(f"{log_prefix} Fauna deploy fail {cell!r}: {msg}")


def _owners_for_units(account, units: list, log_prefix: str):
    owners = []
    for u in units[:4]:
        npc = _ensure_npc_character(account, u["npc_key"], u["npc_desc"])
        if not npc:
            return None
        owners.append(npc)
    return owners


def _bootstrap_bio_for_venue(venue_id: str):
    ind = get_venue(venue_id).get("industrial") or {}
    bio = ind.get("resource_bio")
    if not bio:
        return
    units = ind.get("units") or []
    if len(units) < 4:
        print(
            f"[resource-colony-bio:{venue_id}] need >=4 mine employees for flora/fauna owners; skip."
        )
        return
    account = _target_account()
    if not account:
        print(f"[resource-colony-bio:{venue_id}] No admin/superuser account; skip.")
        return
    owners = _owners_for_units(account, units, f"[resource-colony-bio:{venue_id}]")
    if not owners:
        return
    log_prefix = f"[resource-colony-bio:{venue_id}]"
    _bootstrap_flora_track(venue_id, bio, owners, log_prefix)
    _bootstrap_fauna_track(venue_id, bio, owners, log_prefix)


def _bootstrap_bio_core_industrial_grid():
    bio = CORE_RESOURCE_BIO
    venue_id = CORE_RESOURCE_BIO_VENUE_ID
    account = _target_account()
    if not account:
        print("[resource-colony-bio:core] No admin/superuser account; skip.")
        return
    owners = _owners_for_units(account, NPC_INDUSTRIAL_UNITS, "[resource-colony-bio:core]")
    if not owners:
        return
    log_prefix = "[resource-colony-bio:core]"
    _bootstrap_flora_track(venue_id, bio, owners, log_prefix)
    _bootstrap_fauna_track(venue_id, bio, owners, log_prefix)


def bootstrap_npc_resource_colony_bio():
    for venue_id in all_venue_ids():
        _bootstrap_bio_for_venue(venue_id)
    _bootstrap_bio_core_industrial_grid()
    print("[resource-colony-bio] Bootstrap complete.")
