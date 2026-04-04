"""world_clock snapshot shape (gametime mocked)."""

from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase


class WorldClockSnapshotTests(SimpleTestCase):
    @patch("world.world_clock.game_timestamp")
    def test_snapshot_keys_and_day_phase(self, mock_ts):
        # Fixed IC instant: June 15, 2200 14:00 UTC → day / summer
        fixed = datetime(2200, 6, 15, 14, 0, 0, tzinfo=timezone.utc).timestamp()
        mock_ts.return_value = fixed

        from world.world_clock import compute_clock_snapshot

        snap = compute_clock_snapshot()
        self.assertEqual(snap["day_phase"], "day")
        self.assertEqual(snap["season"], "summer")
        self.assertIn("ambient_weight", snap)
        self.assertIn("crime_weight", snap)
        self.assertIn("battlespace_weight", snap)
        self.assertEqual(snap["hour"], 14)
