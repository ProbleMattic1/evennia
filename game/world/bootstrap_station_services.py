"""
Station service NPCs (listings broker, haul dispatcher, refinery analyst,
claims agent, contract clerk) on the NanoMegaPlex hub promenade. Idempotent.

Also seeds the global StationContractsScript if empty.
"""

from evennia import search_object

from typeclasses.characters import (
    ABILITY_KEYS,
    CHARACTER_TYPECLASS_PATH,
    CLAIMS_AGENT_CHARACTER_KEY,
    CONTRACT_CLERK_CHARACTER_KEY,
    HAUL_DISPATCHER_CHARACTER_KEY,
    LISTINGS_BROKER_CHARACTER_KEY,
    REFINERY_ANALYST_CHARACTER_KEY,
    STATION_SERVICE_NPC_ABILITY_BASES,
)
from typeclasses.station_contracts import get_contracts_script
from world.venue_resolve import hub_room_for_venue


def _target_account():
    from evennia.accounts.models import AccountDB

    return AccountDB.objects.filter(is_superuser=True).order_by("id").first()


def _apply_ability_scores(char, bases: dict):
    char.ensure_default_rpg_traits()
    for key in ABILITY_KEYS:
        trait = char.stats.get(key)
        if trait:
            trait.base = bases[key]
            trait.mod = 0
            trait.mult = 1.0


def _ensure_station_npc(account, character_key: str, venue_id: str = "nanomega_core"):
    hub = hub_room_for_venue(venue_id)
    if not hub:
        print(f"[station-services] hub not found for {venue_id}; skip {character_key!r}.")
        return

    matches = search_object(character_key)
    if matches:
        char = matches[0]
        if not char.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
            print(f"[station-services] {character_key!r} exists but is not a Character; skip.")
            return
        if char not in account.characters:
            account.characters.add(char)
        char.db.rpg_pointbuy_done = True
        char.db.is_npc = True
        if char.location != hub:
            char.move_to(hub, quiet=True)
            print(f"[station-services] Moved {character_key!r} to {hub.key!r}.")
        return

    char, errs = account.create_character(
        key=character_key,
        typeclass=CHARACTER_TYPECLASS_PATH,
        location=hub,
    )
    if errs:
        print(f"[station-services] create_character {character_key!r} failed: {errs}")
        return

    _apply_ability_scores(char, STATION_SERVICE_NPC_ABILITY_BASES)
    char.db.rpg_pointbuy_done = True
    char.db.is_npc = True
    print(f"[station-services] Created {character_key!r} (#{char.id}) on {hub.key!r}.")


def _seed_contracts():
    sc = get_contracts_script(create_missing=True)
    if not sc:
        print("[station-services] Could not create station_contracts script.")
        return
    if sc.db.contracts:
        return
    sc.db.contracts = [
        {
            "id": "PKG-001",
            "title": "List a mining package at this venue",
            "payout": 500,
            "predicate_key": "list_package",
            "venue_id": "nanomega_core",
        },
        {
            "id": "REF-001",
            "title": "Collect refined output at the processing plant",
            "payout": 350,
            "predicate_key": "refine_collect",
            "venue_id": None,
        },
        {
            "id": "CLM-001",
            "title": "List a mining claim deed at this venue",
            "payout": 400,
            "predicate_key": "list_claim",
            "venue_id": "nanomega_core",
        },
        {
            "id": "PDE-001",
            "title": "List a property deed at this venue",
            "payout": 400,
            "predicate_key": "list_property_deed",
            "venue_id": "nanomega_core",
        },
    ]
    print("[station-services] Seeded default station contracts.")


def bootstrap_station_services():
    account = _target_account()
    if not account:
        print("[station-services] No account found; skipping NPCs.")
    else:
        for key in (
            LISTINGS_BROKER_CHARACTER_KEY,
            HAUL_DISPATCHER_CHARACTER_KEY,
            REFINERY_ANALYST_CHARACTER_KEY,
            CLAIMS_AGENT_CHARACTER_KEY,
            CONTRACT_CLERK_CHARACTER_KEY,
        ):
            _ensure_station_npc(account, key, "nanomega_core")

    _seed_contracts()
