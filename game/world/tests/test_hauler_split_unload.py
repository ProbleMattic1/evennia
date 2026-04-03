"""Tests for split local / plant autonomous haul unload (haul_local_reserve_then_plant)."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

# typeclasses.haulers uses datetime.UTC (Python 3.11+).
MIN_PY = (3, 11)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class _FakeInvStore:
    def __init__(self, capacity_tons: float, key: str = "FakeStore"):
        self.key = key
        self.db = SimpleNamespace(capacity_tons=capacity_tons, inventory={})

    def total_mass(self):
        inv = self.db.inventory or {}
        return round(sum(float(v) for v in inv.values()), 2)

    def withdraw(self, resource_key, tons):
        inv = dict(self.db.inventory or {})
        available = float(inv.get(resource_key, 0.0))
        removed = min(available, float(tons))
        remaining = round(available - removed, 2)
        if remaining <= 0.0:
            inv.pop(resource_key, None)
        else:
            inv[resource_key] = remaining
        self.db.inventory = inv
        return round(removed, 2)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class _FakeHauler:
    key = "Test Hauler"

    def __init__(self, cargo=None):
        self.db = SimpleNamespace(cargo=dict(cargo or {}), hauler_state="unloading")

    def unload_cargo(self, resource_key, amount):
        cargo = self.db.cargo or {}
        cur = float(cargo.get(resource_key) or 0)
        removed = min(cur, float(amount))
        removed = round(removed, 2)
        new_cur = round(cur - removed, 2)
        if new_cur <= 0:
            cargo.pop(resource_key, None)
        else:
            cargo[resource_key] = new_cur
        self.db.cargo = cargo
        return removed

    def load_cargo(self, resource_key, amount):
        cargo = dict(self.db.cargo or {})
        cargo[resource_key] = round(float(cargo.get(resource_key, 0)) + float(amount), 2)
        self.db.cargo = cargo


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class TestSplitLocalPlantUnload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def setUp(self):
        self._patch_next = mock.patch("typeclasses.haulers.set_hauler_next_cycle")
        self._patch_emit = mock.patch("typeclasses.haulers._emit_hauler_tick_challenge")
        self._patch_next.start()
        self.addCleanup(self._patch_next.stop)
        self._patch_emit.start()
        self.addCleanup(self._patch_emit.stop)

    def test_fills_local_to_threshold_then_bay_parameterized(self):
        from typeclasses.haulers import _haul_unload_split_local_then_plant

        # Threshold = capacity (100) * fraction; single-commodity cargo 60 t.
        cases = [
            (0.1, 10.0, 50.0, True),
            (0.25, 25.0, 35.0, True),
            (0.5, 50.0, 10.0, True),
            (0.75, 60.0, 0.0, False),
            (1.0, 60.0, 0.0, False),
        ]
        for frac, want_local, want_bay, expect_settle in cases:
            with self.subTest(fraction=frac):
                local = _FakeInvStore(100.0, key="Local Raw")
                bay = _FakeInvStore(1000.0, key="Ore Receiving Bay")
                hauler = _FakeHauler({"iron": 60.0})
                owner = SimpleNamespace(
                    key="NPC",
                    db=SimpleNamespace(
                        local_raw_storage=None,
                        haul_local_plant_fill_fraction=frac,
                    ),
                )
                plant = SimpleNamespace(key="Plant")
                mine = SimpleNamespace(key="Mine")

                with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local):
                    with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
                        with mock.patch(
                            "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                            return_value=1234,
                        ) as settle:
                            ok, msg = _haul_unload_split_local_then_plant(
                                hauler, owner, plant, mine, "mining"
                            )

                self.assertTrue(ok)
                self.assertIn("Split unload", msg)
                self.assertAlmostEqual(local.total_mass(), want_local)
                self.assertAlmostEqual(bay.total_mass(), want_bay)
                self.assertEqual(hauler.db.cargo, {})
                if expect_settle:
                    settle.assert_called_once()
                    kwargs = settle.call_args.kwargs
                    args = settle.call_args.args
                    self.assertEqual(kwargs.get("raw_pipeline"), "mining")
                    delivered = kwargs.get("delivered") or (args[2] if len(args) > 2 else None)
                    self.assertIsNotNone(delivered)
                    assert delivered is not None
                    self.assertAlmostEqual(float(delivered.get("iron", 0)), want_bay)
                else:
                    settle.assert_not_called()

    def test_default_fraction_when_override_unset(self):
        from typeclasses.haulers import HAUL_LOCAL_PLANT_FILL_FRACTION, _haul_unload_split_local_then_plant

        local = _FakeInvStore(100.0, key="Local Raw")
        bay = _FakeInvStore(1000.0, key="Ore Receiving Bay")
        hauler = _FakeHauler({"iron": 60.0})
        owner = SimpleNamespace(key="NPC", db=SimpleNamespace(local_raw_storage=None))
        plant = SimpleNamespace(key="Plant")
        mine = SimpleNamespace(key="Mine")

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local):
            with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
                with mock.patch(
                    "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                    return_value=1234,
                ) as settle:
                    ok, msg = _haul_unload_split_local_then_plant(
                        hauler, owner, plant, mine, "mining"
                    )

        self.assertTrue(ok)
        self.assertIn("Split unload", msg)
        want_local = round(100.0 * HAUL_LOCAL_PLANT_FILL_FRACTION, 2)
        self.assertAlmostEqual(local.total_mass(), want_local)
        self.assertAlmostEqual(bay.total_mass(), 10.0)
        settle.assert_called_once()

    def test_invalid_override_falls_back_to_default_half(self):
        from typeclasses.haulers import HAUL_LOCAL_PLANT_FILL_FRACTION, _haul_unload_split_local_then_plant

        local = _FakeInvStore(100.0, key="Local Raw")
        bay = _FakeInvStore(1000.0, key="Bay")
        hauler = _FakeHauler({"iron": 60.0})
        owner = SimpleNamespace(
            key="NPC",
            db=SimpleNamespace(
                local_raw_storage=None,
                haul_local_plant_fill_fraction=0.33,
            ),
        )
        plant = SimpleNamespace(key="Plant")
        mine = SimpleNamespace(key="Mine")

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local):
            with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
                with mock.patch(
                    "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                    return_value=1,
                ):
                    ok, _msg = _haul_unload_split_local_then_plant(
                        hauler, owner, plant, mine, "mining"
                    )

        self.assertTrue(ok)
        want_local = round(100.0 * HAUL_LOCAL_PLANT_FILL_FRACTION, 2)
        self.assertAlmostEqual(local.total_mass(), want_local)
        self.assertAlmostEqual(bay.total_mass(), 10.0)

    def test_local_already_at_threshold_all_to_bay(self):
        from typeclasses.haulers import _haul_unload_split_local_then_plant

        local = _FakeInvStore(100.0)
        local.db.inventory = {"iron": 50.0}
        bay = _FakeInvStore(1000.0, key="Bay")
        hauler = _FakeHauler({"copper": 20.0})
        owner = SimpleNamespace(key="NPC", db=SimpleNamespace(local_raw_storage=None))
        plant = SimpleNamespace(key="Plant")
        mine = SimpleNamespace(key="Mine")

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local):
            with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
                with mock.patch(
                    "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                    return_value=500,
                ):
                    ok, _msg = _haul_unload_split_local_then_plant(
                        hauler, owner, plant, mine, "mining"
                    )

        self.assertTrue(ok)
        self.assertAlmostEqual(local.total_mass(), 50.0)
        self.assertAlmostEqual(bay.total_mass(), 20.0)
        self.assertEqual(hauler.db.cargo, {})

    def test_settlement_failure_rollbacks_local_and_bay(self):
        from typeclasses.haulers import _haul_unload_split_local_then_plant

        local = _FakeInvStore(100.0)
        bay = _FakeInvStore(1000.0, key="Bay")
        hauler = _FakeHauler({"iron": 60.0})
        owner = SimpleNamespace(key="NPC", db=SimpleNamespace(local_raw_storage=None))
        plant = SimpleNamespace(key="Plant")
        mine = SimpleNamespace(key="Mine")

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local):
            with mock.patch("typeclasses.haulers.get_plant_ore_receiving_bay", return_value=bay):
                with mock.patch(
                    "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                    side_effect=ValueError("treasury"),
                ):
                    ok, msg = _haul_unload_split_local_then_plant(
                        hauler, owner, plant, mine, "mining"
                    )

        self.assertTrue(ok)
        self.assertIn("treasury could not cover", msg)
        self.assertEqual(local.total_mass(), 0.0)
        self.assertEqual(bay.total_mass(), 0.0)
        self.assertAlmostEqual(float(hauler.db.cargo.get("iron", 0)), 60.0)


if __name__ == "__main__":
    unittest.main()
