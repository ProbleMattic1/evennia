"""Session-throttled mission/challenge sync for web polls."""

from unittest.mock import MagicMock

from django.test import RequestFactory, SimpleTestCase

from web.ui.web_poll_sync import web_needs_heavy_mission_challenge_sync


class _MemorySession(dict):
    """Minimal session stand-in for RequestFactory (no DB; SimpleTestCase-safe)."""

    def __init__(self):
        super().__init__()
        self.modified = False


class WebPollSyncTests(SimpleTestCase):
    def _request(self):
        req = RequestFactory().get("/ui/control-surface")
        req.session = _MemorySession()
        return req

    def test_room_change_triggers_sync(self):
        req = self._request()
        loc1 = MagicMock()
        loc1.id = 10
        loc2 = MagicMock()
        loc2.id = 20
        char = MagicMock()
        char.id = 1
        char.location = loc1
        self.assertTrue(web_needs_heavy_mission_challenge_sync(req, char))
        self.assertFalse(web_needs_heavy_mission_challenge_sync(req, char))
        char.location = loc2
        self.assertTrue(web_needs_heavy_mission_challenge_sync(req, char))

    def test_no_character_never_requests_heavy_sync(self):
        req = self._request()
        self.assertFalse(web_needs_heavy_mission_challenge_sync(req, None))
        self.assertFalse(web_needs_heavy_mission_challenge_sync(req, None))
