"""Faction standing handler + pricing curve."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from typeclasses.faction_standing import FactionStandingHandler
from world.factions_loader import buy_price_multiplier_for_standing, clear_factions_cache


class FactionStandingTests(SimpleTestCase):
    def tearDown(self):
        clear_factions_cache()
        super().tearDown()

    def test_buy_mult_interpolates(self):
        m = buy_price_multiplier_for_standing("civilian", -200)
        self.assertGreater(m, 1.0)
        m2 = buy_price_multiplier_for_standing("civilian", 200)
        self.assertLess(m2, m)

    def test_handler_clamps_standing(self):
        char = MagicMock()
        char.key = "Tester"
        char.attributes = MagicMock()

        stored = {}

        def _get(key, category=None, default=None):
            return stored.get((key, category), default)

        def _add(key, val, category=None):
            stored[(key, category)] = val

        char.attributes.get.side_effect = _get
        char.attributes.add.side_effect = _add

        h = FactionStandingHandler(char)
        h.set_standing("civilian", 9999)
        self.assertEqual(h.get_standing("civilian"), 200)
