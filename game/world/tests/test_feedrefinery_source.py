"""Unit tests for ``world.feedrefinery_source.parse_feedrefinery_source`` (no Evennia)."""

import unittest

from world.feedrefinery_source import parse_feedrefinery_source


class TestParseFeedrefinerySource(unittest.TestCase):
    def test_auto_no_keyword(self):
        self.assertEqual(parse_feedrefinery_source("iron 10"), ("auto", "iron 10"))
        self.assertEqual(parse_feedrefinery_source("  ALL  "), ("auto", "all"))

    def test_shared_aliases(self):
        self.assertEqual(parse_feedrefinery_source("shared iron 5"), ("shared", "iron 5"))
        self.assertEqual(parse_feedrefinery_source("plant all"), ("shared", "all"))
        self.assertEqual(parse_feedrefinery_source("BAY copper 2"), ("shared", "copper 2"))

    def test_silo_aliases(self):
        self.assertEqual(parse_feedrefinery_source("silo iron 1"), ("silo", "iron 1"))
        self.assertEqual(parse_feedrefinery_source("mine all"), ("silo", "all"))
        self.assertEqual(parse_feedrefinery_source("personal lead 3"), ("silo", "lead 3"))

    def test_shared_preserves_remainder_case_insensitive_match(self):
        m, r = parse_feedrefinery_source("Shared IRON 10")
        self.assertEqual(m, "shared")
        self.assertEqual(r, "iron 10")


if __name__ == "__main__":
    unittest.main()
