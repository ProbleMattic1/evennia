"""Product catalog validation and part inventory / fabrication helpers."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestProductCatalogValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_validate_product_catalog_passes(self):
        from world.product_catalog_validate import validate_product_catalog

        validate_product_catalog()


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestPartInventoryAndFabrication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def setUp(self):
        self.char = SimpleNamespace(db=SimpleNamespace())

    def test_add_consume_round_trip(self):
        from world.part_inventory import add_part_units, consume_part_units_batch, get_part_inventory

        add_part_units(self.char, "refined_iron", 3.0)
        add_part_units(self.char, "refined_copper", 1.25)
        inv = get_part_inventory(self.char)
        self.assertEqual(inv["refined_iron"], 3.0)
        self.assertEqual(inv["refined_copper"], 1.25)
        ok = consume_part_units_batch(
            self.char, {"refined_iron": 1.0, "refined_copper": 1.25}
        )
        self.assertTrue(ok)
        inv2 = get_part_inventory(self.char)
        self.assertEqual(inv2.get("refined_iron"), 2.0)
        self.assertNotIn("refined_copper", inv2)

    def test_consume_insufficient(self):
        from world.part_inventory import add_part_units, consume_part_units_batch, get_part_inventory

        add_part_units(self.char, "refined_iron", 0.5)
        ok = consume_part_units_batch(self.char, {"refined_iron": 1.0})
        self.assertFalse(ok)
        self.assertEqual(get_part_inventory(self.char).get("refined_iron"), 0.5)

    def test_withdraw_refinery_to_part_hold(self):
        from world.part_inventory import get_part_inventory
        from world.part_withdraw import withdraw_attributed_refinery_parts

        char = SimpleNamespace(id=42, db=SimpleNamespace())
        ref = SimpleNamespace(
            key="TestRefinery",
            db=SimpleNamespace(miner_output={"42": {"refined_iron": 3.5, "refined_copper": 1.0}}),
        )
        ok, msg = withdraw_attributed_refinery_parts(
            ref, char, withdraw_all=False, amounts={"refined_iron": 2.0}
        )
        self.assertTrue(ok)
        inv = get_part_inventory(char)
        self.assertEqual(inv.get("refined_iron"), 2.0)
        self.assertEqual(inv.get("refined_copper"), None)
        mo = ref.db.miner_output["42"]
        self.assertEqual(mo.get("refined_iron"), 1.5)
        self.assertEqual(mo.get("refined_copper"), 1.0)

    def test_fabricate_consumes_and_spawns(self):
        from world.part_inventory import add_part_units, get_part_inventory
        from world.product_catalog import FABRICATION_RECIPES
        from typeclasses.fabricator import fabricate_for_character

        add_part_units(self.char, "refined_iron", 2.0)
        add_part_units(self.char, "refined_copper", 2.0)
        rid = "fab.supply_multitool_v1"
        self.assertIn(rid, FABRICATION_RECIPES)

        with mock.patch("world.product_spawn.create_object") as co:
            fake_obj = SimpleNamespace(
                db=SimpleNamespace(),
                tags=SimpleNamespace(add=lambda *a, **k: None),
                locks=SimpleNamespace(add=lambda *a, **k: None),
            )
            co.return_value = fake_obj
            n, msg = fabricate_for_character(self.char, rid, batches=1)
            self.assertEqual(n, 1)
            self.assertIn("Supply Multitool", msg)
            inv = get_part_inventory(self.char)
            self.assertEqual(inv.get("refined_iron"), 1.0)
            self.assertEqual(inv.get("refined_copper"), 1.0)
