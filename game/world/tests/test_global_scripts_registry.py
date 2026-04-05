"""Settings: GLOBAL_SCRIPTS lists all singleton world engines."""

from importlib import import_module

from django.conf import settings
from django.test import SimpleTestCase


def _resolved_global_scripts():
    """
    Prefer active Django settings; fall back to importing ``server.conf.settings``
    so ``evennia test`` without ``--settings settings.py`` still validates keys.
    """
    gs = getattr(settings, "GLOBAL_SCRIPTS", None) or {}
    if gs:
        return gs
    return import_module("server.conf.settings").GLOBAL_SCRIPTS


_EXPECTED_KEYS = (
    "global_economy",
    "commodity_demand",
    "manufacturing_engine",
    "economy_world_telemetry",
    "economy_automation_controller",
    "mining_engine",
    "flora_engine",
    "fauna_engine",
    "hauler_engine",
    "refinery_engine",
    "site_discovery_engine",
    "flora_site_discovery_engine",
    "fauna_site_discovery_engine",
    "claims_market_snapshot",
    "npc_miner_registry",
    "property_operation_registry",
    "property_operations_engine",
    "property_events_engine",
    "property_lot_discovery_engine",
    "ambient_world_engine",
    "crime_world_engine",
    "battlespace_world_engine",
    "mission_seeds",
    "system_alerts",
    "station_contracts",
    "world_clock_script",
    "world_environment_engine",
    "instance_manager",
    "party_registry",
)


class GlobalScriptsRegistryTests(SimpleTestCase):
    def test_all_singleton_keys_registered(self):
        gs = _resolved_global_scripts()
        self.assertIsInstance(gs, dict)
        for key in _EXPECTED_KEYS:
            self.assertIn(key, gs, msg=f"missing GLOBAL_SCRIPTS[{key!r}]")
            entry = gs[key]
            self.assertIn("typeclass", entry)
            self.assertIsInstance(entry["typeclass"], str)
            self.assertTrue(entry.get("persistent", True))
