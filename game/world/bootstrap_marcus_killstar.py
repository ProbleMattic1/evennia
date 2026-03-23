"""
Ensure Marcus Killstar exists, is linked to the admin account, and has a set credit balance.

Runs from server/conf/at_server_cold_start after bootstrap_hub and bootstrap_economy.
Idempotent.
"""

import os

from evennia import search_object
from evennia.accounts.models import AccountDB

CHARACTER_KEY = "Marcus Killstar"
CHARACTER_TYPECLASS = "typeclasses.characters.Character"
MARCUS_CREDITS = 100_000_000_000


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

    matches = search_object(CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS, exact=False):
            print("[marcus] An object named Marcus Killstar exists but is not a Character; skipping.")
            return
        if char not in account.characters:
            account.characters.add(char)
        account.db._last_puppet = char
        _apply_marcus_credits(char)
        print(f"[marcus] Updated {CHARACTER_KEY} for {account.username} (credits={MARCUS_CREDITS:,}).")
        return

    char, errs = account.create_character(
        key=CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS,
    )
    if errs:
        print(f"[marcus] create_character failed: {errs}")
        return

    _apply_marcus_credits(char)
    account.db._last_puppet = char
    print(f"[marcus] Created {CHARACTER_KEY} for {account.username} (#{char.id}, credits={MARCUS_CREDITS:,}).")
