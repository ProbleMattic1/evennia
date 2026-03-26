"""
Ensure Station Guide Kiran exists and is linked to an account. Idempotent.

Places the guide on the NanoMegaPlex Promenade hub. Attaches promenade room ambience.
"""

from evennia import create_script, search_object
from evennia.accounts.models import AccountDB

from commands.npc_promenade import NPCPromenadeCmdSet
from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    PROMENADE_GUIDE_CHARACTER_KEY,
    PROMENADE_GUIDE_ABILITY_BASES,
)
from world.bootstrap_hub import get_hub_room


def _target_account():
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    return acc


def _apply_ability_scores(char):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = PROMENADE_GUIDE_ABILITY_BASES[key]
            trait.mod = 0
            trait.mult = 1.0


def _place_promenade_guide():
    found = search_object(PROMENADE_GUIDE_CHARACTER_KEY)
    if not found:
        return
    npc = found[0]
    room = get_hub_room()
    if not room:
        print("[promenade-guide] Hub not found; guide not placed.")
        return
    if npc.location != room:
        npc.move_to(room, quiet=True)
        print(f"[promenade-guide] Moved {PROMENADE_GUIDE_CHARACTER_KEY!r} to hub.")


def _ensure_npc_cmdset(char):
    if not char.cmdset.has(NPCPromenadeCmdSet):
        char.cmdset.add(NPCPromenadeCmdSet, persistent=True)


def bootstrap_promenade_guide():
    account = _target_account()
    if not account:
        print("[promenade-guide] No account found; skipping.")
        return

    matches = search_object(PROMENADE_GUIDE_CHARACTER_KEY)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print("[promenade-guide] Object exists but is not a Character; skipping.")
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        char.db.is_npc = True
        _ensure_npc_cmdset(char)
        print(f"[promenade-guide] Linked {PROMENADE_GUIDE_CHARACTER_KEY!r} to {account.username}.")
        _place_promenade_guide()
        return

    char, errs = account.create_character(
        key=PROMENADE_GUIDE_CHARACTER_KEY,
        typeclass=CHARACTER_TYPECLASS_PATH,
    )
    if errs:
        print(f"[promenade-guide] create_character failed: {errs}")
        return

    _apply_ability_scores(char)
    char.db.rpg_pointbuy_done = True
    char.db.is_npc = True
    _ensure_npc_cmdset(char)

    print(f"[promenade-guide] Created {PROMENADE_GUIDE_CHARACTER_KEY!r} (#{char.id}).")
    _place_promenade_guide()


def bootstrap_promenade_room_ambience():
    room = get_hub_room()
    if not room:
        print("[promenade-ambience] Hub not found; skipping.")
        return
    if getattr(room.db, "ambience_lines", None) is None:
        room.db.ambience_lines = [
            "A maintenance skiff hums overhead.",
            "Someone argues about berth fees near the transit map.",
        ]
    for s in room.scripts.all():
        if s.key == "room_ambience_promenade":
            return
    create_script(
        "typeclasses.room_ambience_script.RoomAmbienceScript",
        key="room_ambience_promenade",
        obj=room,
        persistent=True,
    )
    print("[promenade-ambience] Attached RoomAmbienceScript to hub.")
