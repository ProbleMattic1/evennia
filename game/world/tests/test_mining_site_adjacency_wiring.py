"""Strip wiring between mining rooms at generation (no backfill)."""

import os
import sys
import unittest

MIN_PY = (3, 11)


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningSiteAdjacencyWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_two_new_mines_mutually_neighbor_via_strip(self):
        from typeclasses.claim_utils import generate_mining_site
        from world.mining_adjacent_scan import neighbor_rooms
        from world.venues import apply_venue_metadata

        s1 = generate_mining_site(
            is_jackpot=False,
            venue_id="nanomega_core",
            register_for_market_survey=False,
        )
        r1 = s1.location
        apply_venue_metadata(r1, "nanomega_core")

        s2 = generate_mining_site(
            is_jackpot=False,
            venue_id="nanomega_core",
            register_for_market_survey=False,
        )
        r2 = s2.location
        apply_venue_metadata(r2, "nanomega_core")

        try:
            n1 = {int(x.id) for x in neighbor_rooms(r1)}
            n2 = {int(x.id) for x in neighbor_rooms(r2)}
            self.assertIn(int(r2.id), n1, "first deposit room should neighbor second")
            self.assertIn(int(r1.id), n2, "second deposit room should neighbor first")
        finally:
            for s in (s2, s1):
                loc = s.location
                s.delete()
                if loc:
                    loc.delete()

    def test_first_mine_in_venue_has_no_strip_peer(self):
        from typeclasses.claim_utils import generate_mining_site
        from world.mining_site_adjacency_wiring import _strip_exit_degree
        from world.venues import apply_venue_metadata

        s1 = generate_mining_site(
            is_jackpot=False,
            venue_id="nanomega_core",
            register_for_market_survey=False,
        )
        r1 = s1.location
        apply_venue_metadata(r1, "nanomega_core")
        try:
            self.assertEqual(
                _strip_exit_degree(r1),
                0,
                "first room should have no strip exits until a second mine exists",
            )
        finally:
            loc = s1.location
            s1.delete()
            if loc:
                loc.delete()
