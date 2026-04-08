"""Centralized heavy mission/quest/challenge sync for web polls."""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from web.ui.heavy_mission_quest_challenge_web import run_heavy_mission_quest_challenge_sync_if_due


class HeavyMissionQuestChallengeWebTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_skips_when_throttle_returns_false(self):
        req = self.factory.get("/ui/control-surface")
        req.session = {}
        char = MagicMock()
        char.missions = MagicMock()
        with patch(
            "web.ui.heavy_mission_quest_challenge_web.web_needs_heavy_mission_challenge_sync",
            return_value=False,
        ) as need:
            ran = run_heavy_mission_quest_challenge_sync_if_due(req, char)
        self.assertFalse(ran)
        need.assert_called_once_with(req, char)
        char.missions.sync_global_seeds.assert_not_called()

    def test_runs_full_chain_when_throttle_returns_true(self):
        req = self.factory.get("/ui/control-surface")
        req.session = {}
        loc = MagicMock()
        char = MagicMock()
        char.location = loc
        char.missions = MagicMock()
        char.quests = MagicMock()
        char.challenges = MagicMock()
        with patch(
            "web.ui.heavy_mission_quest_challenge_web.web_needs_heavy_mission_challenge_sync",
            return_value=True,
        ):
            ran = run_heavy_mission_quest_challenge_sync_if_due(req, char)
        self.assertTrue(ran)
        char.missions.sync_global_seeds.assert_called_once_with()
        char.missions.sync_room.assert_called_once_with(loc)
        char.quests.on_room_enter.assert_called_once_with(loc)
        char.challenges.sync_all_windows.assert_called_once_with()
        char.challenges.evaluate_window.assert_called_once_with()

    def test_room_hooks_skipped_when_not_located(self):
        req = self.factory.get("/ui/control-surface")
        req.session = {}
        char = MagicMock()
        char.location = None
        char.missions = MagicMock()
        char.quests = MagicMock()
        char.challenges = MagicMock()
        with patch(
            "web.ui.heavy_mission_quest_challenge_web.web_needs_heavy_mission_challenge_sync",
            return_value=True,
        ):
            run_heavy_mission_quest_challenge_sync_if_due(req, char)
        char.missions.sync_global_seeds.assert_called_once_with()
        char.missions.sync_room.assert_not_called()
        char.quests.on_room_enter.assert_not_called()
        char.challenges.sync_all_windows.assert_called_once_with()
        char.challenges.evaluate_window.assert_called_once_with()
