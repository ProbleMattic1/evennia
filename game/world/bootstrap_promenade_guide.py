"""
Ensure promenade guides exist per venue hub. Idempotent.

Core: Station Guide Kiran on NanoMegaPlex Promenade.
Frontier: Frontier Station Guide on Frontier Promenade.
"""

from evennia import create_script, search_object
from evennia.accounts.models import AccountDB

from commands.npc_promenade import NPCPromenadeCmdSet
from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY,
    FRONTIER_PROMENADE_GUIDE_ABILITY_BASES,
    PROMENADE_GUIDE_CHARACTER_KEY,
    PROMENADE_GUIDE_ABILITY_BASES,
)
from world.venue_resolve import hub_room_for_venue


def _target_account():
    acc = AccountDB.objects.filter(is_superuser=True).order_by("id").first()
    return acc


def _apply_ability_scores(char, bases: dict):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = bases[key]
            trait.mod = 0
            trait.mult = 1.0


def _ensure_npc_cmdset(char):
    if not char.cmdset.has(NPCPromenadeCmdSet):
        char.cmdset.add(NPCPromenadeCmdSet, persistent=True)


def _ensure_guide(
    account,
    character_key: str,
    ability_bases: dict,
    venue_id: str,
    log_label: str,
):
    hub = hub_room_for_venue(venue_id)
    if not hub:
        print(f"[promenade-guide] {log_label}: hub not found; skip.")
        return

    matches = search_object(character_key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"[promenade-guide] {character_key!r} exists but is not a Character; skip.")
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        char.db.is_npc = True
        _ensure_npc_cmdset(char)
        if char.location != hub:
            char.move_to(hub, quiet=True)
            print(f"[promenade-guide] Moved {character_key!r} to {hub.key!r}.")
        return

    char, errs = account.create_character(
        key=character_key,
        typeclass=CHARACTER_TYPECLASS_PATH,
        location=hub,
    )
    if errs:
        print(f"[promenade-guide] create_character {character_key!r} failed: {errs}")
        return

    _apply_ability_scores(char, ability_bases)
    char.db.rpg_pointbuy_done = True
    char.db.is_npc = True
    _ensure_npc_cmdset(char)
    print(f"[promenade-guide] Created {character_key!r} (#{char.id}) on {hub.key!r}.")


def bootstrap_promenade_guide():
    account = _target_account()
    if not account:
        print("[promenade-guide] No account found; skipping.")
        return

    _ensure_guide(
        account,
        PROMENADE_GUIDE_CHARACTER_KEY,
        PROMENADE_GUIDE_ABILITY_BASES,
        "nanomega_core",
        "core",
    )
    _ensure_guide(
        account,
        FRONTIER_PROMENADE_GUIDE_CHARACTER_KEY,
        FRONTIER_PROMENADE_GUIDE_ABILITY_BASES,
        "frontier_outpost",
        "frontier",
    )


def bootstrap_promenade_room_ambience():
    from world.venues import all_venue_ids, get_venue

    for venue_id in all_venue_ids():
        room = hub_room_for_venue(venue_id)
        if not room:
            print(f"[promenade-ambience] No hub for {venue_id}; skip.")
            continue
        if getattr(room.db, "ambience_lines", None) is None:
            room.db.ambience_lines = [
                "A maintenance skiff hums overhead.",
                "Someone argues about berth fees near the transit map.",
            ]
        script_key = f"room_ambience_promenade__{venue_id}"
        for s in room.scripts.all():
            if s.key == script_key:
                break
        else:
            create_script(
                "typeclasses.room_ambience_script.RoomAmbienceScript",
                key=script_key,
                obj=room,
                persistent=True,
            )
            print(f"[promenade-ambience] Attached RoomAmbienceScript to {room.key!r}.")
