"""
One-shot migration: Ashfall industrial keys -> Industrial Resource Colony.

Run once per persistent world after deploying renamed bootstrap constants:
  python manage.py migrate_industrial_colony_keys
  python manage.py migrate_industrial_colony_keys --dry-run
"""

from django.core.management.base import BaseCommand
from evennia import search_object
from evennia.objects.models import ObjectDB

OLD_GRID = "Ashfall Industrial Grid"
NEW_GRID = "Industrial Resource Colony Grid"
OLD_PAD_PREFIX = "Ashfall Industrial Pad "
NEW_PAD_PREFIX = "Industrial Resource Colony Pad "
OLD_DEPOSIT_PREFIX = "Ashfall Pad "
NEW_DEPOSIT_PREFIX = "Industrial Resource Colony Pad "
OLD_HUB_EXIT_KEY = "ashfall industrial"
NEW_HUB_EXIT_KEY = "industrial resource colony"
CORE_HUB_KEY = "NanoMegaPlex Promenade"


class Command(BaseCommand):
    help = "Rename Ashfall industrial rooms, mining sites, and promenade exit to Industrial Resource Colony."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log planned renames without writing.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        changed = 0

        def rename_obj(obj, new_key: str, label: str):
            nonlocal changed
            old = obj.key
            if old == new_key:
                return
            self.stdout.write(f"{label}: {old!r} -> {new_key!r}")
            if not dry:
                obj.key = new_key
            changed += 1

        grid_hits = search_object(OLD_GRID)
        if grid_hits:
            rename_obj(grid_hits[0], NEW_GRID, "staging grid")

        for obj in ObjectDB.objects.filter(db_key__startswith=OLD_PAD_PREFIX):
            new_key = NEW_PAD_PREFIX + obj.key[len(OLD_PAD_PREFIX) :]
            rename_obj(obj, new_key, "pad room")

        for obj in ObjectDB.objects.filter(db_key__startswith=OLD_DEPOSIT_PREFIX):
            new_key = NEW_DEPOSIT_PREFIX + obj.key[len(OLD_DEPOSIT_PREFIX) :]
            rename_obj(obj, new_key, "mining site")

        hub_hits = search_object(CORE_HUB_KEY)
        if hub_hits:
            hub = hub_hits[0]
            for ex in hub.contents:
                dest = getattr(ex, "destination", None)
                if not dest:
                    continue
                if dest.key not in (OLD_GRID, NEW_GRID):
                    continue
                if ex.key == OLD_HUB_EXIT_KEY:
                    rename_obj(ex, NEW_HUB_EXIT_KEY, "hub exit")

        if dry:
            self.stdout.write(self.style.WARNING(f"Dry run complete ({changed} renames would apply)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Migration complete ({changed} objects renamed)."))
