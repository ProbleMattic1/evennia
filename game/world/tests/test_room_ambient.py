"""Tests for ``world.room_ambient`` merge and defaults."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from world.room_ambient import resolve_room_ambient, resolve_room_venue_id


class ResolveRoomAmbientTests(SimpleTestCase):
    def test_defaults_when_no_room(self):
        out = resolve_room_ambient(None)
        self.assertEqual(out["themeId"], "default")
        self.assertEqual(out["bannerSlides"], [])
        self.assertEqual(out["marqueeLines"], [])
        self.assertEqual(out["chips"], [])
        self.assertIsNone(out["layoutHints"])

    def test_shallow_merge_room_overrides_top_level_keys(self):
        room = MagicMock()
        room.key = "Test Room"
        room.db.venue_id = "nanomega_core"
        room.db.ui_ambient = {"themeId": "industrial", "marqueeLines": ["local line"]}

        with patch("world.room_ambient.get_venue") as gv:
            gv.return_value = {
                "ui_ambient": {
                    "themeId": "promenade",
                    "marqueeLines": ["venue line"],
                    "label": "Venue label",
                    "bannerSlides": [{"id": "v", "title": "T", "body": None, "graphicKey": None}],
                }
            }
            out = resolve_room_ambient(room)

        self.assertEqual(out["themeId"], "industrial")
        self.assertEqual(out["marqueeLines"], ["local line"])
        self.assertEqual(out["label"], "Venue label")
        self.assertEqual(len(out["bannerSlides"]), 1)
        self.assertEqual(out["bannerSlides"][0]["id"], "v")

    def test_resolve_room_venue_id_prefers_db(self):
        room = SimpleNamespace(db=SimpleNamespace(venue_id="frontier_outpost"))
        self.assertEqual(resolve_room_venue_id(room), "frontier_outpost")
