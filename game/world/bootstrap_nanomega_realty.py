"""
Ensure the NanoMegaPlex Real Estate NPC exists and is linked to an account.

NANOMEGA_REALTY_CREDITS is applied only on first create unless
NANOMEGA_REALTY_RESET_CREDITS=1. Stats use NANOMEGA_REALTY_ABILITY_BASES unless
NANOMEGA_REALTY_RESET_STATS=1.

Account: NANOMEGA_REALTY_ACCOUNT_USERNAME if set, else same fallback as Marcus
(EVENNIA_SUPERUSER_USERNAME / first superuser / id 1).
"""

import os

from evennia import search_object
from evennia.accounts.models import AccountDB

from world.venue_resolve import hub_room_for_venue
from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    NANOMEGA_REALTY_CHARACTER_KEY,
    NANOMEGA_REALTY_ABILITY_BASES,
)

NANOMEGA_REALTY_CREDITS = 0


def _reset_credits_requested():
    return os.environ.get("NANOMEGA_REALTY_RESET_CREDITS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _reset_stats_requested():
    return os.environ.get("NANOMEGA_REALTY_RESET_STATS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _apply_realty_ability_scores(char):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = NANOMEGA_REALTY_ABILITY_BASES[key]
            trait.mod = 0
            trait.mult = 1.0


def _target_account():
    uname = os.environ.get("NANOMEGA_REALTY_ACCOUNT_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
        print(f"[nanomega-realty] No account named {uname!r}; falling back to admin.")
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    if acc:
        return acc
    return AccountDB.objects.filter(id=1).first()


def _apply_realty_credits(char):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(char)
    char.db.credits = NANOMEGA_REALTY_CREDITS
    econ.set_balance(acct, NANOMEGA_REALTY_CREDITS)


def bootstrap_nanomega_realty():
    account = _target_account()
    if not account:
        print("[nanomega-realty] No account found; skipping NanoMegaPlex Real Estate.")
        return

    matches = search_object(NANOMEGA_REALTY_CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(
                f"[nanomega-realty] An object named {NANOMEGA_REALTY_CHARACTER_KEY!r} exists "
                "but is not a Character; skipping."
            )
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        if _reset_stats_requested():
            _apply_realty_ability_scores(char)
            print(
                f"[nanomega-realty] Re-applied ability scores for {NANOMEGA_REALTY_CHARACTER_KEY!r}."
            )
        if _reset_credits_requested():
            _apply_realty_credits(char)
            print(
                f"[nanomega-realty] Updated {NANOMEGA_REALTY_CHARACTER_KEY!r} for {account.username} "
                f"(credits={NANOMEGA_REALTY_CREDITS:,})."
            )
        if not _reset_stats_requested() and not _reset_credits_requested():
            print(
                f"[nanomega-realty] Linked {NANOMEGA_REALTY_CHARACTER_KEY!r} to {account.username} "
                "(credits unchanged)."
            )
        return

    hub = hub_room_for_venue("nanomega_core")
    assert hub, "[nanomega-realty] hub missing"
    char, errs = account.create_character(
        key=NANOMEGA_REALTY_CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS_PATH,
        location=hub,
    )
    if errs:
        print(f"[nanomega-realty] create_character failed: {errs}")
        return

    _apply_realty_ability_scores(char)
    char.db.rpg_pointbuy_done = True
    _apply_realty_credits(char)
    print(
        f"[nanomega-realty] Created {NANOMEGA_REALTY_CHARACTER_KEY!r} for {account.username} "
        f"(#{char.id}, credits={NANOMEGA_REALTY_CREDITS:,})."
    )
