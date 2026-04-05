"""Tests for ``world.billboard_library``."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from world.billboard_library import (
    BillboardLibraryError,
    build_ui_ambient_from_selection,
    catalog_for_staff_api,
    load_billboard_library,
    reload_billboard_library_for_tests,
)


class BillboardLibraryTests(SimpleTestCase):
    def tearDown(self):
        reload_billboard_library_for_tests()

    def test_repo_library_loads(self):
        lib = reload_billboard_library_for_tests()
        self.assertIn("NanoMegaPlex Promenade", lib["rooms"])
        self.assertTrue(lib["presets"])
        cat = catalog_for_staff_api(lib)
        self.assertIn("presets", cat)
        self.assertNotIn("_preset_by_id", cat)

    def test_build_ui_ambient_overlay_omit_preserves_preset_image(self):
        lib = reload_billboard_library_for_tests()
        sample = {
            "rooms": ["R1"],
            "images": ["a.webp"],
            "styles": [{"id": "st", "themeId": "promenade", "marqueeClass": "normal"}],
            "presets": [
                {
                    "id": "p1",
                    "label": None,
                    "tagline": None,
                    "bannerSlides": [
                        {
                            "id": "s1",
                            "title": "T",
                            "body": "B",
                            "graphicKey": None,
                            "imageKey": "a.webp",
                        }
                    ],
                    "marqueeLines": ["line"],
                    "chips": [],
                }
            ],
        }
        with TemporaryDirectory() as td:
            p = Path(td) / "billboard_library.json"
            p.write_text(json.dumps(sample), encoding="utf-8")
            with patch("world.billboard_library._LIBRARY_PATH", p):
                reload_billboard_library_for_tests()
                lib2 = load_billboard_library()
                out = build_ui_ambient_from_selection(lib2, preset_id="p1", style_id="st", slide_images=None)
                self.assertEqual(out["bannerSlides"][0]["imageKey"], "a.webp")

    def test_build_explicit_null_clears_image(self):
        sample = {
            "rooms": ["R1"],
            "images": ["a.webp"],
            "styles": [{"id": "st", "themeId": "promenade", "marqueeClass": "normal"}],
            "presets": [
                {
                    "id": "p1",
                    "label": None,
                    "tagline": None,
                    "bannerSlides": [
                        {
                            "id": "s1",
                            "title": "T",
                            "body": "B",
                            "graphicKey": None,
                            "imageKey": "a.webp",
                        }
                    ],
                    "marqueeLines": [],
                    "chips": [],
                }
            ],
        }
        with TemporaryDirectory() as td:
            p = Path(td) / "billboard_library.json"
            p.write_text(json.dumps(sample), encoding="utf-8")
            with patch("world.billboard_library._LIBRARY_PATH", p):
                reload_billboard_library_for_tests()
                lib2 = load_billboard_library()
                out = build_ui_ambient_from_selection(
                    lib2, preset_id="p1", style_id="st", slide_images={"s1": None}
                )
                self.assertIsNone(out["bannerSlides"][0]["imageKey"])

    def test_invalid_preset_raises(self):
        lib = reload_billboard_library_for_tests()
        with self.assertRaises(BillboardLibraryError):
            build_ui_ambient_from_selection(
                lib, preset_id="no-such-preset", style_id="promenade", slide_images=None
            )

    def test_build_ui_ambient_includes_visual_takeover_when_preset_defines_it(self):
        lib = reload_billboard_library_for_tests()
        out = build_ui_ambient_from_selection(
            lib, preset_id="plex-default", style_id="promenade", slide_images=None
        )
        self.assertIn("visualTakeover", out)
        vt = out["visualTakeover"]
        self.assertIsNotNone(vt)
        self.assertEqual(vt["top"]["imageKey"], "nanomega-takeover-top.svg")
        self.assertEqual(vt["sidebar"]["imageKey"], "nanomega-takeover-sidebar.svg")
