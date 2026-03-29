"""Periodic restock: per venue, up to one R/C/I lot per tick while listable count < cap."""

from datetime import timedelta

from django.utils import timezone
from evennia.scripts.scripts import DefaultScript

from typeclasses.property_claim_market import get_listable_lots
from typeclasses.property_exchange_limits import MAX_LISTABLE_PROPERTY_LOTS_PER_VENUE
from typeclasses.property_lot_generation import generate_market_property_lot
from typeclasses.system_alerts import enqueue_system_alert
from world.venues import all_venue_ids

DISCOVERY_INTERVAL_SECONDS = 900
ZONES_PER_TICK = ("residential", "commercial", "industrial")


class PropertyLotDiscoveryEngine(DefaultScript):
    def at_script_creation(self):
        self.key = "property_lot_discovery_engine"
        self.desc = "Restocks procedural property lots when a venue exchange is below cap."
        self.interval = DISCOVERY_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True

    def _set_next_eta(self):
        self.db.next_discovery_at = timezone.now() + timedelta(seconds=int(self.interval))

    def at_start(self):
        self._set_next_eta()

    def at_repeat(self):
        from evennia.utils import logger

        def count_listable(venue_id):
            return len(get_listable_lots(venue_id))

        for venue_id in all_venue_ids():
            if count_listable(venue_id) >= MAX_LISTABLE_PROPERTY_LOTS_PER_VENUE:
                logger.log_info(
                    f"[property_lot_discovery] {venue_id} cap "
                    f"({count_listable(venue_id)}/{MAX_LISTABLE_PROPERTY_LOTS_PER_VENUE}) — skip."
                )
                continue
            created_keys = []
            for zone in ZONES_PER_TICK:
                if count_listable(venue_id) >= MAX_LISTABLE_PROPERTY_LOTS_PER_VENUE:
                    break
                lot = generate_market_property_lot(zone, venue_id=venue_id)
                created_keys.append(f"{venue_id}:{lot.key}")
                logger.log_info(
                    f"[property_lot_discovery] [{venue_id}] New {zone}: {lot.key} "
                    f"(listable {count_listable(venue_id)})"
                )
            if created_keys:
                enqueue_system_alert(
                    severity="info",
                    category="market",
                    title="Property exchange restocked",
                    detail="New parcels: " + ", ".join(created_keys),
                    source="property_lot_discovery",
                    dedupe_key="property-restocks:" + ",".join(sorted(created_keys)),
                )

        self._set_next_eta()
