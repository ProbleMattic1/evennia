"""
Periodic rebuild of claims-market JSON (listable sites + listings) for fast GET /ui/claims-market.
"""

from typeclasses.scripts import Script


class ClaimsMarketSnapshotScript(Script):
    def at_script_creation(self):
        self.key = "claims_market_snapshot"
        self.desc = "Cached rows for /ui/claims-market and /ui/mine/claims"
        self.persistent = True
        self.interval = 45
        self.repeats = 0
        self.start_delay = False
        self.db.snapshot = {}

    def at_start(self):
        self._run()

    def at_repeat(self, **kwargs):
        self._run()

    def _run(self):
        from world.claims_market_read_model import refresh_claims_market_snapshot

        refresh_claims_market_snapshot()
