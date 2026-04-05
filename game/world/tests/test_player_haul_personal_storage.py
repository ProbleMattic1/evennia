"""Tests for player autonomous haul → local raw reserve (Personal Storage)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from typeclasses.packages import _mining_deploy_dest_note
from world.player_haul_personal_storage import (
    player_autonomous_haul_uses_local_raw_reserve,
    prime_local_raw_storage_for_plant,
)


class TestPlayerAutonomousHaulUsesLocalRawReserve(unittest.TestCase):
    def test_npc_no_op(self):
        db = SimpleNamespace(is_npc=True)
        ch = SimpleNamespace(db=db)
        self.assertFalse(player_autonomous_haul_uses_local_raw_reserve(ch))
        self.assertFalse(hasattr(db, "haul_delivers_to_local_raw_storage"))

    def test_player_sets_flag(self):
        db = SimpleNamespace(is_npc=False)
        ch = SimpleNamespace(db=db)
        self.assertTrue(player_autonomous_haul_uses_local_raw_reserve(ch))
        self.assertTrue(db.haul_delivers_to_local_raw_storage)


class TestPrimeLocalRawStorageForPlant(unittest.TestCase):
    @mock.patch("typeclasses.haulers.ensure_local_raw_storage")
    def test_primes_when_no_prior_destination(self, ensure_mock):
        plant = SimpleNamespace(key="PlantRoom")
        reserve = SimpleNamespace(key="Reserve")
        ensure_mock.return_value = reserve
        db = SimpleNamespace(is_npc=False)
        ch = SimpleNamespace(db=db)
        prime_local_raw_storage_for_plant(ch, plant)
        ensure_mock.assert_called_once_with(plant, ch)
        self.assertIs(db.local_raw_storage, reserve)
        self.assertIs(db.haul_destination_room, plant)

    @mock.patch("typeclasses.haulers.ensure_local_raw_storage")
    def test_skips_storage_when_destination_differs_from_plant(self, ensure_mock):
        annex = SimpleNamespace(key="Annex")
        plant = SimpleNamespace(key="PlantRoom")
        db = SimpleNamespace(is_npc=False, haul_destination_room=annex)
        ch = SimpleNamespace(db=db)
        with mock.patch("typeclasses.haulers.resolve_room", return_value=annex):
            prime_local_raw_storage_for_plant(ch, plant)
        ensure_mock.assert_not_called()


class TestMiningDeployDestNote(unittest.TestCase):
    def test_local_delivery_message_uses_refinery_when_no_hdr(self):
        buyer = SimpleNamespace(
            db=SimpleNamespace(
                haul_delivers_to_local_raw_storage=True,
                haul_local_reserve_then_plant=False,
                haul_destination_room=None,
            )
        )
        ref = SimpleNamespace(key="Ore Plant")
        msg = _mining_deploy_dest_note(buyer, ref)
        self.assertIn("local raw reserve", msg)
        self.assertIn("Ore Plant", msg)
        self.assertNotIn("Receiving Bay", msg)

    def test_bay_message_when_not_local(self):
        buyer = SimpleNamespace(
            db=SimpleNamespace(
                haul_delivers_to_local_raw_storage=False,
                haul_local_reserve_then_plant=False,
                haul_destination_room=None,
            )
        )
        ref = SimpleNamespace(key="Ore Plant")
        msg = _mining_deploy_dest_note(buyer, ref)
        self.assertIn("Ore Receiving Bay", msg)
        self.assertIn("paid on delivery", msg)
