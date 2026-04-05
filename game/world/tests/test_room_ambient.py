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
        self.assertIsNone(out["visualTakeover"])

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

    def test_slide_image_key_and_marquee_class_merge(self):
        room = MagicMock()
        room.key = "Test Room"
        room.db.venue_id = None
        room.db.ui_ambient = {
            "marqueeClass": "slow",
            "bannerSlides": [{"id": "x", "title": "A", "body": None, "graphicKey": None, "imageKey": " ad.webp "}],
        }

        with patch("world.room_ambient.resolve_room_venue_id", return_value=None):
            out = resolve_room_ambient(room)

        self.assertEqual(out["marqueeClass"], "slow")
        self.assertEqual(out["bannerSlides"][0]["imageKey"], "ad.webp")

    def test_invalid_marquee_class_normalized_to_none(self):
        room = MagicMock()
        room.key = "Test Room"
        room.db.venue_id = None
        room.db.ui_ambient = {"marqueeClass": "bogus"}

        with patch("world.room_ambient.resolve_room_venue_id", return_value=None):
            out = resolve_room_ambient(room)

        self.assertIsNone(out["marqueeClass"])

    def test_visual_takeover_deep_merge_and_normalize(self):
        room = MagicMock()
        room.key = "Test Room"
        room.db.venue_id = "nanomega_core"
        room.db.ui_ambient = {
            "visualTakeover": {
                "sidebar": {"imageKey": "custom-rail.svg", "position": "right"},
                "tokens": {"takeoverAccent": "#ff00ff"},
            }
        }

        with patch("world.room_ambient.get_venue") as gv:
            gv.return_value = {
                "ui_ambient": {
                    "visualTakeover": {
                        "top": {"imageKey": "nanomega-takeover-top.svg", "alt": "Core"},
                        "sidebar": {"imageKey": "nanomega-takeover-sidebar.svg", "position": "left"},
                        "tokens": {"takeoverVignette": "0.2"},
                    }
                }
            }
            out = resolve_room_ambient(room)

        vt = out["visualTakeover"]
        self.assertIsNotNone(vt)
        self.assertEqual(vt["top"]["imageKey"], "nanomega-takeover-top.svg")
        self.assertEqual(vt["sidebar"]["imageKey"], "custom-rail.svg")
        self.assertEqual(vt["sidebar"]["position"], "right")
        self.assertEqual(vt["tokens"]["takeoverVignette"], "0.2")
        self.assertEqual(vt["tokens"]["takeoverAccent"], "#ff00ff")

    def test_visual_takeover_invalid_image_key_dropped(self):
        room = MagicMock()
        room.key = "Test Room"
        room.db.venue_id = None
        room.db.ui_ambient = {
            "visualTakeover": {
                "top": {"imageKey": "../etc/passwd", "graphicKey": "promenade"},
            }
        }

        with patch("world.room_ambient.resolve_room_venue_id", return_value=None):
            out = resolve_room_ambient(room)

        vt = out["visualTakeover"]
        self.assertIsNotNone(vt)
        self.assertIsNone(vt["top"].get("imageKey"))
        self.assertEqual(vt["top"]["graphicKey"], "promenade")

    def test_resolve_room_venue_id_prefers_db(self):
        room = SimpleNamespace(db=SimpleNamespace(venue_id="frontier_outpost"))
        self.assertEqual(resolve_room_venue_id(room), "frontier_outpost")
