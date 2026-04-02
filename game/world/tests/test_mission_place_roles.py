"""Tests for mission place role expansion and quest/mission loader merge."""

from django.test import SimpleTestCase

from world.mission_place_roles import expand_place_roles, merge_visit_room_keys
from world.mission_loader import get_mission_template, load_mission_templates
from world.quest_loader import get_quest_template, load_quest_templates


class MissionPlaceRolesTests(SimpleTestCase):
    def test_merge_dock_public_includes_both_venues(self):
        keys = merge_visit_room_keys(explicit_keys=[], role_ids=["dock_public"])
        self.assertIn("Meridian Civil Shipyard", keys)
        self.assertIn("Frontier Meridian Civil Shipyard", keys)

    def test_merge_dock_dispatch_includes_both_venues(self):
        keys = merge_visit_room_keys(explicit_keys=[], role_ids=["dock_dispatch"])
        self.assertIn("NanoMegaPlex Industrial Subdeck", keys)
        self.assertIn("Frontier Industrial Subdeck", keys)

    def test_merge_dedupes_explicit_plus_role(self):
        keys = merge_visit_room_keys(
            explicit_keys=["Meridian Civil Shipyard"],
            role_ids=["dock_public"],
        )
        self.assertEqual(keys.count("Meridian Civil Shipyard"), 1)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            expand_place_roles(["not_a_real_role"])

    def test_main_dock_quest_trigger_expands(self):
        load_quest_templates()
        t = get_quest_template("main_dock_pressure_01")
        self.assertIsNotNone(t)
        rk = (t.get("trigger") or {}).get("roomKeysAny") or []
        self.assertIn("Meridian Civil Shipyard", rk)
        self.assertIn("Frontier Meridian Civil Shipyard", rk)

    def test_main_dock_debrief_objective_expands(self):
        load_quest_templates()
        t = get_quest_template("main_dock_pressure_01")
        self.assertIsNotNone(t)
        debrief = next(
            (o for o in (t.get("objectives") or []) if o.get("id") == "debrief"),
            None,
        )
        self.assertIsNotNone(debrief)
        rk = debrief.get("roomKeysAny") or []
        self.assertIn("NanoMegaPlex Promenade", rk)
        self.assertIn("Frontier Promenade", rk)

    def test_crime_mission_visit_expands(self):
        load_mission_templates()
        t = get_mission_template("crime_customs_anomaly_runner")
        self.assertIsNotNone(t)
        obj = next(
            (o for o in (t.get("objectives") or []) if o.get("id") == "visit_docks"),
            None,
        )
        self.assertIsNotNone(obj)
        rk = obj.get("roomKeysAny") or []
        self.assertIn("Meridian Civil Shipyard", rk)

    def test_battlespace_salvage_uses_dispatch_subdeck(self):
        load_mission_templates()
        t = get_mission_template("bs_salvage_under_fire_assist")
        self.assertIsNotNone(t)
        obj = next(
            (o for o in (t.get("objectives") or []) if o.get("id") == "visit_dock"),
            None,
        )
        self.assertIsNotNone(obj)
        rk = obj.get("roomKeysAny") or []
        self.assertIn("NanoMegaPlex Industrial Subdeck", rk)
        self.assertIn("Frontier Industrial Subdeck", rk)
