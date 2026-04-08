"""Integration tests for mining_scanner_ops (shared web + telnet)."""

import os
import sys
import unittest

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningScannerOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_deploy_and_undeploy_by_object_id(self):
        from evennia import create_object

        from typeclasses.claim_utils import generate_mining_site
        from world.mining_scanner_ops import attempt_deploy_scanner, attempt_undeploy_scanner

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        char = create_object(
            "typeclasses.characters.Character",
            key="TestScannerOpsChar",
            location=room,
        )
        scanner = create_object(
            "typeclasses.mining_scanner.MiningScanner",
            key="TestScannerOpsObj",
            location=char,
        )
        try:
            ok, msg = attempt_deploy_scanner(char, scanner_object_id=scanner.id)
            self.assertTrue(ok, msg)
            self.assertTrue(getattr(scanner.db, "is_deployed", False))
            ok2, msg2 = attempt_undeploy_scanner(char, scanner_object_id=scanner.id)
            self.assertTrue(ok2, msg2)
            self.assertFalse(getattr(scanner.db, "is_deployed", False))
        finally:
            scanner.delete()
            char.delete()
            site.delete()
            if room:
                room.delete()

    def test_district_scan_cooldown_second_call(self):
        from evennia import create_object

        from typeclasses.claim_utils import generate_mining_site
        from world.mining_scanner_ops import attempt_deploy_scanner, attempt_district_scan

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        char = create_object(
            "typeclasses.characters.Character",
            key="TestDistrictCooldownChar",
            location=room,
        )
        scanner = create_object(
            "typeclasses.mining_scanner.MiningScanner",
            key="TestDistrictCooldownScan",
            location=char,
        )
        try:
            ok, msg = attempt_deploy_scanner(char, scanner_object_id=scanner.id)
            self.assertTrue(ok, msg)
            ok1, err1, peers1, dk1 = attempt_district_scan(char)
            self.assertTrue(ok1, err1)
            ok2, err2, peers2, dk2 = attempt_district_scan(char)
            self.assertFalse(ok2)
            self.assertIsNotNone(err2)
            self.assertIn("recharging", (err2 or "").lower())
            self.assertEqual(peers2, [])
            self.assertEqual(dk2, "")
        finally:
            scanner.delete()
            char.delete()
            site.delete()
            if room:
                room.delete()

    def test_district_scan_lists_adjacent_purchasable_deposit(self):
        """Peers are one exit away, same venue, buyable now (NPC primary + balance)."""
        from evennia import create_object

        from typeclasses.economy import get_economy
        from world.mining_scanner_ops import attempt_deploy_scanner, attempt_district_scan
        from world.venues import apply_venue_metadata

        room_a = create_object("typeclasses.rooms.Room", key="TestAdjScanRoomA")
        room_b = create_object("typeclasses.rooms.Room", key="TestAdjScanRoomB")
        apply_venue_metadata(room_a, "nanomega_core")
        apply_venue_metadata(room_b, "nanomega_core")
        exit_ab = create_object(
            "typeclasses.exits.Exit",
            key="east",
            aliases=["e"],
            location=room_a,
            destination=room_b,
        )
        site_a = create_object(
            "typeclasses.mining.MiningSite",
            key="Test Adj Scan Deposit A",
            location=room_a,
            home=room_a,
        )
        site_b = create_object(
            "typeclasses.mining.MiningSite",
            key="Test Adj Scan Deposit B",
            location=room_b,
            home=room_b,
        )
        char = create_object(
            "typeclasses.characters.Character",
            key="TestAdjScanChar",
            location=room_a,
        )
        scanner = create_object(
            "typeclasses.mining_scanner.MiningScanner",
            key="TestAdjScanScanner",
            location=char,
        )
        econ = get_economy(create_missing=True)
        acct = econ.get_character_account(char)
        econ.ensure_account(acct, opening_balance=2_000_000)
        char.db.credits = econ.get_balance(acct)

        try:
            ok, msg = attempt_deploy_scanner(char, scanner_object_id=scanner.id)
            self.assertTrue(ok, msg)
            ok_scan, err, peers, anchor = attempt_district_scan(char)
            self.assertTrue(ok_scan, err)
            self.assertEqual(anchor, room_a.key)
            self.assertEqual(len(peers), 1)
            row = peers[0]
            self.assertEqual(row["siteKey"], site_b.key)
            self.assertEqual(row["roomKey"], room_b.key)
            self.assertEqual(row["purchaseKind"], "npc_primary")
            self.assertIsInstance(row.get("listingPriceCr"), int)
            self.assertGreater(row["listingPriceCr"], 0)
        finally:
            scanner.delete()
            char.delete()
            site_a.delete()
            site_b.delete()
            exit_ab.delete()
            room_a.delete()
            room_b.delete()

    def test_deploy_by_name_fragment_telnet_path(self):
        from evennia import create_object

        from typeclasses.claim_utils import generate_mining_site
        from world.mining_scanner_ops import attempt_deploy_scanner

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        char = create_object(
            "typeclasses.characters.Character",
            key="TestFragDeployChar",
            location=room,
        )
        scanner = create_object(
            "typeclasses.mining_scanner.MiningScanner",
            key="UniqueFragScannerXYZ",
            location=char,
        )
        try:
            ok, msg = attempt_deploy_scanner(char, name_fragment="FragScanner")
            self.assertTrue(ok, msg)
            self.assertTrue(getattr(scanner.db, "is_deployed", False))
        finally:
            scanner.delete()
            char.delete()
            site.delete()
            if room:
                room.delete()
