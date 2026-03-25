"""
Indexed list of listable property lot object IDs for the sovereign exchange.

Reads use ObjectDB.objects.filter(id__in=...) instead of search_tag scans.
Stale IDs are removed when encountered. rebuild_property_exchange_registry()
rescans tags once per cold start (O(all lots), not per HTTP request).

Sold lots are moved to CLAIMED_LOTS_ARCHIVE_ROOM_KEY so the office room
stays a trading floor, not an archive.
"""

from evennia import create_script, search_object, search_script, search_tag
from evennia.objects.models import ObjectDB
from evennia.scripts.scripts import DefaultScript

REGISTRY_SCRIPT_KEY = "property_lot_exchange_registry"

# Void storage — created by bootstrap_realty_office; not linked from the hub.
CLAIMED_LOTS_ARCHIVE_ROOM_KEY = "Property Lots Archive"


class PropertyLotExchangeRegistry(DefaultScript):
    def at_script_creation(self):
        self.key = REGISTRY_SCRIPT_KEY
        self.desc = "Listable sovereign property lot object IDs."
        self.interval = 0
        self.persistent = True
        if self.db.listable_ids is None:
            self.db.listable_ids = []


def get_exchange_registry(create_missing=False):
    found = search_script(REGISTRY_SCRIPT_KEY)
    if found:
        return found[0]
    if create_missing:
        return create_script(PropertyLotExchangeRegistry)
    return None


def _lot_still_listable(lot):
    return (
        lot is not None
        and lot.tags.has("property_lot", category="realty")
        and not getattr(lot.db, "is_claimed", False)
    )


def register_listable_property_lot(lot):
    if not lot or not _lot_still_listable(lot):
        return
    script = get_exchange_registry(create_missing=True)
    ids = list(script.db.listable_ids or [])
    if lot.id in ids:
        return
    ids.append(lot.id)
    script.db.listable_ids = ids


def unregister_listable_property_lot(lot):
    if not lot:
        return
    script = get_exchange_registry(create_missing=False)
    if not script:
        return
    script.db.listable_ids = [i for i in (script.db.listable_ids or []) if i != lot.id]


def rebuild_property_exchange_registry():
    script = get_exchange_registry(create_missing=True)
    ids = [
        obj.id
        for obj in search_tag("property_lot", category="realty")
        if _lot_still_listable(obj)
    ]
    script.db.listable_ids = sorted(set(ids))


def get_claimed_lots_archive_room():
    found = search_object(CLAIMED_LOTS_ARCHIVE_ROOM_KEY)
    return found[0] if found else None


def move_lot_to_claimed_archive(lot):
    archive = get_claimed_lots_archive_room()
    assert archive is not None
    lot.move_to(archive, quiet=True)
    lot.home = archive


def get_listable_lots_from_registry():
    script = get_exchange_registry(create_missing=False)
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
        if obj and _lot_still_listable(obj):
            valid.append(obj)
        else:
            stale.append(pid)

    if stale:
        script.db.listable_ids = [i for i in ids if i not in stale]

    return sorted(valid, key=lambda l: (int(l.db.lot_tier or 1), l.key))
