"""Tests for world.achievement_snapshot."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from world.achievement_snapshot import achievement_dashboard_block, _prereqs_satisfied


class PrereqTests(SimpleTestCase):
    def test_empty(self):
        self.assertTrue(_prereqs_satisfied({}, None))
        self.assertTrue(_prereqs_satisfied({}, []))

    def test_single(self):
        p = {"parent": {"completed": True}}
        self.assertTrue(_prereqs_satisfied(p, "parent"))
        self.assertFalse(_prereqs_satisfied({}, "parent"))


@patch("world.achievement_snapshot._player_progress_blob")
@patch("world.achievement_snapshot.ach.all_achievements")
class AchievementDashboardBlockTests(SimpleTestCase):
    def test_summary_and_progress(self, mock_all, mock_blob):
        mock_all.return_value = {
            "alpha": {
                "name": "Alpha",
                "desc": "d",
                "category": "misc",
                "tracking": "t",
                "count": 3,
            },
        }
        mock_blob.return_value = {"alpha": {"progress": 1}}
        block = achievement_dashboard_block(MagicMock())
        self.assertEqual(block["total"], 1)
        self.assertEqual(block["completed"], 0)
        self.assertEqual(block["completed"], sum(1 for i in block["items"] if i["completed"]))
        self.assertEqual(block["items"][0]["progress"], 1)
        self.assertEqual(block["items"][0]["target"], 3)
        self.assertFalse(block["items"][0]["locked"])

    def test_completed_row(self, mock_all, mock_blob):
        mock_all.return_value = {
            "done": {
                "name": "Done",
                "desc": "",
                "category": "misc",
                "count": 1,
            },
        }
        mock_blob.return_value = {"done": {"completed": True, "progress": 1}}
        block = achievement_dashboard_block(MagicMock())
        self.assertEqual(block["completed"], 1)
        self.assertTrue(block["items"][0]["completed"])
        self.assertEqual(block["items"][0]["progress"], 1)
        self.assertEqual(block["items"][0]["target"], 1)

    def test_locked_prereq(self, mock_all, mock_blob):
        mock_all.return_value = {
            "parent": {
                "name": "Parent",
                "desc": "",
                "category": "c",
                "count": 1,
            },
            "child": {
                "name": "Child",
                "desc": "",
                "category": "c",
                "prereqs": "parent",
                "count": 1,
            },
        }
        mock_blob.return_value = {"child": {"progress": 1}}
        block = achievement_dashboard_block(MagicMock())
        by_key = {r["key"]: r for r in block["items"]}
        self.assertTrue(by_key["child"]["locked"])
        self.assertEqual(by_key["child"]["progress"], 0)

        mock_blob.return_value = {"parent": {"completed": True}, "child": {"progress": 1}}
        block = achievement_dashboard_block(MagicMock())
        by_key = {r["key"]: r for r in block["items"]}
        self.assertFalse(by_key["child"]["locked"])
        self.assertEqual(by_key["child"]["progress"], 1)
