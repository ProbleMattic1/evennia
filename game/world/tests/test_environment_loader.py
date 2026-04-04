"""world_environment.json loads and matches venue registry."""

from django.test import SimpleTestCase

from world.environment_loader import clear_world_environment_cache, load_world_environment_config
from world.venues import all_venue_ids


class EnvironmentLoaderTests(SimpleTestCase):
    def tearDown(self):
        clear_world_environment_cache()
        super().tearDown()

    def test_load_matches_all_venues(self):
        cfg = load_world_environment_config()
        self.assertIn("states", cfg)
        self.assertIn("transition", cfg)
        self.assertIn("venues", cfg)
        for vid in all_venue_ids():
            self.assertIn(vid, cfg["venues"])
