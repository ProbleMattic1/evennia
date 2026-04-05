"""Mission/quest completion calls achievement hooks."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from typeclasses.missions import MissionHandler, _blank_state as mission_blank
from typeclasses.quests import QuestHandler, _blank_state as quest_blank


class MissionAchievementHookTests(SimpleTestCase):
    @patch("world.achievement_hooks.track_mission_completed")
    def test_complete_mission_tracks(self, mock_track):
        char = MagicMock()
        char.attributes.get.return_value = mission_blank()
        char.db.morality = None

        handler = MissionHandler(char)
        mission = {"id": "mid", "templateId": "tid"}
        tmpl = {"id": "tid", "objectives": [], "rewards": {}}
        handler._complete_mission(mission, tmpl)
        mock_track.assert_called_once_with(char)


class QuestAchievementHookTests(SimpleTestCase):
    @patch("world.achievement_hooks.track_quest_completed")
    def test_complete_quest_tracks(self, mock_track):
        char = MagicMock()
        char.attributes.get.return_value = quest_blank()

        handler = QuestHandler(char)
        quest = {"id": "qid", "templateId": "qtid"}
        tmpl = {"id": "qtid", "objectives": [], "rewards": {}}
        handler._complete_quest(quest, tmpl)
        mock_track.assert_called_once_with(char)
