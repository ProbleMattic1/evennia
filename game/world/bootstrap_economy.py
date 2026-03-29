"""
Ensures the global_economy script exists and has starter modifiers seeded.
Creates one CentralBank per venue (branched treasury accounts on the same engine).

Safe to call multiple times (idempotent).

Called from at_server_cold_start so the script is verified alive on every
cold start (scripts can be deleted accidentally or lost on db reset).
"""

from evennia import create_object, create_script, search_object, search_script

SCRIPT_PATH = "typeclasses.economy.EconomyEngine"
SCRIPT_KEY = "global_economy"

COMMODITY_DEMAND_PATH = "typeclasses.commodity_demand.CommodityDemandEngine"
COMMODITY_DEMAND_KEY = "commodity_demand"

MANUFACTURING_ENGINE_PATH = "typeclasses.manufacturing.ManufacturingEngine"
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
    from world.manufacturing_loader import load_manufacturing_tables
    from world.venue_resolve import hub_room_for_venue
    from world.venues import all_venue_ids, apply_venue_metadata, get_venue

    _mcat, _mrec, m_err = load_manufacturing_tables()
    assert not m_err, "manufacturing data errors: " + "; ".join(m_err)
    assert set(_mcat) == set(_mrec), "manufacturing catalog/recipe id mismatch"

    found = search_script(SCRIPT_KEY)
    if found:
        econ = found[0]
        print(f"[economy] Script already exists: {econ.key}")
    else:
        econ = create_script(SCRIPT_PATH, key=SCRIPT_KEY)
        print(f"[economy] Created script: {econ.key}")

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
        econ.ensure_account(treasury_account, opening_balance=int(econ.get_balance(treasury_account) or 0))

        hub = hub_room_for_venue(venue_id)
        if hub:
            _get_or_create_exit("bank", ["alpha", "reserve", "treasury"], hub, reserve)
            _get_or_create_exit("back", ["exit", "promenade", "plex", "hub"], reserve, hub)

        print(f"[economy] Reserve '{bspec['reserve_room_key']}' ({bank_id}) ready.")

    econ.db.tax_pool = econ.get_balance(econ.get_treasury_account("alpha-prime"))

    cd_found = search_script(COMMODITY_DEMAND_KEY)
    if cd_found:
        print(f"[economy] Commodity demand script already exists: {cd_found[0].key}")
    else:
        cd = create_script(COMMODITY_DEMAND_PATH, key=COMMODITY_DEMAND_KEY)
        print(f"[economy] Created commodity demand script: {cd.key}")

    from typeclasses.commodity_demand import seed_procurement_contracts_if_empty

    seed_procurement_contracts_if_empty()

    mf_found = search_script(MANUFACTURING_ENGINE_KEY)
    if mf_found:
        print(f"[economy] Manufacturing engine script already exists: {mf_found[0].key}")
    else:
        mf = create_script(MANUFACTURING_ENGINE_PATH, key=MANUFACTURING_ENGINE_KEY)
        print(f"[economy] Created manufacturing engine script: {mf.key}")

    print("[economy] Seeded starter regional/location/faction modifiers.")

    tel_key = "economy_world_telemetry"
    tel_found = search_script(tel_key)
    if tel_found:
        print(f"[economy] {tel_key} already exists")
    else:
        create_script("typeclasses.economy_world_telemetry.EconomyWorldTelemetry", key=tel_key)
        print(f"[economy] Created script: {tel_key}")
