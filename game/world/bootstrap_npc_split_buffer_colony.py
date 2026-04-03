"""
Parameterized split-buffer Resource Colony mining bootstrap (local reserve + plant bay).

Specs: ``HYBRID_SPLIT_BUFFER_BOOTSTRAP`` (50% default via unset fraction) and
``TIERED_SPLIT_COLONY_SPECS`` (10/25/75/100%). Idempotent per ``site_tag``.
"""

from evennia import create_object

from typeclasses.haulers import ALLOWED_HAUL_LOCAL_PLANT_FILL_FRACTIONS
from typeclasses.packages import _deploy_components_at_site
from world.bootstrap_hub import get_hub_room
from world.bootstrap_mining import _get_or_create_exit
from world.bootstrap_npc_industrial_miners import (
    _components_for_profile,
    _ensure_npc_character,
    _get_or_create_room,
    _pads_for_unit,
    _target_account,
)
from world.mining_bootstrap_presets import catalog_wide_ore_deposit, retune_mining_rigs_on_site
from world.tiered_split_colony_constants import TIERED_SPLIT_COLONY_SPECS
from world.venue_resolve import processing_plant_room_for_npc_autonomous_supply


def apply_split_buffer_colony_haul_attrs(owner, local_plant_fill_fraction=None) -> bool:
    """
    Split-haul: local raw reserve + optional overflow to bay. Destination = core plant.
    If local_plant_fill_fraction is None, clear override (50% default).
    Otherwise must be in ALLOWED_HAUL_LOCAL_PLANT_FILL_FRACTIONS.
    """
    plant = processing_plant_room_for_npc_autonomous_supply()
    if not plant:
        return False
    owner.db.haul_delivers_to_local_raw_storage = True
    owner.db.haul_destination_room = plant
    owner.db.haul_local_reserve_then_plant = True
    if local_plant_fill_fraction is None:
        owner.db.haul_local_plant_fill_fraction = None
        return True
    f = float(local_plant_fill_fraction)
    matched = None
    for a in ALLOWED_HAUL_LOCAL_PLANT_FILL_FRACTIONS:
        if abs(f - float(a)) < 1e-6:
            matched = float(a)
            break
    if matched is None:
        raise ValueError(
            f"local_plant_fill_fraction {local_plant_fill_fraction!r} not in {ALLOWED_HAUL_LOCAL_PLANT_FILL_FRACTIONS!r}"
        )
    owner.db.haul_local_plant_fill_fraction = matched
    return True


def sync_split_buffer_hauler_destinations(owner):
    hdr = getattr(owner.db, "haul_destination_room", None)
    if not hdr:
        return
    for v in owner.db.owned_vehicles or []:
        if getattr(v.db, "hauler_owner", None) != owner:
            continue
        if not (
            v.tags.has("autonomous_hauler", category="mining")
            or v.tags.has("autonomous_hauler", category="flora")
            or v.tags.has("autonomous_hauler", category="fauna")
        ):
            continue
        v.db.hauler_destination_room = hdr


def _ensure_staging_and_hub_link(spec: dict) -> object:
    staging = _get_or_create_room(spec["staging_room_key"], spec["staging_room_desc"])
    hub = get_hub_room()
    if hub:
        _get_or_create_exit(
            spec["hub_to_staging_exit_key"],
            spec["hub_to_staging_aliases"],
            hub,
            staging,
        )
        _get_or_create_exit(
            spec["staging_to_hub_exit_key"],
            spec["staging_to_hub_aliases"],
            staging,
            hub,
        )
    else:
        print(f"{spec['log_prefix']} WARNING: hub missing — no hub link to staging.")
    return staging


def _ensure_cell_room(spec: dict, staging, cell_id: str):
    prefix = spec["pad_colony_prefix"]
    key = f"{prefix} Pad {cell_id}"
    suffix = spec["cell_room_desc_suffix"]
    desc = f"{prefix} pad {cell_id}: {suffix}"
    cell = _get_or_create_room(key, desc)
    ex_key = f"{spec['cell_exit_prefix']}{cell_id.lower().replace(' ', '-')}"
    aliases = [
        cell_id.lower(),
        cell_id.lower().replace(" ", ""),
        f"pad{cell_id.lower().replace(' ', '')}",
    ]
    _get_or_create_exit(ex_key, aliases, staging, cell)
    _get_or_create_exit(
        spec["staging_to_hub_exit_key"],
        ["grid", "staging", "back"],
        cell,
        staging,
    )
    return cell


