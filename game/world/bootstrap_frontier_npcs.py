"""
Frontier venue service NPCs (realty, construction, advertising). Idempotent.

Mirrors NanoMega bootstrap patterns; characters use FRONTIER_* keys in typeclasses.characters.
"""

import os

from evennia import search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    FRONTIER_ADVERTISING_CHARACTER_KEY,
    FRONTIER_CONSTRUCTION_CHARACTER_KEY,
    FRONTIER_REALTY_CHARACTER_KEY,
    NANOMEGA_ADVERTISING_ABILITY_BASES,
    NANOMEGA_CONSTRUCTION_ABILITY_BASES,
    NANOMEGA_REALTY_ABILITY_BASES,
)
from world.venue_resolve import hub_room_for_venue


def _target_account():
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    return AccountDB.objects.filter(is_superuser=True).order_by("id").first()


def _apply_bases(char, bases: dict):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = bases[key]
            trait.mod = 0
            trait.mult = 1.0


def _apply_zero_credits(char):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(char)
    char.db.credits = 0
    econ.set_balance(acct, 0)


def _ensure_character(account, key: str, bases: dict, *, location):
    matches = search_object(key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"[frontier-npcs] {key!r} exists but is not a Character; skip.")
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        _apply_bases(char, bases)
        if char.location != location:
            char.move_to(location, quiet=True)
        print(f"[frontier-npcs] Linked {key!r}.")
        return

    char, errs = account.create_character(
        key=key,
        typeclass=CHARACTER_TYPECLASS_PATH,
        location=location,
    )
    if errs:
        print(f"[frontier-npcs] create_character {key!r} failed: {errs}")
        return
    _apply_bases(char, bases)
    char.db.rpg_pointbuy_done = True
    _apply_zero_credits(char)
    print(f"[frontier-npcs] Created {key!r} (#{char.id}).")


def bootstrap_frontier_service_npcs():
    account = _target_account()
    if not account:
        print("[frontier-npcs] No account found; skipping.")
        return

    hub = hub_room_for_venue("frontier_outpost")
    if not hub:
        print("[frontier-npcs] Frontier hub missing; skipping.")
        return

    _ensure_character(
        account,
        FRONTIER_REALTY_CHARACTER_KEY,
        NANOMEGA_REALTY_ABILITY_BASES,
        location=hub,
    )
    _ensure_character(
        account,
        FRONTIER_CONSTRUCTION_CHARACTER_KEY,
        NANOMEGA_CONSTRUCTION_ABILITY_BASES,
        location=hub,
    )
    _ensure_character(
        account,
        FRONTIER_ADVERTISING_CHARACTER_KEY,
        NANOMEGA_ADVERTISING_ABILITY_BASES,
        location=hub,
    )
