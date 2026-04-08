"""Mining district key assignment."""

import os
import sys
import unittest

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningDistricts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_assign_district_key_deterministic(self):
        from world.mining_districts import assign_district_key

        a = assign_district_key("nanomega_core", 101)
        b = assign_district_key("nanomega_core", 101)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("nm-"))

    def test_generate_mining_site_sets_district(self):
        from typeclasses.claim_utils import generate_mining_site

        site = generate_mining_site(is_jackpot=False, venue_id="nanomega_core")
        try:
            self.assertTrue(getattr(site.db, "mining_district_key", None))
            self.assertIsInstance(site.db.mining_district_key, str)
        finally:
            room = site.location
            site.delete()
            if room:
                room.delete()
