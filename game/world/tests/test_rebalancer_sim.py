"""Tests for decide_rebalance with sim_metrics-derived pressures."""

from django.test import SimpleTestCase

from world.econ_automation.rebalancer import decide_rebalance


class RebalancerSimSignalsTests(SimpleTestCase):
    def test_sim_scarcity_with_fiscal_strain(self):
        d = decide_rebalance(
            current_phase="stable",
            inflation_pressure=0.40,
            treasury_health=0.50,
            passive_payout_pressure=0.20,
            commodity_pressure=0.80,
            logistics_pressure=0.0,
            property_pressure=0.0,
        )
        self.assertEqual(d.next_phase, "scarcity")
        self.assertIn("stress", d.reason)

    def test_sim_alone_does_not_force_scarcity(self):
        d = decide_rebalance(
            current_phase="stable",
            inflation_pressure=0.10,
            treasury_health=0.80,
            passive_payout_pressure=0.10,
            commodity_pressure=0.95,
            logistics_pressure=0.95,
            property_pressure=0.95,
        )
        self.assertEqual(d.next_phase, "stable")
        self.assertIn("hold", d.reason)

    def test_boom_blocked_by_high_logistics(self):
        d = decide_rebalance(
            current_phase="stable",
            inflation_pressure=0.10,
            treasury_health=0.70,
            passive_payout_pressure=0.10,
            commodity_pressure=0.0,
            logistics_pressure=0.60,
            property_pressure=0.0,
        )
        self.assertNotEqual(d.next_phase, "boom")