def _ensure_site_in_room(spec: dict, room, site_key: str, deposit: dict):
    for obj in room.contents:
        if getattr(obj.db, "is_mining_site", False) and obj.key == site_key:
            return obj
    site = create_object(
        "typeclasses.mining.MiningSite",
        key=site_key,
        location=room,
        home=room,
    )
    site.db.desc = spec["site_room_desc"]
    site.db.deposit = dict(deposit)
    site.db.hazard_level = 0.0
    return site


def bootstrap_split_buffer_colony(spec: dict) -> None:
    """Deploy one split-buffer colony from a spec dict (hybrid or tiered)."""
    log_prefix = spec["log_prefix"]
    account = _target_account()
    if not account:
        print(f"{log_prefix} No admin/superuser account; skip.")
        return

    if not processing_plant_room_for_npc_autonomous_supply():
        print(f"{log_prefix} Core processing plant missing; skip.")
        return

    staging = _ensure_staging_and_hub_link(spec)

    deposit = catalog_wide_ore_deposit()
    if not deposit.get("composition"):
        print(f"{log_prefix} RESOURCE_CATALOG empty; skip.")
        return

    site_tag = spec["site_tag"]
    site_tag_category = spec["site_tag_category"]
    frac = spec.get("local_plant_fill_fraction")
    prefix = spec["pad_colony_prefix"]

    for unit in spec["npc_units"]:
        npc = _ensure_npc_character(account, unit["npc_key"], unit["npc_desc"])
        if not npc:
            continue
        try:
            if not apply_split_buffer_colony_haul_attrs(npc, frac):
                print(f"{log_prefix} Could not set haul attrs for {unit['npc_key']!r}; skip unit.")
                continue
        except ValueError as e:
            print(f"{log_prefix} Haul attrs error for {unit['npc_key']!r}: {e}; skip unit.")
            continue
        sync_split_buffer_hauler_destinations(npc)

        for grid_cell in _pads_for_unit(unit["unit_id"]):
            cell_room = _ensure_cell_room(spec, staging, grid_cell)
            site_key = f"{prefix} Pad {grid_cell} Deposit"

            site = _ensure_site_in_room(spec, cell_room, site_key, deposit)
            site.db.hazard_level = 0.0
            if site.tags.has(site_tag, category=site_tag_category):
                site.db.deposit = dict(deposit)
                retune_mining_rigs_on_site(site)
                apply_split_buffer_colony_haul_attrs(npc, frac)
                sync_split_buffer_hauler_destinations(npc)
                print(f"{log_prefix} Already deployed: {site.key!r} in {cell_room.key!r}.")
                continue
            if site.db.is_claimed and site.db.owner and site.db.owner != npc:
                print(f"{log_prefix} Site {site.key!r} claimed by another owner; skip.")
                continue

            components, tier = _components_for_profile(unit["deploy_profile"])

            ok, msg = _deploy_components_at_site(npc, site, cell_room, components, tier)
            if ok:
                site.tags.add(site_tag, category=site_tag_category)
                retune_mining_rigs_on_site(site)
                apply_split_buffer_colony_haul_attrs(npc, frac)
                sync_split_buffer_hauler_destinations(npc)
                print(
                    f"{log_prefix} Deployed {unit['npc_key']!r} @ {cell_room.key!r}: "
                    f"{msg.splitlines()[0]}"
                )
            else:
                print(f"{log_prefix} Deploy failed {unit['npc_key']!r} {grid_cell!r}: {msg}")

    print(f"{log_prefix} Bootstrap complete.")


def bootstrap_npc_tiered_split_colonies():
    for spec in TIERED_SPLIT_COLONY_SPECS:
        bootstrap_split_buffer_colony(spec)
