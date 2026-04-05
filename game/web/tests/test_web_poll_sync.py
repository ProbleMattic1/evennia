"""Session-throttled mission/challenge sync for web polls."""

from unittest.mock import MagicMock

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, SimpleTestCase

from web.ui.web_poll_sync import web_needs_heavy_mission_challenge_sync


class WebPollSyncTests(SimpleTestCase):
    def _request(self):
        req = RequestFactory().get("/ui/control-surface")
        req.session = SessionStore()
        req.session.create()
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
