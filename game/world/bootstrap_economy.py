"""
Ensures the global_economy script exists and has starter modifiers seeded.
Creates one CentralBank per venue (branched treasury accounts on the same engine).

Safe to call multiple times (idempotent).

Called from at_server_cold_start so the script is verified alive on every
cold start (scripts can be deleted accidentally or lost on db reset).
"""

from evennia import create_object, search_object

from world.global_scripts_util import require_global_script

SCRIPT_KEY = "global_economy"

# Seeded on first ledger creation for treasury:alpha-prime only (see bootstrap loop).
INITIAL_ALPHA_PRIME_TREASURY_CR = 100_000_000_000

COMMODITY_DEMAND_KEY = "commodity_demand"
MANUFACTURING_ENGINE_KEY = "manufacturing_engine"


def _get_or_create_room(key, typeclass="typeclasses.rooms.Room", desc=""):
    found = search_object(key)
    if found:
        room = found[0]
    else:
        room = create_object(typeclass, key=key)
    if desc:
        room.db.desc = desc
    return room


def _get_or_create_exit(key, aliases, location, destination, typeclass="typeclasses.exits.Exit"):
    for obj in location.contents:
        if obj.destination == destination and obj.key == key:
            return obj
    return create_object(
        typeclass,
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )


def _get_or_create_bank(room, bank_object_key: str):
    for obj in room.contents:
        if obj.is_typeclass("typeclasses.bank.CentralBank", exact=False):
            return obj
    return create_object(
        "typeclasses.bank.CentralBank",
        key=bank_object_key,
        location=room,
        home=room,
    )


def bootstrap_economy():
    from world.factions_loader import load_factions_config
    from world.manufacturing_loader import load_manufacturing_tables
    from world.venue_resolve import hub_room_for_venue
    from world.venues import all_venue_ids, apply_venue_metadata, get_venue

    load_factions_config()

    _mcat, _mrec, m_err = load_manufacturing_tables()
    assert not m_err, "manufacturing data errors: " + "; ".join(m_err)
    assert set(_mcat) == set(_mrec), "manufacturing catalog/recipe id mismatch"

    econ = require_global_script(SCRIPT_KEY)
    print(f"[economy] Global economy script: {econ.key}")

    econ.set_modifier("regional_modifiers", "core-worlds", 1.08)
    econ.set_modifier("regional_modifiers", "frontier", 0.94)
    econ.set_modifier("location_modifiers", "black-market-exchange", 1.40)
    econ.set_modifier("faction_modifiers", "allied-traders-guild", 0.95)
    econ.set_modifier("category_modifiers", "mining", 1.00)
    if econ.db.accounts is None:
        econ.db.accounts = {}
    if econ.db.transactions is None:
        econ.db.transactions = []
    if econ.db.tax_pool is None:
        econ.db.tax_pool = 0

    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        bspec = vspec["bank"]
        reserve = _get_or_create_room(
            bspec["reserve_room_key"],
            desc=bspec["reserve_room_desc"],
        )
        apply_venue_metadata(reserve, venue_id)
        bank = _get_or_create_bank(reserve, bspec["bank_object_key"])
        bank_id = bspec["bank_id"]
        bank.db.bank_id = bank_id
        treasury_account = econ.get_treasury_account(bank_id)
        bank.db.treasury_account = treasury_account
        accounts_map = econ.db.accounts or {}
        is_new = treasury_account not in accounts_map
        opening = (
            INITIAL_ALPHA_PRIME_TREASURY_CR
            if bank_id == "alpha-prime" and is_new
            else int(accounts_map.get(treasury_account, 0) or 0)
        )
        econ.ensure_account(treasury_account, opening_balance=opening)

        hub = hub_room_for_venue(venue_id)
        if hub:
            _get_or_create_exit("bank", ["alpha", "reserve", "treasury"], hub, reserve)
            _get_or_create_exit("back", ["exit", "promenade", "plex", "hub"], reserve, hub)

        print(f"[economy] Reserve '{bspec['reserve_room_key']}' ({bank_id}) ready.")

    econ.db.tax_pool = econ.get_balance(econ.get_treasury_account("alpha-prime"))

    cd = require_global_script(COMMODITY_DEMAND_KEY)
    print(f"[economy] Commodity demand script: {cd.key}")

    from typeclasses.commodity_demand import seed_procurement_contracts_if_empty

    seed_procurement_contracts_if_empty()

    mf = require_global_script(MANUFACTURING_ENGINE_KEY)
    print(f"[economy] Manufacturing engine script: {mf.key}")

    print("[economy] Seeded starter regional/location/faction modifiers.")

    tel_key = "economy_world_telemetry"
    tel = require_global_script(tel_key)
    print(f"[economy] Telemetry script: {tel.key}")
