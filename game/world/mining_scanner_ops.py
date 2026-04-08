"""
Mining scanner deploy / pickup and district scan — shared by telnet commands and web UI.

Rules mirror ``CmdDeployMiningScanner``, ``CmdUndeployMiningScanner``, and ``CmdDistrictScan``.
"""

from __future__ import annotations

from typing import Any

from world.mining_district_survey import (
    DISTRICT_SCAN_COOLDOWN_KEY,
    DISTRICT_SCAN_COOLDOWN_SEC,
    list_district_peers,
)
from world.mining_survey_ops import resolve_mining_site_in_room, room_has_deployed_scanner

_SCANNER_TYPE = "typeclasses.mining_scanner.MiningScanner"


def resolve_scanner_in_inventory(character, scanner_object_id: int):
    """Return MiningScanner in ``character.contents`` with given db id, or None."""
    for obj in character.contents:
        if obj.id != scanner_object_id:
            continue
        if not obj.is_typeclass(_SCANNER_TYPE, exact=False):
            return None
        return obj
    return None


def resolve_deployed_scanner_in_room(room, character, *, scanner_object_id: int | None = None, key_fragment: str | None = None):
    """
    Find caller's deployed scanner in ``room.contents``.
    If ``scanner_object_id`` is set, match by id only; else match ``key_fragment`` substring on key.
    """
    if not room:
        return None
    frag = (key_fragment or "").strip().lower() or None
    for obj in room.contents:
        if not obj.is_typeclass(_SCANNER_TYPE, exact=False):
            continue
        if getattr(obj.db, "owner", None) != character:
            continue
        if scanner_object_id is not None:
            if obj.id == int(scanner_object_id):
                return obj
            continue
        if frag is not None and frag in (obj.key or "").lower():
            return obj
    return None


def _pick_scanner_by_fragment(caller, fragment: str):
    frag = (fragment or "").strip().lower()
    if not frag:
        return None
    for obj in caller.contents:
        if not obj.is_typeclass(_SCANNER_TYPE, exact=False):
            continue
        if frag in (obj.key or "").lower():
            return obj
    return None


def attempt_deploy_scanner(
    character,
    *,
    scanner_object_id: int | None = None,
    name_fragment: str | None = None,
) -> tuple[bool, str]:
    """
    Deploy a carried scanner at the mining site in ``character.location``.

    Exactly one of ``scanner_object_id`` (web) or ``name_fragment`` (telnet) must identify the scanner.
    """
    has_id = scanner_object_id is not None
    has_frag = bool((name_fragment or "").strip())
    if has_id and has_frag:
        return False, "Use either scanner object id or name fragment, not both."
    if not has_id and not has_frag:
        return False, "Specify a scanner (object id or name fragment)."

    loc = character.location
    site = resolve_mining_site_in_room(loc)
    if not site:
        return False, "There is no mining deposit here."
    if site.db.is_claimed and site.db.owner != character:
        return False, "This deposit is claimed by someone else."

    if has_id:
        scanner = resolve_scanner_in_inventory(character, int(scanner_object_id))
        if not scanner:
            return False, "You are not carrying a Mining Scanner with that id."
    else:
        scanner = _pick_scanner_by_fragment(character, name_fragment or "")
        if not scanner:
            return False, "You are not carrying a matching Mining Scanner."

    if getattr(scanner.db, "is_deployed", False):
        return False, "That scanner is already deployed. Pick it up first."
    try:
        scanner.deploy_at_site(character, site)
    except ValueError as exc:
        return False, str(exc)
    return (
        True,
        f"You deploy {scanner.key} at {site.key}. "
        "Use survey or district scan while it remains here.",
    )


def attempt_undeploy_scanner(
    character,
    *,
    scanner_object_id: int | None = None,
    key_fragment: str | None = None,
) -> tuple[bool, str]:
    """Recover a deployed scanner from ``character.location`` to inventory."""
    loc = character.location
    if not loc:
        return False, "You are nowhere."

    has_uid = scanner_object_id is not None
    has_frag = bool((key_fragment or "").strip())
    if has_uid and has_frag:
        return False, "Use either scannerObjectId or scannerKeyFragment, not both."
    if not has_uid and not has_frag:
        return False, "Specify scannerObjectId or scannerKeyFragment."

    if has_uid:
        target = resolve_deployed_scanner_in_room(
            loc, character, scanner_object_id=int(scanner_object_id), key_fragment=None
        )
    else:
        target = resolve_deployed_scanner_in_room(
            loc,
            character,
            scanner_object_id=None,
            key_fragment=(key_fragment or "").strip(),
        )
    if target is None:
        return False, "No deployed scanner of yours here matches that request."
    try:
        target.undeploy_to_inventory(character)
    except ValueError as exc:
        return False, str(exc)
    return True, f"You pack up {target.key}."


def attempt_district_scan(character) -> tuple[bool, str | None, list[dict[str, Any]], str]:
    """
    Run district scan: adjacent purchasable mining peers, with cooldown and scanner gate.

    On success: ``(True, None, peers, anchor_room_key)`` — ``peers`` may be empty;
    ``anchor_room_key`` is the deposit room key for display.
    On failure: ``(False, error_message, [], "")``.
    """
    if not character.cooldowns.ready(DISTRICT_SCAN_COOLDOWN_KEY):
        left = float(character.cooldowns.time_left(DISTRICT_SCAN_COOLDOWN_KEY))
        return False, f"District array is still recharging ({left:.1f}s).", [], ""

    loc = character.location
    site = resolve_mining_site_in_room(loc)
    if not site:
        return False, "There is no mining deposit here.", [], ""
    if not room_has_deployed_scanner(loc, character, site):
        return (
            False,
            "You need a deployed Mining Scanner at this deposit (deployminingscanner).",
            [],
            "",
        )

    peers = list_district_peers(character, site)
    character.cooldowns.add(DISTRICT_SCAN_COOLDOWN_KEY, DISTRICT_SCAN_COOLDOWN_SEC)
    loc = getattr(site, "location", None)
    anchor = str(loc.key) if loc and getattr(loc, "key", None) else ""

    return True, None, peers, anchor
