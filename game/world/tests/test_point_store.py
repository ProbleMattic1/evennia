"""Tests for challenge point store loader and refining gates."""

from types import SimpleNamespace

from django.test import SimpleTestCase

from typeclasses.refining import refining_recipe_allowed_for_character
from world.mission_loader import _normalize_mission_row
from world.point_store.point_store_loader import _normalize_point_offer_row


class PointOfferRowValidationTests(SimpleTestCase):
    def test_valid_row(self):
        raw = {
            "id": "x",
            "category": "trait_step",
            "title": "T",
            "summary": "S",
            "costLifetime": 1,
            "costSeason": 0,
            "effect": {"type": "trait_bump", "traitKey": "athletics", "handler": "skills"},
        }
        row, err = _normalize_point_offer_row(raw, "ref")
        self.assertIsNone(err)
        assert row is not None
        self.assertEqual(row["id"], "x")

    def test_rejects_zero_costs(self):
        raw = {
            "id": "x",
            "category": "trait_step",
            "title": "T",
            "summary": "S",
            "costLifetime": 0,
            "costSeason": 0,
            "effect": {"type": "trait_bump", "traitKey": "athletics"},
        }
        row, err = _normalize_point_offer_row(raw, "ref")
        self.assertIsNone(row)
        assert err is not None
        self.assertIn("cost", err)


class MissionEligibilityExtensionTests(SimpleTestCase):
    def test_requires_offer_ids_normalized(self):
        raw = {
            "id": "m1",
            "title": "T",
            "summary": "S",
            "missionKind": "mission",
            "trigger": {"kind": "interaction", "interactionKeysAny": ["a"]},
            "eligibility": {"requiresOfferIds": ["offer_a", ""]},
            "objectives": [
                {
                    "id": "o1",
                    "kind": "interaction",
                    "text": "x",
                    "interactionKeysAny": ["a"],
                }
            ],
        }
        row, err = _normalize_mission_row(raw, "ref")
        self.assertIsNone(err)
        assert row is not None
        self.assertEqual(row["eligibility"]["requiresOfferIds"], ["offer_a"])


class RefiningGateTests(SimpleTestCase):
    def test_synth_blocked_without_unlock(self):
        ch = SimpleNamespace(
            challenges=SimpleNamespace(
                has_refining_recipe_unlock=lambda k: False,
                license_tier=lambda k: 1 if k == "arc_clearance" else 0,
            )
        )
        ok, msg = refining_recipe_allowed_for_character(ch, "synth_lubricant_base")
        self.assertFalse(ok)
        self.assertIn("unlock", msg.lower())

    def test_synth_blocked_without_license(self):
        ch = SimpleNamespace(
            challenges=SimpleNamespace(
                has_refining_recipe_unlock=lambda k: k == "synth_lubricant_base",
                license_tier=lambda k: 0,
            )
        )
        ok, msg = refining_recipe_allowed_for_character(ch, "synth_lubricant_base")
        self.assertFalse(ok)
        self.assertIn("clearance", msg.lower())

    def test_synth_allowed_with_both(self):
        ch = SimpleNamespace(
            challenges=SimpleNamespace(
                has_refining_recipe_unlock=lambda k: k == "synth_lubricant_base",
                license_tier=lambda k: 1 if k == "arc_clearance" else 0,
            )
        )
        ok, _msg = refining_recipe_allowed_for_character(ch, "synth_lubricant_base")
        self.assertTrue(ok)

    def test_public_recipe_always_ok(self):
        ch = SimpleNamespace(challenges=None)
        ok, _msg = refining_recipe_allowed_for_character(ch, "refined_iron")
        self.assertTrue(ok)
