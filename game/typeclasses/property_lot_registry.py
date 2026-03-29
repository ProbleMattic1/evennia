"""
Indexed list of listable property lot object IDs per venue exchange.

Reads use ObjectDB.objects.filter(id__in=...) instead of search_tag scans.
rebuild_property_exchange_registry(venue_id) rescans tags once per cold start.
"""

from evennia import create_script, search_object, search_script, search_tag
from evennia.objects.models import ObjectDB
from evennia.scripts.scripts import DefaultScript

# Legacy global key (nanomega_core) — unchanged for existing databases
REGISTRY_SCRIPT_KEY = "property_lot_exchange_registry"

# Void storage room keys come from world.venues per venue bootstrap.


class PropertyLotExchangeRegistry(DefaultScript):
    def at_script_creation(self):
        self.desc = "Listable sovereign property lot object IDs (per venue)."
        self.interval = 0
        self.persistent = True
        if self.db.listable_ids is None:
            self.db.listable_ids = []


def exchange_registry_script_key_for_venue(venue_id: str) -> str:
    from world.venues import get_venue

    return str(get_venue(venue_id)["realty"]["exchange_registry_script_key"])


def get_claimed_lots_archive_room_key_for_venue(venue_id: str) -> str:
    from world.venues import get_venue

    return str(get_venue(venue_id)["realty"]["archive_room_key"])


def _lot_still_listable(lot):
    return (
        lot is not None
        and lot.tags.has("property_lot", category="realty")
        and not getattr(lot.db, "is_claimed", False)
    )


def infer_lot_venue_id(lot):
    """Persistent venue_id on lot, else infer from office room key (legacy rows)."""
    v = getattr(lot.db, "venue_id", None)
    if v:
        return str(v)
    loc = lot.location
    if not loc:
        return "nanomega_core"
    lk = str(loc.key)
    if lk == "Frontier Real Estate Office":
        return "frontier_outpost"
    return "nanomega_core"


def get_exchange_registry(venue_id="nanomega_core", create_missing=False):
    key = exchange_registry_script_key_for_venue(venue_id)
    found = search_script(key)
    if found:
        return found[0]
    if create_missing:
        return create_script(PropertyLotExchangeRegistry, key=key)
    return None


def register_listable_property_lot(lot):
    if not lot or not _lot_still_listable(lot):
        return
    vid = infer_lot_venue_id(lot)
    script = get_exchange_registry(vid, create_missing=True)
    ids = list(script.db.listable_ids or [])
    if lot.id in ids:
        return
    ids.append(lot.id)
    script.db.listable_ids = ids


def unregister_listable_property_lot(lot):
    if not lot:
        return
    vid = infer_lot_venue_id(lot)
    script = get_exchange_registry(vid, create_missing=False)
    if not script:
        return
    script.db.listable_ids = [i for i in (script.db.listable_ids or []) if i != lot.id]


def rebuild_property_exchange_registry(venue_id=None):
    from world.venues import all_venue_ids

    def _rebuild_one(vid):
        script = get_exchange_registry(vid, create_missing=True)
        ids = [
            obj.id
            for obj in search_tag("property_lot", category="realty")
            if _lot_still_listable(obj) and infer_lot_venue_id(obj) == vid
        ]
        script.db.listable_ids = sorted(set(ids))

    if venue_id:
        _rebuild_one(venue_id)
    else:
        for vid in all_venue_ids():
            _rebuild_one(vid)


def get_claimed_lots_archive_room(venue_id="nanomega_core"):
    key = get_claimed_lots_archive_room_key_for_venue(venue_id)
    found = search_object(key)
    return found[0] if found else None


def move_lot_to_claimed_archive(lot):
    vid = infer_lot_venue_id(lot)
    archive = get_claimed_lots_archive_room(vid)
    assert archive is not None
    lot.move_to(archive, quiet=True)
    lot.home = archive


def get_listable_lots_from_registry(venue_id="nanomega_core"):
    script = get_exchange_registry(venue_id, create_missing=False)
    if not script:
        return []

    ids = list(script.db.listable_ids or [])
    if not ids:
        return []

    objs = ObjectDB.objects.filter(id__in=ids)
    by_id = {o.id: o for o in objs}

    valid = []
    stale = []
    for pid in ids:
        obj = by_id.get(pid)
        if obj and _lot_still_listable(obj) and infer_lot_venue_id(obj) == venue_id:
            valid.append(obj)
        else:
            stale.append(pid)

    if stale:
        script.db.listable_ids = [i for i in ids if i not in stale]

    return sorted(valid, key=lambda l: (int(l.db.lot_tier or 1), l.key))
