"""
Ensures the global_economy script exists and has starter modifiers seeded.
Safe to call multiple times (idempotent).

Called from at_server_cold_start so the script is verified alive on every
cold start (scripts can be deleted accidentally or lost on db reset).
"""

from evennia import create_object, create_script, search_object, search_script

SCRIPT_PATH = "typeclasses.economy.EconomyEngine"
SCRIPT_KEY = "global_economy"


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


def _get_or_create_bank(room):
    for obj in room.contents:
        if obj.is_typeclass("typeclasses.bank.CentralBank", exact=False):
            return obj
    return create_object("typeclasses.bank.CentralBank", key="Alpha Prime", location=room, home=room)


def bootstrap_economy():
    found = search_script(SCRIPT_KEY)
    if found:
        econ = found[0]
        print(f"[economy] Script already exists: {econ.key}")
    else:
        econ = create_script(SCRIPT_PATH, key=SCRIPT_KEY)
        print(f"[economy] Created script: {econ.key}")

    # Idempotent: set_modifier is always a dict write, safe to repeat.
    econ.set_modifier("regional_modifiers", "core-worlds", 1.08)
    econ.set_modifier("regional_modifiers", "frontier", 0.94)
    econ.set_modifier("location_modifiers", "black-market-exchange", 1.40)
    econ.set_modifier("faction_modifiers", "allied-traders-guild", 0.95)
    if econ.db.accounts is None:
        econ.db.accounts = {}
    if econ.db.transactions is None:
        econ.db.transactions = []
    if econ.db.tax_pool is None:
        econ.db.tax_pool = 0

    treasury_account = econ.get_treasury_account("alpha-prime")
    econ.ensure_account(treasury_account, opening_balance=econ.db.tax_pool or 0)
    econ.db.tax_pool = econ.get_balance(treasury_account)

    reserve = _get_or_create_room(
        "Alpha Prime Central Reserve",
        desc="A secure treasury chamber of armored terminals, sovereign seals, and reserve ledgers.",
    )
    bank = _get_or_create_bank(reserve)
    bank.db.bank_id = "alpha-prime"
    bank.db.treasury_account = treasury_account

    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()
    if hub:
        _get_or_create_exit("bank", ["alpha", "reserve"], hub, reserve)
        _get_or_create_exit("back", ["exit", "promenade", "plex", "hub"], reserve, hub)

    print("[economy] Seeded starter regional/location/faction modifiers.")
    print(f"[economy] Treasury account ready: {treasury_account}")
    print("[economy] Alpha Prime Central Reserve ready.")
