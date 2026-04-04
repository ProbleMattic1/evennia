"""Tests for backlog-driven autonomous hauler next-run scheduling."""

import sys
import unittest
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from types import SimpleNamespace
from unittest import mock

MIN_PY = (3, 11)


@unittest.skipUnless(
    sys.version_info >= MIN_PY,
    "datetime.UTC in typeclasses.haulers requires Python 3.11+",
)
class HaulerDynamicScheduleTests(unittest.TestCase):
    def _owner(self):
        return SimpleNamespace(key="TestOwner")

    def _storage(self, tons: float):
        st = SimpleNamespace()
        st.total_mass = lambda: float(tons)
        return st

    def _site(self, owner, *, next_cycle_at: datetime, last_dep: datetime | None, storage_tons: float):
        last_ore = last_dep.isoformat() if last_dep else None
        return SimpleNamespace(
            key="TestSite",
            db=SimpleNamespace(
                owner=owner,
                next_cycle_at=next_cycle_at.isoformat(),
                last_ore_deposit_at=last_ore,
                linked_storage=self._storage(storage_tons),
            ),
        )

    def _hauler(self, owner, *, state: str, cargo_mass: float, storage_tons: float = 0.0):
        h = SimpleNamespace(
            key="Hauler",
            db=SimpleNamespace(
                hauler_owner=owner,
                hauler_state=state,
                hauler_mine_room=None,
            ),
        )

        def cargo_total_mass():
            return float(cargo_mass)

        h.cargo_total_mass = cargo_total_mass
        return h, self._site(
            owner,
            next_cycle_at=datetime(2030, 1, 1, 13, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=storage_tons,
        )

    def test_clean_idle_at_mine_uses_grid_when_next_slot_future(self):
        from typeclasses.haulers import compute_next_hauler_run_at

        owner = self._owner()
        next_c = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        after = datetime(2030, 1, 1, 11, 0, 0, tzinfo=UTC)
        site = self._site(owner, next_cycle_at=next_c, last_dep=None, storage_tons=0.0)
        hauler, _ = self._hauler(owner, state="at_mine", cargo_mass=0.0, storage_tons=0.0)

        grid_ret = (site, 1800, 900, "last_ore_deposit_at")

        with mock.patch("typeclasses.haulers._hauler_grid_params", return_value=grid_ret):
            got = compute_next_hauler_run_at(hauler, after=after)
        self.assertEqual(got, next_c)

    def test_backlog_at_mine_returns_reference_time(self):
        from typeclasses.haulers import compute_next_hauler_run_at

        owner = self._owner()
        after = datetime(2030, 2, 1, 15, 30, 0, tzinfo=UTC)
        site = self._site(
            owner,
            next_cycle_at=datetime(2030, 2, 2, 0, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=50.0,
        )
        hauler, _ = self._hauler(owner, state="at_mine", cargo_mass=0.0, storage_tons=50.0)
        with mock.patch("typeclasses.haulers._hauler_grid_params", return_value=(site, 1800, 900, "last_ore_deposit_at")):
            got = compute_next_hauler_run_at(hauler, after=after)
        self.assertEqual(got, after)

    def test_mid_route_returns_reference_time(self):
        from typeclasses.haulers import compute_next_hauler_run_at

        owner = self._owner()
        after = datetime(2030, 3, 1, 8, 0, 0, tzinfo=UTC)
        site = self._site(
            owner,
            next_cycle_at=datetime(2030, 3, 1, 9, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=0.0,
        )
        hauler, _ = self._hauler(owner, state="transit_refinery", cargo_mass=40.0, storage_tons=0.0)
        with mock.patch("typeclasses.haulers._hauler_grid_params", return_value=(site, 1800, 900, "last_ore_deposit_at")):
            got = compute_next_hauler_run_at(hauler, after=after)
        self.assertEqual(got, after)

    def test_at_mine_with_cargo_returns_reference_time(self):
        from typeclasses.haulers import compute_next_hauler_run_at

        owner = self._owner()
        after = datetime(2030, 4, 1, 12, 0, 0, tzinfo=UTC)
        site = self._site(
            owner,
            next_cycle_at=datetime(2030, 4, 2, 0, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=0.0,
        )
        hauler, _ = self._hauler(owner, state="at_mine", cargo_mass=0.01, storage_tons=0.0)
        with mock.patch("typeclasses.haulers._hauler_grid_params", return_value=(site, 1800, 900, "last_ore_deposit_at")):
            got = compute_next_hauler_run_at(hauler, after=after)
        self.assertEqual(got, after)

    def test_hauler_is_clean_idle_at_mine_helper(self):
        from typeclasses.haulers import _hauler_is_clean_idle_at_mine

        owner = self._owner()
        site = self._site(
            owner,
            next_cycle_at=datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=0.0,
        )
        hauler, _ = self._hauler(owner, state="at_mine", cargo_mass=0.0, storage_tons=0.0)
        self.assertTrue(_hauler_is_clean_idle_at_mine(hauler, site))

        site2 = self._site(
            owner,
            next_cycle_at=datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC),
            last_dep=None,
            storage_tons=1.0,
        )
        self.assertFalse(_hauler_is_clean_idle_at_mine(hauler, site2))

    def test_grid_from_deposit_future_pickup(self):
        from typeclasses.haulers import compute_next_hauler_run_at

        owner = self._owner()
        last_dep = datetime(2030, 5, 1, 10, 0, 0, tzinfo=UTC)
        after = datetime(2030, 5, 1, 10, 10, 0, tzinfo=UTC)
        expected_pickup = last_dep + timedelta(seconds=900)
        site = self._site(
            owner,
            next_cycle_at=datetime(2030, 5, 1, 11, 0, 0, tzinfo=UTC),
            last_dep=last_dep,
            storage_tons=0.0,
        )
        hauler, _ = self._hauler(owner, state="at_mine", cargo_mass=0.0, storage_tons=0.0)
        with mock.patch("typeclasses.haulers._hauler_grid_params", return_value=(site, 1800, 900, "last_ore_deposit_at")):
            got = compute_next_hauler_run_at(hauler, after=after)
        self.assertEqual(got, expected_pickup)


if __name__ == "__main__":
    unittest.main()
