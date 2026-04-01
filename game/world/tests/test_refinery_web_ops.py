"""Tests for ``world.refinery_web_ops.feed_recipe_batch_to_miner_queue`` (mocked room/silo/refinery)."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from world.refinery_web_ops import feed_recipe_batch_to_miner_queue


class FeedRecipeBatchToMinerQueueTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.mock_room = SimpleNamespace()
        self.mock_ref = SimpleNamespace()
        self.mock_ref.db = SimpleNamespace(miner_ore_queue={})
        self.mock_ref.key = "test-refinery"
        self.mock_silo = SimpleNamespace()
        self.mock_silo.db = SimpleNamespace(inventory={})
        self.char = SimpleNamespace(id=99, key="tester")

    def _patch_deps(self):
        return patch.multiple(
            "world.refinery_web_ops",
            resolve_refinery_web_context=lambda *a, **k: (self.mock_room, self.mock_room, None),
            _main_refinery=lambda room: self.mock_ref,
            get_plant_player_storage=lambda room, char: self.mock_silo,
        )

    def test_single_input_success(self):
        self.mock_silo.db.inventory = {"iron_ore": 4.0}
        with self._patch_deps():
            ok, msg = feed_recipe_batch_to_miner_queue(self.char, "nanomega_core", "refined_iron")
        self.assertTrue(ok)
        self.assertIn("Refined Iron", msg)
        self.assertEqual(self.mock_silo.db.inventory, {})
        q = self.mock_ref.db.miner_ore_queue["99"]
        self.assertEqual(q["iron_ore"], 4.0)

    def test_single_input_insufficient(self):
        self.mock_silo.db.inventory = {"iron_ore": 3.0}
        with self._patch_deps():
            ok, msg = feed_recipe_batch_to_miner_queue(self.char, "nanomega_core", "refined_iron")
        self.assertFalse(ok)
        self.assertIn("Not enough", msg)
        self.assertEqual(self.mock_silo.db.inventory, {"iron_ore": 3.0})
        self.assertEqual(self.mock_ref.db.miner_ore_queue, {})

    def test_multi_input_success(self):
        self.mock_silo.db.inventory = {"iron_ore": 3.0, "lead_zinc_ore": 1.0}
        with self._patch_deps():
            ok, msg = feed_recipe_batch_to_miner_queue(self.char, "nanomega_core", "steel_alloy")
        self.assertTrue(ok)
        self.assertIn("Steel Alloy", msg)
        self.assertEqual(self.mock_silo.db.inventory, {})
        q = self.mock_ref.db.miner_ore_queue["99"]
        self.assertEqual(q["iron_ore"], 3.0)
        self.assertEqual(q["lead_zinc_ore"], 1.0)

    def test_unknown_recipe(self):
        self.mock_silo.db.inventory = {"iron_ore": 99.0}
        with self._patch_deps():
            ok, msg = feed_recipe_batch_to_miner_queue(self.char, "nanomega_core", "not_a_real_recipe_key")
        self.assertFalse(ok)
        self.assertEqual(msg, "Unknown recipe.")
