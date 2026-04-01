"""
Ensure Marcus Killstar exists and is linked to the admin account.

Initial credit seed (MARCUS_CREDITS) runs only when the character is first created.
Existing characters keep their ledger balance unless MARCUS_RESET_CREDITS is set.

Ability scores use MARCUS_ABILITY_BASES (see typeclasses.characters). Set MARCUS_RESET_STATS=1
to re-apply those bases to an existing Marcus.

Runs from server/conf/at_server_cold_start after bootstrap_hub and bootstrap_economy,
before promenade/station NPC bootstraps (lowest Character id on the admin account after first setup).
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
MARCUS_CREDITS = 500_000_000_000

# Killstar autonomous haulers deliver to local raw reserve in this room (not the ore plant).
MARCUS_LOCAL_RAW_WAREHOUSE_ROOM_KEY = "Marcus Killstar Mining Annex"


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


def ensure_marcus_local_raw_destination(char):
    """
    Idempotent: local raw MiningStorage in Marcus Killstar Mining Annex, haul_destination_room,
    sync autonomous hauler db.hauler_destination_room for this owner.
    No-op if char is missing or haul_delivers_to_local_raw_storage is False, or annex not spawned yet.
    """
    if not char or not getattr(char.db, "haul_delivers_to_local_raw_storage", False):
        return
    from typeclasses.haulers import ensure_local_raw_storage, set_hauler_next_cycle

    hits = search_object(MARCUS_LOCAL_RAW_WAREHOUSE_ROOM_KEY)
    room = None
    for o in hits:
        if hasattr(o, "contents"):
            room = o
            break
    if not room:
        return

    st = ensure_local_raw_storage(room, char)
    char.db.local_raw_storage = st
    char.db.haul_destination_room = room

    for v in char.db.owned_vehicles or []:
        if not getattr(v.db, "is_vehicle", False):
            continue
        if not (
            v.tags.has("autonomous_hauler", category="mining")
            or v.tags.has("autonomous_hauler", category="flora")
            or v.tags.has("autonomous_hauler", category="fauna")
        ):
            continue
        if getattr(v.db, "hauler_owner", None) != char:
            continue
        v.db.hauler_destination_room = room
        try:
            set_hauler_next_cycle(v)
        except Exception:
            pass


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
        char.db.haul_delivers_to_local_raw_storage = True
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
    char.db.haul_delivers_to_local_raw_storage = True
    _apply_marcus_credits(char)
    account.db._last_puppet = char
    print(
        f"[marcus] Created {MARCUS_CHARACTER_KEY} for {account.username} (#{char.id}, credits={MARCUS_CREDITS:,})."
    )
