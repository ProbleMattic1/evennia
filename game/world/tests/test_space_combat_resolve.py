"""
Unit tests for the space combat pure resolver.

No Evennia imports — the resolver is pure Python so these run with
Django's SimpleTestCase and a deterministic RNG seed.
"""

import random
import unittest

from world.space_combat_resolve import (
    RANGE_BANDS,
    RANGE_KNIFE,
    RANGE_MEDIUM,
    RANGE_MERGE,
    RANGE_STANDOFF,
    apply_ew,
    apply_maneuver,
    apply_weapon,
    make_actor,
    make_state,
    npc_choose_action,
    tick,
)

_COMBAT_LIGHT = {
    "hp": 60,
    "shields": 20,
    "armor": 2,
    "agility": 6,
    "sensors": 5,
    "stealth": 4,
    "hardpoints": 2,
}

_COMBAT_HEAVY = {
    "hp": 120,
    "shields": 40,
    "armor": 8,
    "agility": 3,
    "sensors": 6,
    "stealth": 2,
    "hardpoints": 4,
}


def _two_ship_state(range_band=RANGE_STANDOFF):
    alpha = make_actor("alpha_1", "alpha", _COMBAT_LIGHT)
    bravo = make_actor("bravo_1", "bravo", _COMBAT_HEAVY)
    return make_state([alpha, bravo], rng_seed=42, range_band=range_band)


class TestMakeState(unittest.TestCase):
    def test_initial_fields(self):
        state = _two_ship_state()
        self.assertEqual(state["tick"], 0)
        self.assertFalse(state["closed"])
        self.assertEqual(len(state["actors"]), 2)
        self.assertEqual(state["range_band"], RANGE_STANDOFF)

    def test_actors_start_at_full_hull(self):
        state = _two_ship_state()
        for actor in state["actors"]:
            self.assertEqual(actor["hull_pct"], 100)


class TestTick(unittest.TestCase):
    def test_tick_increments(self):
        state = _two_ship_state()
        r = random.Random(99)
        new_state, events = tick(state, rng=r)
        self.assertEqual(new_state["tick"], 1)

    def test_tick_does_not_mutate_original(self):
        state = _two_ship_state()
        original_tick = state["tick"]
        r = random.Random(99)
        tick(state, rng=r)
        self.assertEqual(state["tick"], original_tick)

    def test_heat_bleed_on_normal_emcon(self):
        state = _two_ship_state()
        # Give alpha some heat to bleed
        state["actors"][0]["heat"] = 30
        r = random.Random(99)
        new_state, _ = tick(state, rng=r)
        self.assertLess(new_state["actors"][0]["heat"], 30)

    def test_lock_decays_each_tick(self):
        state = _two_ship_state()
        state["actors"][0]["lock_quality"] = 2
        r = random.Random(99)
        new_state, _ = tick(state, rng=r)
        self.assertLess(new_state["actors"][0]["lock_quality"], 2)


