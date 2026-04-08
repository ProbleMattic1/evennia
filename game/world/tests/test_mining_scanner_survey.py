"""Survey requires deployed mining scanner."""

import os
import sys
import unittest
from types import SimpleNamespace

MIN_PY = (3, 11)


class _FakeCooldowns:
    def __init__(self):
        self._blocked = False

    def ready(self, key):
        return not self._blocked

    def time_left(self, key):
        return 2.5 if self._blocked else 0.0

    def add(self, key, sec):
        self._blocked = True


class _FakeTags:
    def __init__(self, mining_site=False, mining_scanner=False):
        self._ms = mining_site
        self._sc = mining_scanner

    def has(self, name, category=None):
        if name == "mining_site" and category == "mining":
            return self._ms
        if name == "mining_scanner" and category == "mining":
            return self._sc
        return False


class _FakeSite:
    def __init__(self):
        self.db = SimpleNamespace(survey_level=0)
        self.tags = _FakeTags(mining_site=True)

    def advance_survey(self):
        from typeclasses.mining import SURVEY_LEVELS

        cur = int(self.db.survey_level or 0)
        if cur >= 3:
            return cur, "done"
        self.db.survey_level = cur + 1
        return self.db.survey_level, f"report L{self.db.survey_level}"


class _FakeScanner:
    def __init__(self, owner, site):
        self.db = SimpleNamespace(
            is_deployed=True,
            owner=owner,
            deploy_site_ref=site,
        )

    def is_typeclass(self, path, exact=False):
        return str(path).endswith("MiningScanner")


@unittest.skipUnless(sys.version_info >= MIN_PY, "project baseline Python 3.11+")
class TestMiningScannerSurvey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
        import django

        django.setup()

    def test_execute_survey_fails_without_scanner(self):
        from world.mining_survey_ops import execute_survey
        from world.web_interactions import InteractionError

        site = _FakeSite()
        room = SimpleNamespace(contents=[site])
        char = SimpleNamespace(location=room, cooldowns=_FakeCooldowns())
        with self.assertRaises(InteractionError):
            execute_survey(char)

    def test_execute_survey_succeeds_with_scanner(self):
        from world.mining_survey_ops import execute_survey
        from world.web_interactions import InteractionError

        site = _FakeSite()
        char = SimpleNamespace(location=None, cooldowns=_FakeCooldowns())
        scanner = _FakeScanner(char, site)
        room = SimpleNamespace(contents=[site, scanner])
        char.location = room
        line = execute_survey(char)
        self.assertEqual(line.interaction_key, "survey")
        self.assertIn("level 1", line.dialogue.lower())
        self.assertFalse(char.cooldowns.ready("survey_scan"))
