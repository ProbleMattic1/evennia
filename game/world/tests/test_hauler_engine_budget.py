"""Tests for HaulerEngine wall-clock budget (reactor fairness)."""

import os
import sys
import time
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

MIN_PY = (3, 11)
UTC = timezone.utc


class _FakeTags:
    def has(self, tag, category=None):
        return True


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class HaulerEngineBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_at_repeat_respects_wall_budget(self):
        from evennia.objects.models import ObjectDB

        from typeclasses.haulers import HaulerEngine

        past = datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC)
        owner = SimpleNamespace(sessions=SimpleNamespace(count=lambda: 0))
        hauler = SimpleNamespace(
            key="BudgetHauler",
            id=42,
            db=SimpleNamespace(
                is_vehicle=True,
                hauler_owner=owner,
            ),
            tags=_FakeTags(),
        )

        def slow_process_one(*_a, **_kw):
            time.sleep(0.06)
            return True, "step"

        engine = HaulerEngine.__new__(HaulerEngine)
        engine.ndb = SimpleNamespace()

        with mock.patch(
            "typeclasses.haulers.HAULER_ENGINE_MAX_WALL_SEC",
            0.12,
        ), mock.patch(
            "typeclasses.haulers.HAULER_MAX_PIPELINE_STEPS",
            50,
        ), mock.patch(
            "world.hauler_dispatch.fetch_due_hauler_ids",
            return_value=[42],
        ), mock.patch.object(
            ObjectDB.objects,
            "get",
            return_value=hauler,
        ), mock.patch(
            "typeclasses.haulers.get_hauler_next_cycle_at",
            return_value=past,
        ), mock.patch(
            "typeclasses.haulers.set_hauler_next_cycle",
        ), mock.patch(
            "typeclasses.haulers.hauler_process_one",
            side_effect=slow_process_one,
        ):
            HaulerEngine.at_repeat(engine)

        self.assertTrue(getattr(engine.ndb, "last_tick_budget_hit", False))
        self.assertGreater(getattr(engine.ndb, "last_tick_deferred_approx", 0), 0)
        wall = float(getattr(engine.ndb, "last_tick_duration_sec", 99))
        self.assertLess(wall, 0.35)
        # At least one slow step ran before budget cut the tick short.
        self.assertGreaterEqual(wall, 0.05)

    def test_at_repeat_completes_small_queue_under_budget(self):
        from evennia.objects.models import ObjectDB

        from typeclasses.haulers import HaulerEngine

        past = datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC)
        owner = SimpleNamespace(sessions=SimpleNamespace(count=lambda: 0))
        hauler = SimpleNamespace(
            key="FastHauler",
            id=7,
            db=SimpleNamespace(is_vehicle=True, hauler_owner=owner),
            tags=_FakeTags(),
        )

        calls = {"n": 0}

        def one_step_then_stop(h, **_kw):
            calls["n"] += 1
            return False, "done"

        engine = HaulerEngine.__new__(HaulerEngine)
        engine.ndb = SimpleNamespace()

        with mock.patch(
            "typeclasses.haulers.HAULER_ENGINE_MAX_WALL_SEC",
            2.0,
        ), mock.patch(
            "world.hauler_dispatch.fetch_due_hauler_ids",
            return_value=[7],
        ), mock.patch.object(
            ObjectDB.objects,
            "get",
            return_value=hauler,
        ), mock.patch(
            "typeclasses.haulers.get_hauler_next_cycle_at",
            return_value=past,
        ), mock.patch(
            "typeclasses.haulers.set_hauler_next_cycle",
        ), mock.patch(
            "typeclasses.haulers.hauler_process_one",
            side_effect=one_step_then_stop,
        ):
            HaulerEngine.at_repeat(engine)

        self.assertFalse(getattr(engine.ndb, "last_tick_budget_hit", True))
        self.assertEqual(getattr(engine.ndb, "last_tick_deferred_approx", -1), 0)
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
