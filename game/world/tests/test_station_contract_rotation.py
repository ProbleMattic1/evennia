"""Tests for station contract rotation merge logic."""

from django.test import SimpleTestCase

from world.station_contract_rotation import build_visible_contracts, core_station_contracts, load_rotation_pool


class StationContractRotationTests(SimpleTestCase):
    def test_core_contracts_stable_ids(self):
        core = core_station_contracts()
        ids = {c["id"] for c in core}
        self.assertIn("PKG-001", ids)
        self.assertIn("REF-001", ids)

    def test_build_merges_core_rotation_and_preserves_in_flight(self):
        prev = list(core_station_contracts()) + [
            {
                "id": "ROT-OLD",
                "title": "Old rotating",
                "payout": 99,
                "predicate_key": "refine_collect",
                "venue_id": None,
            }
        ]
        new_list, next_ri = build_visible_contracts(
            rotation_index=0,
            previous_contracts=prev,
            in_flight_ids={"ROT-OLD"},
        )
        ids = [c["id"] for c in new_list]
        self.assertIn("PKG-001", ids)
        self.assertIn("ROT-OLD", ids)
        self.assertEqual(next_ri, 1)

    def test_rotation_pool_loads(self):
        pool = load_rotation_pool()
        self.assertGreaterEqual(len(pool), 1)
        self.assertIn("id", pool[0])
