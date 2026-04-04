"""Deterministic perception vs stealth resolution."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from world.perception_resolve import resolve_spot


class PerceptionResolveTests(SimpleTestCase):
    def test_spot_when_perception_exceeds_stealth(self):
        obs = MagicMock()
        mover = MagicMock()

        def skill_map(name):
            m = MagicMock()
            m.value = 15 if name == "perception_rating" else 5
            return m if name in ("perception_rating", "stealth_rating") else None

        obs.skills.get.side_effect = skill_map
        mover.skills.get.side_effect = skill_map

        spotted, margin = resolve_spot(obs, mover, room_mod=1.0, environment_mod=1.0)
        self.assertTrue(spotted)
        self.assertEqual(margin, 10)

    def test_no_spot_when_stealth_higher(self):
        obs = MagicMock()
        mover = MagicMock()

        def skill_map(name):
            m = MagicMock()
            m.value = 5 if name == "perception_rating" else 20
            return m if name in ("perception_rating", "stealth_rating") else None

        obs.skills.get.side_effect = skill_map
        mover.skills.get.side_effect = skill_map

        spotted, margin = resolve_spot(obs, mover)
        self.assertFalse(spotted)
        self.assertEqual(margin, -15)
