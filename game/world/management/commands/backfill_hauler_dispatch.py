from django.core.management.base import BaseCommand
from evennia.utils.search import search_tag

from typeclasses.haulers import set_hauler_next_cycle


class Command(BaseCommand):
    help = "Rebuild HaulerDispatchRow from all autonomous haulers (run after adding the table)."

    def handle(self, *args, **options):
        haulers = (
            list(search_tag("autonomous_hauler", category="mining"))
            + list(search_tag("autonomous_hauler", category="flora"))
            + list(search_tag("autonomous_hauler", category="fauna"))
        )
        n = 0
        for h in haulers:
            if not getattr(h.db, "is_vehicle", False):
                continue
            set_hauler_next_cycle(h)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Synced dispatch rows for {n} haulers."))
