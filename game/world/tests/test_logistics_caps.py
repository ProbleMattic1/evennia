"""Per-venue hauler and refinery ingress caps (pure helpers)."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class LogisticsCapsTests(SimpleTestCase):
    def test_haul_budget_clamps_and_tracks_per_venue(self):
        from typeclasses.haulers import _consume_venue_haul_tick_budget

        room = MagicMock()
        budget = {}
        with patch("world.venues.venue_id_for_object", return_value="v_test"):
            with patch(
                "world.venue_logistics.get_venue_logistics",
                return_value={
                    "max_hauler_tons_per_tick": 5.0,
                    "refinery_ingress_cap_tons": 1e12,
                },
            ):
                self.assertEqual(_consume_venue_haul_tick_budget(room, 8.0, budget), 5.0)
                self.assertEqual(budget.get("v_test"), 5.0)
                self.assertEqual(_consume_venue_haul_tick_budget(room, 3.0, budget), 0.0)

    def test_refinery_ingress_clamp(self):
        from commands.refining import _clamp_bay_feed_tons

        plant = MagicMock()
        with patch("world.venues.venue_id_for_object", return_value="v_test"):
            with patch(
                "world.venue_logistics.get_venue_logistics",
                return_value={
                    "max_hauler_tons_per_tick": 1e12,
                    "refinery_ingress_cap_tons": 12.5,
                },
            ):
                self.assertEqual(_clamp_bay_feed_tons(plant, 100.0), 12.5)
                self.assertEqual(_clamp_bay_feed_tons(plant, 3.0), 3.0)
