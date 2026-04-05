from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

from evennia.utils import logger

# -----------------------------------------------------------------------------
# Buckets — add rows here only (order = first match wins).
# Convention: generic goods use tag name == bucket_id, category "inventory".
# Legacy: mining_*, property deeds use existing tags.
# Portable processors use mining tags from PortableProcessor.at_object_creation;
# they bucket as "part" so installable gear appears with other parts.
# -----------------------------------------------------------------------------

InventoryRule = tuple[str, Callable[[Any], bool]]

INVENTORY_RULES: tuple[InventoryRule, ...] = (
    ("flora_claim", lambda o: o.tags.has("flora_claim", category="flora")),
    ("fauna_claim", lambda o: o.tags.has("fauna_claim", category="fauna")),
    ("mining_claim", lambda o: o.tags.has("mining_claim", category="mining")),
    ("flora_package", lambda o: o.tags.has("flora_package", category="flora")),
    ("fauna_package", lambda o: o.tags.has("fauna_package", category="fauna")),
    ("mining_package", lambda o: o.tags.has("mining_package", category="mining")),
    ("property_deed", lambda o: o.tags.has("property_claim", category="realty")),
    ("vehicle", lambda o: o.tags.has("vehicle", category="inventory")),
    ("weapon", lambda o: o.tags.has("weapon", category="inventory")),
    ("tool", lambda o: o.tags.has("tool", category="inventory")),
    ("consumable", lambda o: o.tags.has("consumable", category="inventory")),
    ("novelty", lambda o: o.tags.has("novelty", category="inventory")),
    ("enhancer", lambda o: o.tags.has("enhancer", category="inventory")),
    (
        "part",
        lambda o: o.tags.has("part", category="inventory")
        or o.tags.has("portable_processor", category="mining"),
    ),
    ("blueprint", lambda o: o.tags.has("blueprint", category="inventory")),
)

STACKABLE_BUCKETS: frozenset[str] = frozenset(
    {
        "vehicle",
        "weapon",
        "tool",
        "consumable",
        "novelty",
        "enhancer",
        "part",
        "blueprint",
    }
)

BUCKET_DISPLAY_ORDER: tuple[str, ...] = (
    "flora_claim",
    "fauna_claim",
    "mining_claim",
    "flora_package",
    "fauna_package",
    "mining_package",
    "property_deed",
    "vehicle",
    "weapon",
    "tool",
    "consumable",
    "novelty",
    "enhancer",
    "part",
    "blueprint",
)

BUCKET_LABELS: dict[str, str] = {
    "flora_claim": "Flora claims",
    "fauna_claim": "Fauna claims",
    "mining_claim": "Mining claims",
    "flora_package": "Flora packages",
    "fauna_package": "Fauna packages",
    "mining_package": "Mining packages",
    "property_deed": "Property deeds",
    "vehicle": "Vehicles",
    "weapon": "Weapons",
    "tool": "Tools",
    "consumable": "Consumables",
    "novelty": "Collectibles",
    "enhancer": "Enhancers",
    "part": "Parts",
    "blueprint": "Blueprints",
}


def inventory_bucket(obj: Any) -> str | None:
    for bucket_id, pred in INVENTORY_RULES:
        try:
            if pred(obj):
                return bucket_id
        except Exception as err:
            logger.log_err(
                f"inventory rule crashed for obj id={getattr(obj, 'id', '?')}: {err}"
            )
    return None


def _skip_carried(obj: Any) -> bool:
    if getattr(obj, "destination", None):
        return True
    if getattr(obj.db, "is_template", False):
        return True
    return False


def classify_carried_objects(char: Any) -> dict[str, list[Any]]:
    """Evennia character.contents → bucket → list of objects (unstacked)."""
    out: MutableMapping[str, list[Any]] = defaultdict(list)
    for obj in char.contents:
        if _skip_carried(obj):
            continue
        bid = inventory_bucket(obj)
        if bid is None:
            logger.log_warn(
                f"[inventory] unclassified object id={getattr(obj, 'id', None)!r} "
                f"key={getattr(obj, 'key', None)!r} — omit from payload"
            )
            continue
        out[bid].append(obj)
    return dict(out)


def bucket_stackable(bucket_id: str) -> bool:
    return bucket_id in STACKABLE_BUCKETS


def ordered_bucket_keys(by_bucket: Mapping[str, Any]) -> list[str]:
    seen = set(by_bucket.keys())
    ordered: list[str] = [b for b in BUCKET_DISPLAY_ORDER if b in seen]
    tail = sorted(seen.difference(ordered))
    ordered.extend(tail)
    return ordered


def bucket_labels_for_response() -> dict[str, str]:
    return dict(BUCKET_LABELS)


def empty_inventory_payload() -> dict[str, Any]:
    return {
        "byBucket": {},
        "bucketOrder": [],
        "bucketLabels": bucket_labels_for_response(),
    }


def serialize_inventory_by_bucket(char: Any, item_for_obj: Callable[[Any, Any], dict]) -> dict[str, Any]:
    from evennia.utils import utils

    raw = classify_carried_objects(char)
    by_bucket: dict[str, list] = {}

    for bucket_id, objs in raw.items():
        if not objs:
            continue
        if bucket_stackable(bucket_id):
            rows = []
            for _name, _desc, group in utils.group_objects_by_key_and_desc(objs, caller=char):
                entry = item_for_obj(char, group[0])
                if len(group) > 1:
                    entry["count"] = len(group)
                    entry["stacked"] = True
                    entry["ids"] = [o.id for o in group]
                rows.append(entry)
            by_bucket[bucket_id] = rows
        else:
            by_bucket[bucket_id] = [item_for_obj(char, o) for o in objs]

    return {
        "byBucket": by_bucket,
        "bucketOrder": ordered_bucket_keys(by_bucket),
        "bucketLabels": bucket_labels_for_response(),
    }
