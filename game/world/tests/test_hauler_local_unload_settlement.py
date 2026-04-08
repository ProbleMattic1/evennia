"""Tests for local raw reserve unload + treasury settlement (haul_delivers_to_local_raw_storage)."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

MIN_PY = (3, 11)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class _FakeInvStore:
    def __init__(self, capacity_tons: float, key: str = "Local"):
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
    key = "Test Local Hauler"

    def __init__(self, cargo=None):
        self.db = SimpleNamespace(
            cargo=dict(cargo or {}),
            hauler_state="unloading",
            hauler_mine_room=None,
            hauler_refinery_room=None,
            hauler_destination_room=None,
            hauler_owner=None,
            cargo_capacity_tons=100.0,
            hauler_upgrades={},
        )
        self.location = None

        class _Tags:
            @staticmethod
            def has(name, category=None):
                return name == "autonomous_hauler" and category == "mining"

        self.tags = _Tags()

    def move_to(self, *args, **kwargs):
        return None

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

    def cargo_total_mass(self):
        c = self.db.cargo or {}
        return round(sum(float(v) for v in c.values()), 2)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class TestHaulerLocalUnloadSettlement(unittest.TestCase):
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

    def test_hauler_process_one_local_unload_calls_settle(self):
        from typeclasses.haulers import hauler_process_one

        mine_room = SimpleNamespace(key="Mine Room", contents=[])
        plant_room = SimpleNamespace(key="Plant Room", contents=[])

        owner = SimpleNamespace(
            key="Payee",
            id=4242,
            db=SimpleNamespace(
                haul_delivers_to_local_raw_storage=True,
                haul_local_reserve_then_plant=False,
                credits=0,
            ),
        )
        hauler = _FakeHauler({"nickel_ore": 8.5})
        hauler.db.hauler_owner = owner
        hauler.db.hauler_mine_room = mine_room
        hauler.db.hauler_refinery_room = plant_room
        hauler.location = plant_room

        local_store = _FakeInvStore(500_000.0, key="Payee Local Raw Reserve")

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local_store):
            with mock.patch(
                "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                return_value=9999,
            ) as settle:
                ok, msg = hauler_process_one(hauler)

        self.assertTrue(ok)
        self.assertIn("paid", msg)
        self.assertIn("9,999", msg)
        self.assertAlmostEqual(local_store.total_mass(), 8.5)
        self.assertEqual(hauler.db.cargo, {})
        settle.assert_called_once()
        kwargs = settle.call_args.kwargs
        args = settle.call_args.args
        self.assertEqual(kwargs.get("raw_pipeline"), "mining")
        delivered = kwargs.get("delivered") or (args[2] if len(args) > 2 else None)
        self.assertIsNotNone(delivered)
        assert delivered is not None
        self.assertAlmostEqual(float(delivered.get("nickel_ore", 0)), 8.5)
        self.assertEqual(settle.call_args.kwargs.get("memo"), f"Plant raw intake ({hauler.key})")

    def test_hauler_process_one_local_unload_treasury_failure_rollbacks(self):
        from typeclasses.haulers import hauler_process_one

        mine_room = SimpleNamespace(key="Mine Room", contents=[])
        plant_room = SimpleNamespace(key="Plant Room", contents=[])

        owner = SimpleNamespace(
            key="Payee",
            id=4243,
            db=SimpleNamespace(
                haul_delivers_to_local_raw_storage=True,
                haul_local_reserve_then_plant=False,
                credits=0,
            ),
        )
        hauler = _FakeHauler({"iron": 4.0})
        hauler.db.hauler_owner = owner
        hauler.db.hauler_mine_room = mine_room
        hauler.db.hauler_refinery_room = plant_room
        hauler.location = plant_room

        local_store = _FakeInvStore(500_000.0)

        with mock.patch("typeclasses.haulers.ensure_local_raw_storage", return_value=local_store):
            with mock.patch(
                "typeclasses.refining.settle_plant_raw_purchase_from_treasury",
                side_effect=ValueError("treasury short"),
            ):
                ok, msg = hauler_process_one(hauler)

        self.assertTrue(ok)
        self.assertIn("treasury could not cover", msg)
        self.assertEqual(local_store.total_mass(), 0.0)
        self.assertAlmostEqual(float(hauler.db.cargo.get("iron", 0)), 4.0)


if __name__ == "__main__":
    unittest.main()
