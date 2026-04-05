"""Tests for world.progression reward XP helpers."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from world.progression import apply_reward_xp, xp_from_rewards


class XpFromRewardsTests(SimpleTestCase):
    def test_missing_and_empty(self):
        self.assertEqual(xp_from_rewards(None), 0)
        self.assertEqual(xp_from_rewards({}), 0)

    def test_positive(self):
        self.assertEqual(xp_from_rewards({"xp": 50}), 50)
        self.assertEqual(xp_from_rewards({"xp": 0}), 0)

    def test_invalid_xp_raises(self):
        with self.assertRaises(ValueError):
            xp_from_rewards({"xp": "nope"})


class ApplyRewardXpTests(SimpleTestCase):
    def test_zero_no_call(self):
        ch = MagicMock()
        self.assertEqual(apply_reward_xp(ch, {}, reason="test"), 0)
        ch.grant_xp.assert_not_called()

    def test_positive_calls_grant_xp(self):
        ch = MagicMock()
        ch.grant_xp = MagicMock()
        self.assertEqual(apply_reward_xp(ch, {"xp": 25}, reason="mission reward"), 25)
        ch.grant_xp.assert_called_once_with(25, reason="mission reward")

    def test_missing_grant_xp_raises(self):
        ch = object()
        with self.assertRaises(TypeError):
            apply_reward_xp(ch, {"xp": 10}, reason="x")
