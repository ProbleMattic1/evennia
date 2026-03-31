"""Unit tests for Ore Receiving Bay JSON serializer (web UI read model)."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from typeclasses.refining import iter_plant_raw_resource_keys
from web.ui.ore_receiving_bay_serialize import (
    serialize_ore_receiving_bay_rows,
    serialize_plant_intake_snapshot_rows,
)


class OreReceivingBaySerializeTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            patch("typeclasses.mining.get_commodity_bid", return_value=100),
            patch("typeclasses.flora.get_flora_commodity_bid", return_value=1),
            patch("typeclasses.fauna.get_fauna_commodity_bid", return_value=1),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_dense_row_count_matches_catalog_when_bay_missing(self):
        expected = len(frozenset(iter_plant_raw_resource_keys()))
        rows = serialize_ore_receiving_bay_rows(None, None)
        self.assertEqual(len(rows), expected)

    def test_iron_ore_tons_from_inventory(self):
        bay = SimpleNamespace(db=SimpleNamespace(inventory={"iron_ore": 10.0}))
        rows = serialize_ore_receiving_bay_rows(bay, None)
        iron = next(r for r in rows if r["key"] == "iron_ore")
        self.assertEqual(iron["tons"], 10.0)
        self.assertEqual(iron["displayName"], "Iron Ore")
        self.assertEqual(iron["estimatedValueCr"], 1000)
        self.assertEqual(iron["rawPipeline"], "mining")

    def test_flora_key_raw_pipeline(self):
        bay = SimpleNamespace(db=SimpleNamespace(inventory={"algal_mat": 3.0}))
        rows = serialize_ore_receiving_bay_rows(bay, None)
        row = next(r for r in rows if r["key"] == "algal_mat")
        self.assertEqual(row["tons"], 3.0)
        self.assertEqual(row["rawPipeline"], "flora")

    def test_fauna_key_raw_pipeline(self):
        bay = SimpleNamespace(db=SimpleNamespace(inventory={"pelagic_protein_slurry": 2.0}))
        rows = serialize_ore_receiving_bay_rows(bay, None)
        row = next(r for r in rows if r["key"] == "pelagic_protein_slurry")
        self.assertEqual(row["tons"], 2.0)
        self.assertEqual(row["rawPipeline"], "fauna")

    def test_unknown_inventory_key_appended(self):
        bay = SimpleNamespace(db=SimpleNamespace(inventory={"not_in_catalog_test_key": 4.5}))
        rows = serialize_ore_receiving_bay_rows(bay, None)
        extra = [r for r in rows if r["key"] == "not_in_catalog_test_key"]
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra[0]["tons"], 4.5)
        self.assertEqual(extra[0]["displayName"], "not_in_catalog_test_key")
        self.assertEqual(extra[0]["estimatedValueCr"], 0)
        self.assertEqual(extra[0]["rawPipeline"], "unknown")

    def test_plant_intake_snapshot_uses_aggregated_inventory(self):
        with patch(
            "typeclasses.haulers.iter_plant_aggregated_raw_inventory",
            return_value={"iron_ore": 12.25},
        ) as agg:
            rows = serialize_plant_intake_snapshot_rows(None)
        agg.assert_called_once_with(None)
        iron = next(r for r in rows if r["key"] == "iron_ore")
        self.assertEqual(iron["tons"], 12.25)
        self.assertEqual(iron["estimatedValueCr"], 1225)
