"""Smoke: mission templates match commodity emergency seed id."""

from django.test import SimpleTestCase

from world.mission_loader import load_mission_templates, matching_templates_for_seed


class MissionCommoditySeedMatchingTests(SimpleTestCase):
    def test_commodity_emergency_pulse_matches(self):
        load_mission_templates()
        seed = {
            "kind": "alert",
            "seedId": "commodity_emergency_pulse",
            "sourceKey": "test",
        }
        matches = matching_templates_for_seed(seed)
        ids = {m["id"] for m in matches}
        self.assertIn("econ_commodity_emergency_pulse", ids)
