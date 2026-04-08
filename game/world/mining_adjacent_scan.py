"""
Adjacent mining deposits a character can buy (primary deed or property listing).

District scan uses the exit graph (one hop between rooms), not ``mining_district_key``.
"""

from __future__ import annotations

from typing import Any

from evennia.objects.models import ObjectDB

from world.venue_resolve import venue_id_for_object

_EXIT_SUB = "typeclasses.exits.Exit"
_ROOM_SUB = "typeclasses.rooms.Room"


def _tc(obj) -> str:
    return (getattr(obj, "db_typeclass_path", None) or "") or ""


def _is_exit_obj(obj) -> bool:
    return _EXIT_SUB in _tc(obj)


def _is_room_obj(obj) -> bool:
    return _ROOM_SUB in _tc(obj)


def neighbor_rooms(room) -> list[Any]:
    """
    Undirected 1-hop room neighbors: outbound exits from ``room`` plus inbound exits
    whose destination is ``room``.
    """
    if not room:
        return []
    self_id = int(room.id)
    by_id: dict[int, Any] = {}

    for obj in room.contents:
        dest = getattr(obj, "destination", None)
        if not dest or int(dest.id) == self_id:
            continue
        if not _is_exit_obj(obj) or not _is_room_obj(dest):
            continue
        by_id[int(dest.id)] = dest

    inbound = (
        ObjectDB.objects.filter(db_destination=room)
        .exclude(db_location__isnull=True)
        .select_related("db_location")
    )
    for ex in inbound:
        loc = ex.location
        if not loc or int(loc.id) == self_id:
            continue
        if not _is_exit_obj(ex) or not _is_room_obj(loc):
            continue
        by_id[int(loc.id)] = loc

    return list(by_id.values())


def _mining_sites_in_room(room) -> list[Any]:
    if not room:
        return []
    return [o for o in room.contents if o.tags.has("mining_site", category="mining")]


def _purchase_summary_mining(site, buyer) -> dict[str, Any] | None:
    """
    If ``buyer`` can complete a purchase now, return purchase fields; else None.

    Aligns with web ``_serialize_mining_site`` NPC primary path, property listings,
    and ``purchase_property_listing`` balance checks.
    """
    from typeclasses.claim_market import (
        _existing_deed_for_site,
        _validate_site_purchasable,
        get_property_listing_for_site_id,
        listing_price_cr,
        mining_site_primary_deed_eligibility,
    )
    from typeclasses.economy import get_economy

    if not site or not site.tags.has("mining_site", category="mining"):
        return None

    econ = get_economy(create_missing=True)
    balance = int(econ.get_character_balance(buyer))

    pl_ent = get_property_listing_for_site_id(site.id)
    ex_deed = _existing_deed_for_site(site)
    unclaimed = not bool(getattr(site.db, "is_claimed", False))

    if pl_ent is not None:
        seller_id = pl_ent.get("seller_id")
        if seller_id is not None and int(seller_id) == int(buyer.id):
            return None
        price = int(pl_ent.get("price", 0) or 0)
        ok_v, _err_v = _validate_site_purchasable(site, buyer)
        if not ok_v:
            return None
        if balance < price:
            return None
        return {
            "purchaseKind": "player_listing",
            "listingPriceCr": price,
        }

    can_primary_base = unclaimed and ex_deed is None and pl_ent is None
    if not can_primary_base:
        return None
    ok_elig, _err = mining_site_primary_deed_eligibility(site, buyer)
    if not ok_elig:
        return None
    price = int(listing_price_cr(site))
    if balance < price:
        return None
    return {
        "purchaseKind": "npc_primary",
        "listingPriceCr": price,
    }


def list_adjacent_purchasable_mining_peers(character, site) -> list[dict[str, Any]]:
    """
    Mining sites in exit-adjacent rooms (same venue as ``site``) that ``character``
    can buy immediately (NPC primary or active player listing, with sufficient credits).
    """
    if not site or not getattr(site, "location", None):
        return []

    origin_room = site.location
    my_venue = venue_id_for_object(site) or "nanomega_core"

    rows: list[dict[str, Any]] = []
    for room in neighbor_rooms(origin_room):
        if venue_id_for_object(room) != my_venue:
            continue
        for s in _mining_sites_in_room(room):
            ps = _purchase_summary_mining(s, character)
            if not ps:
                continue
            room_obj = s.location
            rows.append(
                {
                    "siteKey": s.key,
                    "roomKey": room_obj.key if room_obj else "",
                    "isClaimed": bool(getattr(s.db, "is_claimed", False)),
                    "surveyLevel": int(getattr(s.db, "survey_level", 0) or 0),
                    "purchaseKind": ps["purchaseKind"],
                    "listingPriceCr": ps["listingPriceCr"],
                }
            )

    rows.sort(key=lambda r: (r["roomKey"], r["siteKey"]))
    return rows
