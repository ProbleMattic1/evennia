"""
SiteDiscoveryEngine — periodic script that generates new unclaimed mining sites.

Runs every DISCOVERY_INTERVAL_SECONDS.  Each tick, if the number of unclaimed
sites is below MAX_UNCLAIMED_SITES, a new site is generated via
claim_utils.generate_mining_site().
"""

from datetime import timedelta

from django.utils import timezone
from evennia.scripts.scripts import DefaultScript


DISCOVERY_INTERVAL_SECONDS = 900  # 15 minutes
MAX_UNCLAIMED_SITES = 100


class SiteDiscoveryEngine(DefaultScript):
    """Periodically discovers new mining sites for the claims market."""

    def at_script_creation(self):
        self.key = "site_discovery_engine"
        self.desc = "Generates new unclaimed mining sites over time."
        self.interval = DISCOVERY_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True

    def _set_next_discovery_eta(self):
        """Persist next repeat time for Django/UI (ndb task is not visible there)."""
        self.db.next_discovery_at = timezone.now() + timedelta(seconds=int(self.interval))

    def at_start(self):
        self._set_next_discovery_eta()

    def at_repeat(self):
        from evennia.utils import logger
        from typeclasses.claim_utils import generate_mining_site, get_unclaimed_sites

        try:
            unclaimed = get_unclaimed_sites()
            if len(unclaimed) >= MAX_UNCLAIMED_SITES:
                logger.log_info(
                    f"[site_discovery] Cap reached ({len(unclaimed)}/{MAX_UNCLAIMED_SITES})"
                    f" — skipping discovery this tick."
                )
            else:
                site = generate_mining_site()
                logger.log_info(
                    f"[site_discovery] New site discovered: {site.key} "
                    f"(unclaimed total: {len(unclaimed) + 1})"
                )
        except Exception as err:
            logger.log_err(f"[site_discovery] Error during discovery: {err}")
        finally:
            self._set_next_discovery_eta()
