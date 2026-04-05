"""Tests for contrib JSON endpoints (mail list auth, dice roll, staff reports permission)."""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from web.ui import contrib_web


class ContribWebMailTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_mail_list_anonymous_401(self):
        req = self.factory.get("/ui/mail")
        req.user = AnonymousUser()
        resp = contrib_web.ui_mail_list(req)
        self.assertEqual(resp.status_code, 401)


class ContribWebDiceTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_roll_anonymous_401(self):
        req = self.factory.post("/ui/play/roll", data=b"{}", content_type="application/json")
        req.user = AnonymousUser()
        resp = contrib_web.ui_play_roll(req)
        self.assertEqual(resp.status_code, 401)

    @patch.object(contrib_web, "_resolve_character_for_web", return_value=(None, "No character."))
    def test_roll_no_character_400(self, _mock_res):
        req = self.factory.post(
            "/ui/play/roll",
            data=json.dumps({"expression": "1d6"}).encode("utf-8"),
            content_type="application/json",
        )
        req.user = MagicMock(is_authenticated=True)
        resp = contrib_web.ui_play_roll(req)
        self.assertEqual(resp.status_code, 400)

    @patch.object(contrib_web.dice_contrib, "roll", return_value=4)
    def test_roll_ok(self, _mock_roll):
        char = MagicMock()
        char.key = "Tester"
        loc = MagicMock()
        char.location = loc

        req = self.factory.post(
            "/ui/play/roll",
            data=json.dumps({"expression": "1d6", "visibility": "secret"}).encode("utf-8"),
            content_type="application/json",
        )
        req.user = MagicMock(is_authenticated=True)

        with patch.object(contrib_web, "_resolve_character_for_web", return_value=(char, None)):
            resp = contrib_web.ui_play_roll(req)

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("result"), 4)
        char.msg.assert_called_once()


class ContribWebStaffReportsTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_staff_list_anonymous_401(self):
        req = self.factory.get("/ui/staff/reports?type=bugs")
        req.user = AnonymousUser()
        resp = contrib_web.ui_staff_reports_list(req)
        self.assertEqual(resp.status_code, 401)

    def test_staff_list_non_admin_403(self):
        acc = MagicMock(is_authenticated=True, is_superuser=False)
        acc.check_permstring = MagicMock(return_value=False)
        req = self.factory.get("/ui/staff/reports?type=bugs")
        req.user = acc
        resp = contrib_web.ui_staff_reports_list(req)
        self.assertEqual(resp.status_code, 403)
