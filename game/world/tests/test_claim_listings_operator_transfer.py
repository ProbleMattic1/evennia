"""Player-listed mining deed sale: survey operator rights must follow the buyer."""

import os
import sys
import unittest

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestClaimListingsMiningOperatorTransfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_buy_listed_mining_claim_transfers_discovered_by_to_buyer(self):
        """
        Survey-era deposits pin ``discovered_by``; deploy requires buyer == discoverer.
        Listing sale must reassign operator to the purchaser (regression vs survey rollout).
        """
        from evennia import create_object, search_object

        from typeclasses.claim_listings import (
            buy_listed_claim,
            get_claim_listings_script,
            list_claim_for_sale,
        )
        from typeclasses.claim_market import mining_site_buyer_may_operate_exclusive
        from typeclasses.claim_utils import create_claim_for_site, generate_mining_site
        from typeclasses.economy import get_economy
        from world.venues import apply_venue_metadata, get_venue

        hub_key = get_venue("nanomega_core")["hub_key"]
        found_hub = search_object(hub_key)
        if found_hub:
            hub = found_hub[0]
        else:
            hub = create_object("typeclasses.rooms.Room", key=hub_key)
        apply_venue_metadata(hub, "nanomega_core")

        container = None
        for obj in hub.contents:
            if getattr(obj.db, "is_claim_listings_container", False):
                container = obj
                break
        created_container = False
        if not container:
            container = create_object(
                "typeclasses.objects.Object",
                key="Test Claim Listings Escrow",
                location=hub,
                home=hub,
            )
            container.db.is_claim_listings_container = True
            container.locks.add("get:false();drop:false()")
            created_container = True

        script = get_claim_listings_script("nanomega_core", create_missing=True)
        self.assertIsNotNone(script, "claim_listings script required")
        prev_listings = list(script.db.listings or [])

        seller = create_object(
            "typeclasses.characters.Character",
            key="ClaimListSellerOp",
            location=hub,
        )
        buyer = create_object(
            "typeclasses.characters.Character",
            key="ClaimListBuyerOp",
            location=hub,
        )

        site = generate_mining_site(
            is_jackpot=False,
            venue_id="nanomega_core",
            register_for_market_survey=False,
        )
        site_room = site.location
        site.db.discovered_by = seller
        site.db.discovery_pending = False

        claim = create_claim_for_site(site, seller, is_jackpot=False)
        cid = claim.id

        econ = get_economy(create_missing=True)
        self.assertIsNotNone(econ)
        b_acct = econ.get_character_account(buyer)
        econ.ensure_account(b_acct, opening_balance=500_000)
        buyer.db.credits = econ.get_balance(b_acct)

        try:
            ok, msg = list_claim_for_sale(seller, cid, price=1000)
            self.assertTrue(ok, msg)
            self.assertEqual(claim.location, container)

            ok_buy, err = mining_site_buyer_may_operate_exclusive(site, buyer)
            self.assertFalse(ok_buy, "buyer must not pass deploy gate before purchase")
            self.assertIsNotNone(err)

            ok2, msg2 = buy_listed_claim(buyer, cid)
            self.assertTrue(ok2, msg2)

            self.assertEqual(claim.location, buyer)
            self.assertEqual(getattr(site.db, "discovered_by", None), buyer)
            self.assertFalse(getattr(site.db, "discovery_pending", True))
            self.assertIsNotNone(getattr(site.db, "discovered_at", None))

            ok3, err3 = mining_site_buyer_may_operate_exclusive(site, buyer)
            self.assertTrue(ok3, err3)
            self.assertIsNone(err3)

            self.assertFalse(
                any(e.get("claim_id") == cid for e in (script.db.listings or []))
            )
        finally:
            claim.delete()
            seller.delete()
            buyer.delete()
            site.delete()
            if site_room:
                site_room.delete()
            if created_container:
                container.delete()
            script.db.listings = prev_listings