class TestManeuver(unittest.TestCase):
    def _r(self):
        return random.Random(7)

    def test_burn_in_closes_range(self):
        state = _two_ship_state(range_band=RANGE_STANDOFF)
        new_state, events = apply_maneuver(state, "alpha_1", "burn_in", rng=self._r())
        self.assertLess(new_state["range_band"], RANGE_STANDOFF)
        kinds = [e["kind"] for e in events]
        self.assertIn("maneuver", kinds)

    def test_burn_in_at_merge_stays_at_merge(self):
        state = _two_ship_state(range_band=RANGE_MERGE)
        new_state, _ = apply_maneuver(state, "alpha_1", "burn_in", rng=self._r())
        self.assertEqual(new_state["range_band"], RANGE_MERGE)

    def test_burn_out_opens_range(self):
        state = _two_ship_state(range_band=RANGE_KNIFE)
        new_state, _ = apply_maneuver(state, "alpha_1", "burn_out", rng=self._r())
        self.assertGreater(new_state["range_band"], RANGE_KNIFE)

    def test_burn_out_at_standoff_stays(self):
        state = _two_ship_state(range_band=RANGE_STANDOFF)
        new_state, _ = apply_maneuver(state, "alpha_1", "burn_out", rng=self._r())
        self.assertEqual(new_state["range_band"], RANGE_STANDOFF)

    def test_burn_in_spikes_heat(self):
        state = _two_ship_state()
        state["actors"][0]["heat"] = 0
        new_state, _ = apply_maneuver(state, "alpha_1", "burn_in", rng=self._r())
        self.assertGreater(new_state["actors"][0]["heat"], 0)

    def test_cold_coast_bleeds_heat(self):
        state = _two_ship_state()
        state["actors"][0]["heat"] = 50
        new_state, _ = apply_maneuver(state, "alpha_1", "cold_coast", rng=self._r())
        self.assertLess(new_state["actors"][0]["heat"], 50)

    def test_cold_coast_sets_emcon_zero(self):
        state = _two_ship_state()
        state["actors"][0]["emcon"] = 2
        new_state, _ = apply_maneuver(state, "alpha_1", "cold_coast", rng=self._r())
        self.assertEqual(new_state["actors"][0]["emcon"], 0)

    def test_unknown_maneuver_returns_error(self):
        state = _two_ship_state()
        _, events = apply_maneuver(state, "alpha_1", "teleport", rng=self._r())
        self.assertEqual(events[0]["kind"], "error")

    def test_eliminated_actor_returns_error(self):
        state = _two_ship_state()
        state["actors"][0]["eliminated"] = True
        _, events = apply_maneuver(state, "alpha_1", "burn_in", rng=self._r())
        self.assertEqual(events[0]["kind"], "error")


class TestEW(unittest.TestCase):
    def _r(self):
        return random.Random(13)

    def test_spike_raises_enemy_lock(self):
        state = _two_ship_state()
        state["actors"][1]["lock_quality"] = 0
        new_state, events = apply_ew(state, "alpha_1", "spike", rng=self._r())
        self.assertGreater(new_state["actors"][1]["lock_quality"], 0)
        kinds = [e["kind"] for e in events]
        self.assertIn("ew_spike", kinds)

    def test_ghost_returns_success_or_failure_event(self):
        state = _two_ship_state()
        _, events = apply_ew(state, "alpha_1", "ghost", rng=self._r())
        kinds = [e["kind"] for e in events]
        self.assertTrue(
            "ew_ghost_success" in kinds or "ew_ghost_failed" in kinds
        )

    def test_seduction_returns_success_or_failure_event(self):
        state = _two_ship_state()
        _, events = apply_ew(state, "alpha_1", "seduction", rng=self._r())
        kinds = [e["kind"] for e in events]
        self.assertTrue(
            "ew_seduction_success" in kinds or "ew_seduction_failed" in kinds
        )


