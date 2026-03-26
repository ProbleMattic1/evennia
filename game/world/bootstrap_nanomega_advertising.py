"""
NanoMegaPlex Advertising Agent NPC + Advertising Agency room on the promenade.

Runs after bootstrap_hub and bootstrap_nanomega_construction (same account pattern
as Construction). Idempotent.
"""

import os

from evennia import create_object, search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    NANOMEGA_ADVERTISING_ABILITY_BASES,
    NANOMEGA_ADVERTISING_CHARACTER_KEY,
)

ADVERTISING_AGENCY_ROOM_KEY = "NanoMegaPlex Advertising Agency"
ADVERTISING_AGENCY_DESC = (
    "Glass-walled suites off the promenade where licensed brokers place tenancy "
    "and income-stream campaigns on sovereign ad bands. Holo rate cards flicker "
    "above a reception counter staffed by the station advertising agent."
)

NANOMEGA_ADVERTISING_CREDITS = 0


def _reset_credits_requested():
    return os.environ.get("NANOMEGA_ADVERTISING_RESET_CREDITS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _reset_stats_requested():
    return os.environ.get("NANOMEGA_ADVERTISING_RESET_STATS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _apply_ability_scores(char):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = NANOMEGA_ADVERTISING_ABILITY_BASES[key]
            trait.mod = 0
            trait.mult = 1.0


def _target_account():
    uname = os.environ.get("NANOMEGA_ADVERTISING_ACCOUNT_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
        print(f"[nanomega-advertising] No account named {uname!r}; falling back to admin.")
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    if acc:
        return acc
    return AccountDB.objects.filter(id=1).first()


def _apply_starting_credits(char):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(char)
    char.db.credits = NANOMEGA_ADVERTISING_CREDITS
    econ.set_balance(acct, NANOMEGA_ADVERTISING_CREDITS)


def _get_or_create_room(key, desc=""):
    found = search_object(key)
    room = found[0] if found else create_object("typeclasses.rooms.Room", key=key)
    if desc:
        room.db.desc = desc
    return room


def _get_or_create_exit(key, aliases, location, destination):
    for obj in location.contents:
        if getattr(obj, "destination", None) == destination and obj.key == key:
            return obj
    return create_object(
        "typeclasses.exits.Exit",
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )


def _wire_hub_and_office():
    from world.bootstrap_hub import get_hub_room

    hub = get_hub_room()
    office = _get_or_create_room(ADVERTISING_AGENCY_ROOM_KEY, ADVERTISING_AGENCY_DESC)
    if hub:
        _get_or_create_exit("advertising", ["ads", "ad agency", "marketing", "agency"], hub, office)
        _get_or_create_exit("promenade", ["back", "exit", "out", "plex", "hub"], office, hub)
    return office


def _place_agent(office):
    found = search_object(NANOMEGA_ADVERTISING_CHARACTER_KEY)
    if not found:
        return
    npc = found[0]
    if npc.location != office:
        npc.move_to(office, quiet=True)
        print(f"[nanomega-advertising] Moved '{npc.key}' into '{office.key}'.")


def bootstrap_nanomega_advertising():
    account = _target_account()
    if not account:
        print("[nanomega-advertising] No account found; skipping.")
        return

    matches = search_object(NANOMEGA_ADVERTISING_CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(
                f"[nanomega-advertising] An object named {NANOMEGA_ADVERTISING_CHARACTER_KEY!r} exists "
                "but is not a Character; skipping."
            )
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        if _reset_stats_requested():
            _apply_ability_scores(char)
            print(f"[nanomega-advertising] Re-applied ability scores for {NANOMEGA_ADVERTISING_CHARACTER_KEY!r}.")
        if _reset_credits_requested():
            _apply_starting_credits(char)
            print(
                f"[nanomega-advertising] Updated {NANOMEGA_ADVERTISING_CHARACTER_KEY!r} credits for "
                f"{account.username}."
            )
        office = _wire_hub_and_office()
        _place_agent(office)
        return

    char, errs = account.create_character(
        key=NANOMEGA_ADVERTISING_CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS_PATH,
    )
    if errs:
        print(f"[nanomega-advertising] create_character failed: {errs}")
        return

    _apply_ability_scores(char)
    char.db.rpg_pointbuy_done = True
    _apply_starting_credits(char)
    print(
        f"[nanomega-advertising] Created {NANOMEGA_ADVERTISING_CHARACTER_KEY!r} for {account.username} "
        f"(#{char.id})."
    )
    office = _wire_hub_and_office()
    _place_agent(office)
