"""
Ensure Marcus Killstar exists and is linked to the admin account.

Initial credit seed (MARCUS_CREDITS) runs only when the character is first created.
Existing characters keep their ledger balance unless MARCUS_RESET_CREDITS is set.

Ability scores use MARCUS_ABILITY_BASES (see typeclasses.characters). Set MARCUS_RESET_STATS=1
to re-apply those bases to an existing Marcus.

Runs from server/conf/at_server_cold_start after bootstrap_hub and bootstrap_economy.
Idempotent for linkage; credits are not reset each cold start by default.
"""

import os

from evennia import search_object
from evennia.accounts.models import AccountDB

from world.bootstrap_hub import get_hub_room
from typeclasses.characters import (
    ABILITY_KEYS,
    MARCUS_ABILITY_BASES,
    MARCUS_CHARACTER_KEY,
)

CHARACTER_TYPECLASS = "typeclasses.characters.Character"
MARCUS_CREDITS = 1_000_000_000_000


def _marcus_reset_credits_requested():
    return os.environ.get("MARCUS_RESET_CREDITS", "").strip().lower() in ("1", "true", "yes")


def _marcus_reset_stats_requested():
    return os.environ.get("MARCUS_RESET_STATS", "").strip().lower() in ("1", "true", "yes")


def _apply_marcus_ability_scores(char):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = MARCUS_ABILITY_BASES[key]
            trait.mod = 0
            trait.mult = 1.0


def _admin_account():
    """Prefer Docker superuser username, then first superuser, then account #1."""
    uname = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "").strip()
    if uname:
        acc = AccountDB.objects.filter(username__iexact=uname).first()
        if acc:
            return acc
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    if acc:
        return acc
    return AccountDB.objects.filter(id=1).first()


def _apply_marcus_credits(char):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(char)
    char.db.credits = MARCUS_CREDITS
    econ.set_balance(acct, MARCUS_CREDITS)


def bootstrap_marcus_killstar():
    account = _admin_account()
    if not account:
        print("[marcus] No admin account found; skipping Marcus Killstar.")
        return

    matches = search_object(MARCUS_CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS, exact=False):
            print(
                f"[marcus] An object named {MARCUS_CHARACTER_KEY} exists but is not a Character; skipping."
            )
            return
        if char not in account.characters:
            account.characters.add(char)
        hub = get_hub_room()
        if hub and not char.location:
            char.move_to(hub)
        account.db._last_puppet = char
        char.db.rpg_pointbuy_done = True
        char.db.mining_owner_uses_npc_production = True
        if _marcus_reset_stats_requested():
            _apply_marcus_ability_scores(char)
            print(f"[marcus] Re-applied ability scores for {MARCUS_CHARACTER_KEY}.")
        if _marcus_reset_credits_requested():
            _apply_marcus_credits(char)
            print(f"[marcus] Updated {MARCUS_CHARACTER_KEY} for {account.username} (credits={MARCUS_CREDITS:,}).")
        if not _marcus_reset_stats_requested() and not _marcus_reset_credits_requested():
            print(f"[marcus] Linked {MARCUS_CHARACTER_KEY} to {account.username} (credits unchanged).")
        return

    hub = get_hub_room()
    assert hub, "[marcus] hub missing"
    char, errs = account.create_character(
        key=MARCUS_CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS,
        location=hub,
    )
    if errs:
        print(f"[marcus] create_character failed: {errs}")
        return

    _apply_marcus_ability_scores(char)
    char.db.rpg_pointbuy_done = True
    char.db.mining_owner_uses_npc_production = True
    _apply_marcus_credits(char)
    account.db._last_puppet = char
    print(
        f"[marcus] Created {MARCUS_CHARACTER_KEY} for {account.username} (#{char.id}, credits={MARCUS_CREDITS:,})."
    )
