from django.core.management.base import BaseCommand
from evennia.utils.search import search_tag

from typeclasses.haulers import set_hauler_next_cycle
from world.venue_resolve import processing_plant_room_for_npc_autonomous_supply


class Command(BaseCommand):
    help = (
        "Point all autonomous haulers owned by NPCs at the core plant "
        "(nanomega_core Ore Receiving Bay / treasury). Clears haul_destination_room. "
        "Reschedules dispatch rows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print actions without changing objects.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        plant = processing_plant_room_for_npc_autonomous_supply()
        if not plant:
            self.stderr.write(self.style.ERROR("Core plant room (nanomega_core) not found."))
            return

        changed = 0
        skipped = 0
        for cat in ("mining", "flora", "fauna"):
            for h in search_tag("autonomous_hauler", category=cat):
                owner = h.db.hauler_owner
                if not owner or not getattr(owner.db, "is_npc", False):
                    skipped += 1
                    continue
                rid = getattr(getattr(h.db, "hauler_refinery_room", None), "id", None)
                hdr = getattr(h.db, "haul_destination_room", None)
                if rid == plant.id and not hdr:
                    skipped += 1
                    continue
                self.stdout.write(
                    f"{'[dry-run] ' if dry else ''}hauler #{h.id} {h.key} -> {plant.key}"
                )
                if not dry:
                    h.db.hauler_refinery_room = plant
                    if hdr:
                        h.db.haul_destination_room = None
                    set_hauler_next_cycle(h)
                changed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry else 'Updated'} {changed} hauler(s); skipped {skipped}."
            )
        )
