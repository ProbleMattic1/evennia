"""Mining camp/base multipliers."""

import os
import sys
import unittest
from types import SimpleNamespace

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningClusterMultiplier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_probe_complete(self):
        from world.mining_clusters import probe_complete

        self.assertFalse(probe_complete(SimpleNamespace(db=SimpleNamespace(survey_level=2))))
        self.assertTrue(probe_complete(SimpleNamespace(db=SimpleNamespace(survey_level=3))))

    def test_cluster_multiplier_for_site(self):
        from world.mining_clusters import BASE_OUTPUT_MULT, CAMP_OUTPUT_MULT, cluster_multiplier_for_site

        self.assertEqual(cluster_multiplier_for_site(SimpleNamespace(db=SimpleNamespace())), 1.0)
        self.assertEqual(
            cluster_multiplier_for_site(SimpleNamespace(db=SimpleNamespace(cluster_id="camp:u"))),
            CAMP_OUTPUT_MULT,
        )
        self.assertEqual(
            cluster_multiplier_for_site(SimpleNamespace(db=SimpleNamespace(cluster_id="base:u"))),
            BASE_OUTPUT_MULT,
        )
