"""Tests for world.econ_automation.sim_metrics normalization."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from world.econ_automation import sim_metrics


class SimMetricsNormalizationTests(SimpleTestCase):
    def test_normalize_commodity_unavailable_zero(self):
        self.assertEqual(sim_metrics.normalize_commodity_pressure({"available": False}), 0.0)

    def test_normalize_commodity_high_stress(self):
        raw = {
            "available": True,
            "highStressFraction": 0.5,
            "meanPriceMultiplier": 1.25,
        }
        p = sim_metrics.normalize_commodity_pressure(raw)
        self.assertGreater(p, 0.4)
        self.assertLessEqual(p, 1.0)

    def test_normalize_logistics(self):
        self.assertEqual(sim_metrics.normalize_logistics_pressure({"available": False}), 0.0)
        self.assertAlmostEqual(
            sim_metrics.normalize_logistics_pressure({"available": True, "dueCount": 20}),
            0.5,
            places=5,
        )

    def test_normalize_property(self):
        self.assertEqual(sim_metrics.normalize_property_pressure({"available": False}), 0.0)
        self.assertAlmostEqual(
            sim_metrics.normalize_property_pressure({"available": True, "activeHoldingCount": 75}),
            0.5,
            places=5,
        )

    def test_raw_commodity_empty_engine(self):
        eng = MagicMock()
        eng.state = {"commodities": {}}
        eng._ensure_commodity_rows = MagicMock()
        raw = sim_metrics.raw_commodity_demand_metrics(eng)
        self.assertFalse(raw["available"])

    def test_raw_commodity_with_rows(self):
        eng = MagicMock()
        eng._ensure_commodity_rows = MagicMock()
        eng.state = {
            "commodities": {
                "a": {"price_multiplier": 1.3, "state": "shortage"},
                "b": {"price_multiplier": 0.95, "state": "surplus"},
            }
        }
        raw = sim_metrics.raw_commodity_demand_metrics(eng)
        self.assertTrue(raw["available"])
        self.assertEqual(raw["commodityCount"], 2)
        self.assertGreater(raw["meanPriceMultiplier"], 1.0)

    def test_suggested_ambient_ids(self):
        self.assertEqual(sim_metrics.suggested_ambient_ids_for_commodity_stress({"available": False}), [])
        ids = sim_metrics.suggested_ambient_ids_for_commodity_stress(
            {"available": True, "meanPriceMultiplier": 1.2, "highStressFraction": 0.2}
        )
        self.assertIn("refinery_backlog", ids)


class SimMetricsHaulerPatchTests(SimpleTestCase):
    @patch("django.utils.timezone.now")
    @patch("world.models.HaulerDispatchRow")
    def test_raw_hauler_metrics(self, mock_row, mock_now):
        filtered = MagicMock()
        filtered.count.return_value = 5
        mock_row.objects.filter.return_value = filtered
        mock_row.objects.count.return_value = 12
        mock_now.return_value = MagicMock()

        raw = sim_metrics.raw_hauler_logistics_metrics()
        self.assertTrue(raw.get("available"))
        self.assertEqual(raw.get("dueCount"), 5)
        self.assertEqual(raw.get("dispatchRowCount"), 12)
