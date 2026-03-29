"""
Ensure the NanoMegaPlex Construction NPC exists and is linked to an account.

Mirrors bootstrap_nanomega_realty: optional env overrides for account, credits reset, stats reset.
"""

import os

from evennia import search_object
from evennia.accounts.models import AccountDB

from world.venue_resolve import hub_room_for_venue
from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    NANOMEGA_CONSTRUCTION_ABILITY_BASES,
    NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
)

NANOMEGA_CONSTRUCTION_CREDITS = 0


def _reset_credits_requested():
    return os.environ.get("NANOMEGA_CONSTRUCTION_RESET_CREDITS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _reset_stats_requested():
    return os.environ.get("NANOMEGA_CONSTRUCTION_RESET_STATS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _apply_construction_ability_scores(char):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = NANOMEGA_CONSTRUCTION_ABILITY_BASES[key]
            trait.mod = 0
            trait.mult = 1.0


def _target_account():
    uname = os.environ.get("NANOMEGA_CONSTRUCTION_ACCOUNT_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
        print(f"[nanomega-construction] No account named {uname!r}; falling back to admin.")
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    if acc:
        return acc
    return AccountDB.objects.filter(id=1).first()


def _apply_construction_credits(char):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(char)
    char.db.credits = NANOMEGA_CONSTRUCTION_CREDITS
    econ.set_balance(acct, NANOMEGA_CONSTRUCTION_CREDITS)


def bootstrap_nanomega_construction():
    account = _target_account()
    if not account:
        print("[nanomega-construction] No account found; skipping NanoMegaPlex Construction.")
        return

    matches = search_object(NANOMEGA_CONSTRUCTION_CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(
                f"[nanomega-construction] An object named {NANOMEGA_CONSTRUCTION_CHARACTER_KEY!r} exists "
                "but is not a Character; skipping."
            )
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        if _reset_stats_requested():
            _apply_construction_ability_scores(char)
            print(
                f"[nanomega-construction] Re-applied ability scores for {NANOMEGA_CONSTRUCTION_CHARACTER_KEY!r}."
            )
        if _reset_credits_requested():
            _apply_construction_credits(char)
            print(
                f"[nanomega-construction] Updated {NANOMEGA_CONSTRUCTION_CHARACTER_KEY!r} for {account.username} "
                f"(credits={NANOMEGA_CONSTRUCTION_CREDITS:,})."
            )
        if not _reset_stats_requested() and not _reset_credits_requested():
            print(
                f"[nanomega-construction] Linked {NANOMEGA_CONSTRUCTION_CHARACTER_KEY!r} to {account.username} "
                "(credits unchanged)."
            )
        return

    hub = hub_room_for_venue("nanomega_core")
    assert hub, "[nanomega-construction] hub missing"
    char, errs = account.create_character(
        key=NANOMEGA_CONSTRUCTION_CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS_PATH,
        location=hub,
    )
    if errs:
        print(f"[nanomega-construction] create_character failed: {errs}")
        return

    _apply_construction_ability_scores(char)
    char.db.rpg_pointbuy_done = True
    _apply_construction_credits(char)
    print(
        f"[nanomega-construction] Created {NANOMEGA_CONSTRUCTION_CHARACTER_KEY!r} for {account.username} "
        f"(#{char.id}, credits={NANOMEGA_CONSTRUCTION_CREDITS:,})."
    )
