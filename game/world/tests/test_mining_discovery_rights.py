"""Mining deposit discovery: survey registration, primary deed exclusivity, discoverer listings."""

import os
import sys
import unittest

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningDiscoveryRights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_generate_mining_site_sets_discovery_pending(self):
        from typeclasses.claim_utils import generate_mining_site

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        try:
            self.assertTrue(getattr(site.db, "discovery_pending", False))
            self.assertIsNone(getattr(site.db, "discovered_by", None))
        finally:
            room = site.location
            site.delete()
            if room:
                room.delete()

    def test_pending_site_not_claims_market_listable(self):
        from typeclasses.claim_market import site_is_claims_market_listable
        from typeclasses.claim_utils import generate_mining_site

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        try:
            self.assertFalse(site_is_claims_market_listable(site))
        finally:
            room = site.location
            site.delete()
            if room:
                room.delete()

    def test_mining_site_primary_deed_eligibility(self):
        from evennia import create_object

        from typeclasses.claim_market import mining_site_primary_deed_eligibility
        from typeclasses.claim_utils import generate_mining_site

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        a = create_object("typeclasses.characters.Character", key="DiscEligA", location=room)
        b = create_object("typeclasses.characters.Character", key="DiscEligB", location=room)
        try:
            ok, err = mining_site_primary_deed_eligibility(site, a)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

            site.db.discovery_pending = False
            site.db.discovered_by = None
            ok2, err2 = mining_site_primary_deed_eligibility(site, a)
            self.assertTrue(ok2)
            self.assertIsNone(err2)

            site.db.discovered_by = a
            ok3, err3 = mining_site_primary_deed_eligibility(site, b)
            self.assertFalse(ok3)
            ok4, err4 = mining_site_primary_deed_eligibility(site, a)
            self.assertTrue(ok4)
            self.assertIsNone(err4)
        finally:
            a.delete()
            b.delete()
            site.delete()
            if room:
                room.delete()

    def test_survey_registers_discoverer_and_listable(self):
        from evennia import create_object

        from typeclasses.claim_market import site_is_claims_market_listable
        from typeclasses.claim_utils import generate_mining_site
        from world.mining_scanner_ops import attempt_deploy_scanner
        from world.mining_survey_ops import execute_survey

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        char = create_object(
            "typeclasses.characters.Character",
            key="DiscSurveyChar",
            location=room,
        )
        scanner = create_object(
            "typeclasses.mining_scanner.MiningScanner",
            key="DiscSurveyScan",
            location=char,
        )
        try:
            self.assertFalse(site_is_claims_market_listable(site))
            ok, msg = attempt_deploy_scanner(char, scanner_object_id=scanner.id)
            self.assertTrue(ok, msg)
            execute_survey(char)
            self.assertFalse(getattr(site.db, "discovery_pending", True))
            self.assertEqual(getattr(site.db, "discovered_by", None), char)
            self.assertTrue(site_is_claims_market_listable(site))
        finally:
            scanner.delete()
            char.delete()
            site.delete()
            if room:
                room.delete()

    def test_grant_random_claim_marks_buyer_discoverer(self):
        from evennia import create_object

        from typeclasses.claim_utils import grant_random_claim_on_purchase

        char = create_object(
            "typeclasses.characters.Character",
            key="RandClaimDiscChar",
            location=None,
        )
        try:
            claim, _jp = grant_random_claim_on_purchase(char)
            site = claim.db.site_ref
            self.assertIsNotNone(site)
            self.assertFalse(getattr(site.db, "discovery_pending", True))
            self.assertEqual(getattr(site.db, "discovered_by", None), char)
            claim.delete()
            room = site.location
            site.delete()
            if room:
                room.delete()
        finally:
            char.delete()

    def test_list_unclaimed_discovery_for_sale_smoke(self):
        from evennia import create_object

        from typeclasses.claim_market import (
            _get_property_listings_script,
            list_unclaimed_discovery_for_sale,
        )
        from typeclasses.claim_utils import generate_mining_site

        script = _get_property_listings_script()
        if not script:
            self.skipTest("property_listings script not present")

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        room = site.location
        char = create_object(
            "typeclasses.characters.Character",
            key="DiscListSeller",
            location=room,
        )
        try:
            site.db.discovery_pending = False
            site.db.discovered_by = char
            ok, msg = list_unclaimed_discovery_for_sale(char, site.id, 500)
            self.assertTrue(ok, msg)
            listings = list(script.db.listings or [])
            self.assertTrue(any(e.get("site_id") == site.id for e in listings))
            script.db.listings = [e for e in listings if e.get("site_id") != site.id]
        finally:
            char.delete()
            site.delete()
            if room:
                room.delete()
