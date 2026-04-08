"""Web msg-stream view and character web_msg_buffer coalescing."""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from typeclasses.characters import Character, _WEB_MSG_PENDING
from web.ui import views


class _AttrStore:
    def __init__(self):
        self._d = {"web_msg_buffer": [], "web_msg_seq": 0}

    def get(self, key, default=None):
        return self._d.get(key, default)

    def add(self, key, val):
        self._d[key] = val


class _DummyChar:
    """Minimal stand-in for Character web buffer methods (no Evennia DB)."""

    WEB_MSG_BUFFER_MAX = 200

    def __init__(self, oid):
        self.id = oid
        self.attributes = _AttrStore()


class WebMsgBufferCoalesceTests(SimpleTestCase):
    def tearDown(self):
        super().tearDown()
        _WEB_MSG_PENDING.clear()

    def test_pending_flushes_on_get_after_sub_batch(self):
        d = _DummyChar(9001)
        meta = {}
        for i in range(7):
            Character.record_web_stream_text(d, f"line{i}", meta)
        self.assertEqual(len(_WEB_MSG_PENDING.get(9001, [])), 7)
        self.assertEqual(d.attributes.get("web_msg_buffer", []), [])

        rows = Character.get_web_msg_buffer(d, 0)
        self.assertEqual(len(rows), 7)
        self.assertEqual(_WEB_MSG_PENDING.get(9001, []), [])
        self.assertEqual(len(d.attributes.get("web_msg_buffer", [])), 7)

    def test_pending_flushes_when_batch_size_reached(self):
        d = _DummyChar(9002)
        meta = {}
        for i in range(8):
            Character.record_web_stream_text(d, f"row{i}", meta)
        self.assertEqual(_WEB_MSG_PENDING.get(9002, []), [])
        stored = d.attributes.get("web_msg_buffer", [])
        self.assertEqual(len(stored), 8)
        self.assertEqual(stored[-1]["seq"], 8)


class MsgStreamViewTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_anonymous_401(self):
        req = self.factory.get("/ui/msg-stream?since=0")
        req.user = AnonymousUser()
        resp = views.msg_stream(req)
        self.assertEqual(resp.status_code, 401)

    def test_no_character_400(self):
        req = self.factory.get("/ui/msg-stream?since=0")
        req.user = MagicMock(is_authenticated=True)
        with patch.object(views, "_resolve_character_for_web", return_value=(None, "No character.")):
            resp = views.msg_stream(req)
        self.assertEqual(resp.status_code, 400)

    def test_immediate_empty_payload(self):
        char = MagicMock()
        char.get_web_msg_buffer = MagicMock(return_value=[])
        req = self.factory.get("/ui/msg-stream?since=3")
        req.user = MagicMock(is_authenticated=True)
        with patch.object(views, "_resolve_character_for_web", return_value=(char, None)):
            resp = views.msg_stream(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["messages"], [])
        self.assertEqual(data["seq"], 3)
        char.get_web_msg_buffer.assert_called_once_with(since_seq=3)

    def test_returns_new_rows(self):
        char = MagicMock()
        char.get_web_msg_buffer = MagicMock(
            return_value=[{"seq": 4, "html": "<p>x</p>", "ts": 1.0, "meta": {}}]
        )
        req = self.factory.get("/ui/msg-stream?since=3")
        req.user = MagicMock(is_authenticated=True)
        with patch.object(views, "_resolve_character_for_web", return_value=(char, None)):
            resp = views.msg_stream(req)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(data["seq"], 4)
        self.assertEqual(len(data["messages"]), 1)

    @patch("web.ui.views.time.sleep", lambda *_a, **_k: None)
    def test_long_poll_exits_on_deadline(self):
        char = MagicMock()
        char.get_web_msg_buffer = MagicMock(return_value=[])

        # First monotonic for deadline, then always past deadline inside loop
        with patch("web.ui.views.time.monotonic", side_effect=[0.0, 100.0, 100.0]):
            req = self.factory.get("/ui/msg-stream?since=0&block_ms=500")
            req.user = MagicMock(is_authenticated=True)
            with patch.object(views, "_resolve_character_for_web", return_value=(char, None)):
                resp = views.msg_stream(req)

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["messages"], [])
        self.assertGreaterEqual(char.get_web_msg_buffer.call_count, 1)
