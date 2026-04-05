"""
FloraSiteDiscoveryEngine — periodic script that generates new unclaimed FloraSites.

Mirrors SiteDiscoveryEngine; uses claim_utils.generate_flora_site.
"""

from datetime import timedelta

from django.utils import timezone
from evennia.scripts.scripts import DefaultScript


DISCOVERY_INTERVAL_SECONDS = 900
MAX_UNCLAIMED_SITES_PER_VENUE = 50


class FloraSiteDiscoveryEngine(DefaultScript):
    """Periodically discovers new flora stands for the claims market."""

    def at_script_creation(self):
        self.key = "flora_site_discovery_engine"
        self.desc = "Generates new unclaimed flora sites over time."
        self.interval = DISCOVERY_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True

    def _set_next_discovery_eta(self):
        self.db.next_discovery_at = timezone.now() + timedelta(seconds=int(self.interval))

    def at_start(self):
        self._set_next_discovery_eta()

    def at_repeat(self):
        from evennia.utils import logger
        from typeclasses.claim_utils import generate_flora_site, get_unclaimed_flora_sites
        from typeclasses.system_alerts import enqueue_system_alert
        from world.venue_resolve import venue_id_for_object
        from world.venues import all_venue_ids

        try:
            for venue_id in all_venue_ids():
                unclaimed = [
                    s
                    for s in get_unclaimed_flora_sites()
                    if (venue_id_for_object(s.location) or "nanomega_core") == venue_id
                ]
                if len(unclaimed) >= MAX_UNCLAIMED_SITES_PER_VENUE:
                    logger.log_info(
                        f"[flora_site_discovery] {venue_id} cap "
                        f"({len(unclaimed)}/{MAX_UNCLAIMED_SITES_PER_VENUE}) — skip."
                    )
                    continue
                site = generate_flora_site(venue_id=venue_id)
                logger.log_info(
                    f"[flora_site_discovery] [{venue_id}] New site: {site.key} "
                    f"(unclaimed in venue: {len(unclaimed) + 1})"
                )
                try:
                    enqueue_system_alert(
                        severity="info",
                        category="market",
                        title="New flora stand listed",
                        detail=f"{site.key} is now available on the claims market.",
                        source=site.key,
                        dedupe_key=f"new-flora-claim:{site.id}",
                    )
                except Exception:
                    pass
                break
        except Exception as err:
            logger.log_err(f"[flora_site_discovery] Error during discovery: {err}")
        finally:
            self._set_next_discovery_eta()
