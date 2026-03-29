"""
Advertising agency rooms per venue + agent placement.

NanoMegaPlex agent: full account / reset env handling.
Frontier agent: created in bootstrap_frontier_service_npcs; this wires the room and placement.
"""

import os

from evennia import create_object, search_object
from evennia.accounts.models import AccountDB

from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    FRONTIER_ADVERTISING_CHARACTER_KEY,
    NANOMEGA_ADVERTISING_ABILITY_BASES,
    NANOMEGA_ADVERTISING_CHARACTER_KEY,
)
from world.venue_resolve import hub_room_for_venue
from world.venues import all_venue_ids, apply_venue_metadata, get_venue

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


def _wire_venue_advertising(venue_id: str):
    vspec = get_venue(venue_id)
    adv = vspec["advertising"]
    hub = hub_room_for_venue(venue_id)
    office = _get_or_create_room(adv["room_key"], adv["room_desc"])
    apply_venue_metadata(office, venue_id)
    if hub:
        _get_or_create_exit(
            adv["hub_exit"],
            adv["hub_aliases"],
            hub,
            office,
        )
        _get_or_create_exit(
            "promenade",
            ["back", "exit", "out", "plex", "hub"],
            office,
            hub,
        )
    return office


def _place_agent(office, npc_key: str):
    found = search_object(npc_key)
    if not found:
        return
    npc = found[0]
    if npc.location != office:
        npc.move_to(office, quiet=True)
        print(f"[advertising] Moved '{npc.key}' into '{office.key}'.")


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
            print(
                f"[nanomega-advertising] Re-applied ability scores for "
                f"{NANOMEGA_ADVERTISING_CHARACTER_KEY!r}."
            )
        if _reset_credits_requested():
            _apply_starting_credits(char)
            print(
                f"[nanomega-advertising] Updated {NANOMEGA_ADVERTISING_CHARACTER_KEY!r} credits for "
                f"{account.username}."
            )
        office = _wire_venue_advertising("nanomega_core")
        _place_agent(office, NANOMEGA_ADVERTISING_CHARACTER_KEY)
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
    office = _wire_venue_advertising("nanomega_core")
    _place_agent(office, NANOMEGA_ADVERTISING_CHARACTER_KEY)


def bootstrap_frontier_advertising_wiring():
    """After frontier NPC exists: agency room + exit wiring + placement."""
    office = _wire_venue_advertising("frontier_outpost")
    _place_agent(office, FRONTIER_ADVERTISING_CHARACTER_KEY)
