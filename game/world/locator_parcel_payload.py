"""
Locator parcel rows for Universal Locator (hub-anchored titled parcels).

Claimed lots with a PropertyHolding; optional interior room id when place shell exists.
"""

from __future__ import annotations

from evennia.objects.models import ObjectDB

from typeclasses.property_holdings import (
    PROPERTY_HOLDING_CATEGORY,
    PROPERTY_HOLDING_TAG,
    PROPERTY_HOLDING_TYPECLASS_PATH,
)
from typeclasses.property_lot_registry import infer_lot_venue_id
from world.venue_resolve import hub_room_for_venue


def _hub_id_for_venue(vid: str) -> int | None:
    room = hub_room_for_venue(vid)
    return int(room.id) if room else None


def build_locator_parcel_rows() -> list[dict]:
    """
    One row per titled parcel with a holding and resolved venue hub.
    """
    rows: list[dict] = []

    qs = ObjectDB.objects.filter(db_typeclass_path=PROPERTY_HOLDING_TYPECLASS_PATH)

    for h in qs.iterator(chunk_size=200):
        if not h.tags.has(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY):
            continue
        lot = getattr(h.db, "lot_ref", None)
        if not lot:
            continue
        vid = infer_lot_venue_id(lot)
        hub_id = _hub_id_for_venue(vid)
        if hub_id is None:
            continue

        st = dict(h.db.place_state or {})
        root_id = st.get("root_room_id")
        interior_id = int(root_id) if root_id else None

        rows.append(
            {
                "holdingId": h.id,
                "lotId": lot.id,
                "lotKey": lot.key,
                "venueId": vid,
                "anchorRoomId": hub_id,
                "tier": int(getattr(lot.db, "lot_tier", None) or 1),
                "zone": str(getattr(lot.db, "zone", None) or "residential"),
                "interiorRoomId": interior_id,
            }
        )

    return rows
