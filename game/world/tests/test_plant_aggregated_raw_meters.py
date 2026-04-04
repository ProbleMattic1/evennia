"""Tests for plant-wide raw storage meters vs aggregated inventory (web processing payload)."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

MIN_PY = (3, 11)


class _FakeTags:
    def __init__(self, *pairs: tuple[str, str | None]):
        self._pairs = set(pairs)

    def has(self, tag, category=None):
        return (tag, category) in self._pairs


class _FakeIntakeStore:
    def __init__(self, inventory: dict, capacity_tons: float, tag_pairs: tuple):
        self.db = SimpleNamespace(inventory=dict(inventory), capacity_tons=float(capacity_tons))
        self.tags = _FakeTags(*tag_pairs)

    def total_mass(self):
        inv = self.db.inventory or {}
        return round(sum(float(v) for v in inv.values()), 2)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "typeclasses.haulers uses datetime.UTC (Python 3.11+)",
)
class PlantAggregatedRawMetersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_meters_sum_bay_silo_and_local(self):
        from typeclasses.haulers import (
            LOCAL_RAW_STORAGE_CATEGORY,
            LOCAL_RAW_STORAGE_TAG,
            ORE_RECEIVING_BAY_TAG,
            ORE_RECEIVING_BAY_TAG_CATEGORY,
            PLANT_PLAYER_STORAGE_CATEGORY,
            PLANT_PLAYER_STORAGE_TAG,
            plant_aggregated_raw_storage_meters,
        )

        mining = ("mining_storage", "mining")
        bay = _FakeIntakeStore(
            {"iron_ore": 100.0},
            1_000_000.0,
            (mining, (ORE_RECEIVING_BAY_TAG, ORE_RECEIVING_BAY_TAG_CATEGORY)),
        )
        silo = _FakeIntakeStore(
            {"copper_ore": 50.25},
            500.0,
            (mining, (PLANT_PLAYER_STORAGE_TAG, PLANT_PLAYER_STORAGE_CATEGORY)),
        )
        local = _FakeIntakeStore(
            {"nickel_ore": 25.0},
            500_000.0,
            (mining, (LOCAL_RAW_STORAGE_TAG, LOCAL_RAW_STORAGE_CATEGORY)),
        )
        room = SimpleNamespace(contents=[silo, local])

        with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
            used, cap = plant_aggregated_raw_storage_meters(room)

        self.assertEqual(used, 175.25)
        self.assertEqual(cap, 1_000_000.0 + 500.0 + 500_000.0)

    def test_iter_aggregated_inventory_mass_matches_meters_used(self):
        from typeclasses.haulers import iter_plant_aggregated_raw_inventory, plant_aggregated_raw_storage_meters

        mining = ("mining_storage", "mining")
        from typeclasses.haulers import (
            LOCAL_RAW_STORAGE_CATEGORY,
            LOCAL_RAW_STORAGE_TAG,
            ORE_RECEIVING_BAY_TAG,
            ORE_RECEIVING_BAY_TAG_CATEGORY,
            PLANT_PLAYER_STORAGE_CATEGORY,
            PLANT_PLAYER_STORAGE_TAG,
        )

        bay = _FakeIntakeStore(
            {"iron_ore": 10.0, "copper_ore": 5.0},
            100.0,
            (mining, (ORE_RECEIVING_BAY_TAG, ORE_RECEIVING_BAY_TAG_CATEGORY)),
        )
        silo = _FakeIntakeStore(
            {"iron_ore": 3.0},
            200.0,
            (mining, (PLANT_PLAYER_STORAGE_TAG, PLANT_PLAYER_STORAGE_CATEGORY)),
        )
        room = SimpleNamespace(contents=[silo])

        with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
            merged = iter_plant_aggregated_raw_inventory(room)
            used, _ = plant_aggregated_raw_storage_meters(room)

        agg_sum = round(sum(merged.values()), 2)
        self.assertEqual(agg_sum, used)
        self.assertEqual(used, 18.0)