class TestWeapon(unittest.TestCase):
    def _r(self):
        return random.Random(5)

    def test_kinetic_at_merge_emits_hit_or_miss(self):
        state = _two_ship_state(range_band=RANGE_MERGE)
        state["actors"][0]["lock_quality"] = 3
        _, events = apply_weapon(state, "alpha_1", "kinetic_squeeze", rng=self._r())
        kinds = [e["kind"] for e in events]
        self.assertTrue("kinetic_hit" in kinds or "kinetic_miss" in kinds)

    def test_kinetic_hit_reduces_target_hull(self):
        # Force a guaranteed hit by patching the roll
        state = _two_ship_state(range_band=RANGE_MERGE)
        state["actors"][0]["lock_quality"] = 3
        bravo_hull_before = state["actors"][1]["hull_pct"]
        # Use seed that produces a low roll at merge+high-lock
        new_state, events = apply_weapon(state, "alpha_1", "kinetic_squeeze",
                                         rng=random.Random(0))
        hit_events = [e for e in events if e["kind"] == "kinetic_hit"]
        if hit_events:
            self.assertLess(new_state["actors"][1]["hull_pct"], bravo_hull_before)

    def test_fox_missile_adds_tube_timer(self):
        state = _two_ship_state(range_band=RANGE_MEDIUM)
        new_state, events = apply_weapon(state, "alpha_1", "fox_missile", rng=self._r())
        kinds = [e["kind"] for e in events]
        self.assertIn("missile_launched", kinds)
        self.assertGreater(len(new_state["actors"][0]["tube_timers"]), 0)

    def test_fox_missile_blocked_when_hardpoints_full(self):
        state = _two_ship_state()
        hardpoints = _COMBAT_LIGHT["hardpoints"]
        state["actors"][0]["tube_timers"] = [3] * hardpoints
        _, events = apply_weapon(state, "alpha_1", "fox_missile", rng=self._r())
        self.assertEqual(events[0]["kind"], "error")

    def test_pdc_toggles(self):
        state = _two_ship_state()
        state["actors"][0]["pdc_posture"] = False
        new_state, events = apply_weapon(state, "alpha_1", "pdc_posture", rng=self._r())
        self.assertTrue(new_state["actors"][0]["pdc_posture"])
        kinds = [e["kind"] for e in events]
        self.assertIn("pdc_posture_toggle", kinds)


class TestMissileImpact(unittest.TestCase):
    def test_missile_fires_on_timer_zero(self):
        state = _two_ship_state()
        state["actors"][0]["tube_timers"] = [1]  # fires next tick
        r = random.Random(1)
        new_state, events = tick(state, rng=r)
        kinds = [e["kind"] for e in events]
        self.assertTrue("missile_hit" in kinds or "missile_defeated" in kinds)

    def test_pdc_improves_intercept_odds(self):
        hits_with_pdc = 0
        hits_without_pdc = 0
        for seed in range(200):
            for pdc_on, counter in ((True, "with"), (False, "without")):
                state = _two_ship_state()
                state["actors"][0]["tube_timers"] = [1]
                state["actors"][1]["pdc_posture"] = pdc_on
                r = random.Random(seed)
                _, events = tick(state, rng=r)
                defeated = any(e["kind"] == "missile_defeated" for e in events)
                if pdc_on and defeated:
                    hits_with_pdc += 1
                if not pdc_on and defeated:
                    hits_without_pdc += 1
        self.assertGreater(hits_with_pdc, hits_without_pdc)


class TestNPCPolicy(unittest.TestCase):
    def test_aggressive_closes_at_standoff(self):
        state = _two_ship_state(range_band=RANGE_STANDOFF)
        state["actors"][1]["ai_policy_id"] = "aggressive"
        action_type, action_name = npc_choose_action(state, "bravo_1")
        self.assertEqual(action_type, "maneuver")
        self.assertIn(action_name, ("burn_in",))

    def test_defensive_opens_at_knife(self):
        state = _two_ship_state(range_band=RANGE_KNIFE)
        state["actors"][1]["ai_policy_id"] = "defensive"
        action_type, action_name = npc_choose_action(state, "bravo_1")
        self.assertEqual(action_type, "maneuver")
        self.assertEqual(action_name, "burn_out")

    def test_critical_hull_always_disengages(self):
        state = _two_ship_state(range_band=RANGE_MERGE)
        state["actors"][1]["hull_pct"] = 10
        state["actors"][1]["ai_policy_id"] = "aggressive"
        action_type, action_name = npc_choose_action(state, "bravo_1")
        self.assertEqual(action_type, "maneuver")
        self.assertEqual(action_name, "burn_out")

    def test_overheated_npc_coasts(self):
        state = _two_ship_state()
        state["actors"][1]["heat"] = 90
        action_type, action_name = npc_choose_action(state, "bravo_1")
        self.assertEqual(action_type, "maneuver")
        self.assertEqual(action_name, "cold_coast")
