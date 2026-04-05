"""JWT helpers and allowlist for `/ui/*`."""

import os

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from web.ui.jwt_tokens import decode_token, issue_pair, user_from_access_token
from web.ui.ui_jwt_constants import get_requires_jwt, path_is_jwt_exempt


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "throttle": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
)
class UiJwtTokenTests(TestCase):
    def setUp(self):
        os.environ["AURNOM_JWT_SECRET"] = "test-secret-key-for-jwt-unit-tests"
        User = get_user_model()
        self.user = User.objects.create_user(username="jwt_tester", password="test-pass-xyz")

    def tearDown(self):
        os.environ.pop("AURNOM_JWT_SECRET", None)

    def test_issue_and_validate_access(self):
        access, refresh = issue_pair(self.user.pk)
        u = user_from_access_token(access)
        self.assertIsNotNone(u)
        self.assertEqual(u.pk, self.user.pk)
        payload = decode_token(refresh, expected_typ="refresh")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], str(self.user.pk))


class UiJwtPathTests(TestCase):
    def test_exempt_auth_paths(self):
        self.assertTrue(path_is_jwt_exempt("/ui/auth/csrf"))
        self.assertTrue(path_is_jwt_exempt("/ui/auth/token"))

    def test_requires_jwt_for_msg_stream(self):
        class R:
            path = "/ui/msg-stream"
            method = "GET"

        self.assertTrue(get_requires_jwt(R()))

    def test_anon_get_control_surface(self):
        class R:
            path = "/ui/control-surface"
            method = "GET"

        self.assertFalse(get_requires_jwt(R()))
