"""
SiteDiscoveryEngine — periodic script that generates new unclaimed mining sites.

Runs every DISCOVERY_INTERVAL_SECONDS.  Each tick, if the number of unclaimed
sites is below MAX_UNCLAIMED_SITES, a new site is generated via
claim_utils.generate_mining_site().
"""

from evennia.scripts.scripts import DefaultScript


DISCOVERY_INTERVAL_SECONDS = 3600  # 1 hour
MAX_UNCLAIMED_SITES = 6


class SiteDiscoveryEngine(DefaultScript):
    """Periodically discovers new mining sites for the claims market."""

    def at_script_creation(self):
        self.key = "site_discovery_engine"
        self.desc = "Generates new unclaimed mining sites over time."
        self.interval = DISCOVERY_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True

    def at_repeat(self):
        from typeclasses.claim_utils import generate_mining_site, get_unclaimed_sites

        unclaimed = get_unclaimed_sites()
        if len(unclaimed) >= MAX_UNCLAIMED_SITES:
            return

        site = generate_mining_site()
        print(
            f"[site_discovery] New site discovered: {site.key} "
            f"(unclaimed total: {len(unclaimed) + 1})"
        )
