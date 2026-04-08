"""NPC characters do not load or advance persisted challenge state."""

from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from world.challenges.challenge_handler import (
    ChallengeHandler,
    NonParticipantChallengeHandler,
    challenge_handler_for_object,
    character_participates_in_challenge_system,
)


class ChallengeNpcExclusionTests(SimpleTestCase):
    def test_participation_false_for_npc(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=True))
        self.assertFalse(character_participates_in_challenge_system(obj))

    def test_participation_true_for_player(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=False))
        self.assertTrue(character_participates_in_challenge_system(obj))

    def test_participation_true_when_is_npc_missing(self):
        obj = SimpleNamespace(db=SimpleNamespace())
        self.assertTrue(character_participates_in_challenge_system(obj))

    def test_factory_returns_non_participant_for_npc(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=True))
        h = challenge_handler_for_object(obj)
        self.assertIsInstance(h, NonParticipantChallengeHandler)

    def test_non_participant_emit_path_is_noop(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=True))
        h = challenge_handler_for_object(obj)
        h.on_event("room_enter", {"room_id": 1, "zone_id": "arrival"})
        self.assertEqual(h.evaluate_window("daily"), [])
        self.assertEqual(list(h.telemetry.get("zones_today") or []), [])

    def test_non_participant_mark_complete_false(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=True))
        h = challenge_handler_for_object(obj)
        self.assertFalse(h.mark_complete("daily.test", "daily:2026-01-01"))

    def test_non_participant_serialize_shape(self):
        obj = SimpleNamespace(db=SimpleNamespace(is_npc=True))
        h = challenge_handler_for_object(obj)
        with mock.patch(
            "world.challenges.challenge_handler.all_point_offers",
            return_value=(),
        ):
            web = h.serialize_for_web()
        self.assertEqual(web["active"], [])
        self.assertEqual(web["pointsLifetime"], 0)
        self.assertEqual(web["equippedPerks"], [])

    def test_factory_returns_challenge_handler_for_player(self):
        class _Attr:
            def __init__(self):
                self._d = None

            def get(self, key, category=None, default=None):
                return self._d if key == "_challenges" else default

            def add(self, key, val, category=None):
                self._d = val

        obj = SimpleNamespace(db=SimpleNamespace(is_npc=False), attributes=_Attr())
        h = challenge_handler_for_object(obj)
        self.assertIsInstance(h, ChallengeHandler)
