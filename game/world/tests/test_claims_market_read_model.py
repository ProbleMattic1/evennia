"""Claims market snapshot read model (import/build API surface)."""

from django.test import SimpleTestCase


class ClaimsMarketReadModelModuleTests(SimpleTestCase):
    def test_module_exports_callables(self):
        from world import claims_market_read_model as m

        self.assertTrue(callable(m.build_claims_market_snapshot_payload))
        self.assertTrue(callable(m.refresh_claims_market_snapshot))
        self.assertTrue(callable(m.get_claims_market_snapshot))
        self.assertTrue(callable(m.invalidate_claims_market_snapshot))
