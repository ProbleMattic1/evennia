"""Perk defs loader, resolver aggregation, and challenge loadout validation."""

from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from world.challenges.challenge_handler import CHALLENGE_ATTR_CATEGORY, CHALLENGE_ATTR_KEY, ChallengeHandler
from world.point_store.perk_defs_loader import _normalize_perk_row
from world.point_store import perk_resolver as perk_resolver_mod
from typeclasses.refining import RAW_SALE_FEE_RATE, split_raw_sale_payout
from world.point_store.perk_resolver import (
    clamped_fee_rate,
    mining_output_multiplier,
    processing_fee_multiplier,
)


class _MockAttributes:
    def __init__(self):
        self._blob: dict | None = None

    def get(self, key, category=None, default=None):
        if key == CHALLENGE_ATTR_KEY and str(category) == CHALLENGE_ATTR_CATEGORY:
            return self._blob
        return default

    def add(self, key, val, category=None):
        if key == CHALLENGE_ATTR_KEY and str(category) == CHALLENGE_ATTR_CATEGORY:
            self._blob = val


class PerkDefsLoaderTests(SimpleTestCase):
    def test_normalize_accepts_title_and_mechanics(self):
        raw = {
            "id": "test_perk_row",
            "title": "T",
            "summary": "S",
            "miningOutputMult": 1.1,
            "processingFeeMult": 0.9,
        }
        row, err = _normalize_perk_row(raw, "ref")
        self.assertIsNone(err)
        assert row is not None
        self.assertEqual(row["title"], "T")
        self.assertEqual(row["miningOutputMult"], 1.1)
        self.assertEqual(row["hazardGeoFloorMult"], 1.0)

    def test_normalize_rejects_out_of_range(self):
        raw = {"id": "bad", "title": "x", "miningOutputMult": 99.0}
        row, err = _normalize_perk_row(raw, "ref")
        self.assertIsNone(row)
        assert err is not None


class PerkResolverTests(SimpleTestCase):
    def test_product_over_equipped(self):
        char = SimpleNamespace(
            challenges=SimpleNamespace(equipped_perk_ids=lambda: ["a", "b"])
        )
        fake_defs = {
            "a": {"miningOutputMult": 2.0},
            "b": {"miningOutputMult": 1.5},
        }
        with mock.patch.object(perk_resolver_mod, "get_perk_def", side_effect=lambda pid: fake_defs.get(pid)):
            self.assertEqual(mining_output_multiplier(char), 3.0)

    def test_clamped_fee_rate(self):
        self.assertEqual(clamped_fee_rate(0.1, 0.5), 0.05)
        self.assertEqual(clamped_fee_rate(0.5, 3.0), 1.0)

    def test_processing_fee_mult_defaults_without_challenges(self):
        char = SimpleNamespace()
        self.assertEqual(processing_fee_multiplier(char), 1.0)


class RefiningPerkHookTests(SimpleTestCase):
    def test_split_raw_sale_respects_fee_mult(self):
        net, fee = split_raw_sale_payout(10000, fee_mult=0.5)
        eff = clamped_fee_rate(RAW_SALE_FEE_RATE, 0.5)
        self.assertEqual(fee, int(round(10000 * eff)))
        self.assertEqual(net, 10000 - fee)


class ChallengePerkLoadoutTests(SimpleTestCase):
    def test_set_equipped_perks_validates(self):
        obj = SimpleNamespace(attributes=_MockAttributes())
        h = ChallengeHandler(obj)
        h._state["ownedPerks"] = ["p1", "p2"]
        h._state["perkSlotTotal"] = 2

        ok, msg = h.set_equipped_perks(["p1", "p2"])
        self.assertTrue(ok)
        self.assertEqual(h.equipped_perk_ids(), ["p1", "p2"])

        ok, msg = h.set_equipped_perks(["p1", "nope"])
        self.assertFalse(ok)
        self.assertIn("not owned", msg.lower())

        ok, msg = h.set_equipped_perks(["p1", "p2", "p1"])
        self.assertFalse(ok)
        self.assertIn("duplicate", msg.lower())

        h._state["perkSlotTotal"] = 1
        ok, msg = h.set_equipped_perks(["p1", "p2"])
        self.assertFalse(ok)
        self.assertIn("too many", msg.lower())
