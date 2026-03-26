"""
Bootstrap NPCs for promenade_missing_parcel. Idempotent.

Must run after bootstrap_hub and bootstrap_shops.
"""

from evennia import search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    GENERAL_SUPPLY_CLERK_ABILITY_BASES,
    GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
    PARCEL_COMMUTER_ABILITY_BASES,
    PARCEL_COMMUTER_CHARACTER_KEY,
)
from world.bootstrap_hub import get_hub_room


def _target_account():
    return AccountDB.objects.filter(is_superuser=True).order_by("id").first()


def _apply_bases(char, bases):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = bases[key]
            trait.mod = 0
            trait.mult = 1.0


def _ensure_npc(account, key, bases, desc):
    matches = search_object(key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"[parcel-npcs] {key!r} exists but is not a Character; skipping.")
            return None
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        char.db.is_npc = True
        char.db.desc = desc
        _apply_bases(char, bases)
        return char

    char, errs = account.create_character(key=key, typeclass=CHARACTER_TYPECLASS_PATH)
    if errs:
        print(f"[parcel-npcs] create_character {key!r} failed: {errs}")
        return None
    char.db.rpg_pointbuy_done = True
    char.db.is_npc = True
    char.db.desc = desc
    _apply_bases(char, bases)
    print(f"[parcel-npcs] Created {key!r} (#{char.id}).")
    return char


def bootstrap_parcel_mission_npcs():
    account = _target_account()
    if not account:
        print("[parcel-npcs] No account found; skipping.")
        return

    commuter_desc = (
        "A courier shell-jacket, stains at the cuffs, eyes tracking every transit board. "
        "She looks like missing one delivery could cost her the route."
    )
    clerk_desc = (
        "Efficient movements behind the supply counter — the kind of worker who "
        "remembers SKU codes and pretends not to notice irregular routing slips."
    )

    commuter = _ensure_npc(
        account,
        PARCEL_COMMUTER_CHARACTER_KEY,
        PARCEL_COMMUTER_ABILITY_BASES,
        commuter_desc,
    )
    clerk = _ensure_npc(
        account,
        GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
        GENERAL_SUPPLY_CLERK_ABILITY_BASES,
        clerk_desc,
    )

    hub = get_hub_room()
    if hub and commuter and commuter.location != hub:
        commuter.move_to(hub, quiet=True)
        print(f"[parcel-npcs] Placed {PARCEL_COMMUTER_CHARACTER_KEY!r} on hub.")

    supply = search_object("Aurnom General Supply")
    if supply and clerk:
        room = supply[0]
        if clerk.location != room:
            clerk.move_to(room, quiet=True)
            print(f"[parcel-npcs] Placed {GENERAL_SUPPLY_CLERK_CHARACTER_KEY!r} in General Supply.")
