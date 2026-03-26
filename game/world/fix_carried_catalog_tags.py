"""
One-time maintenance: add inventory bucket tags to non-template catalog objects
already owned by players (copies made before templates carried inventory tags).

Run once from an Evennia shell, e.g.:
    python -i manage.py shell  # or: evennia shell
    from world.fix_carried_catalog_tags import run
    run()
"""

from evennia import search_object

from world.bootstrap_shops import CATALOG


def run():
    key_to_bucket = {row[0]: row[4] for row in CATALOG}
    for key, bucket in key_to_bucket.items():
        for obj in search_object(key):
            if getattr(obj.db, "is_template", False):
                continue
            if not obj.tags.has(bucket, category="inventory"):
                obj.tags.add(bucket, category="inventory")
