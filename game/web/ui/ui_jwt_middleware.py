"""Require Bearer JWT for `/ui/*` except exempt and anonymous-GET allowlist."""

from __future__ import annotations

from django.http import JsonResponse

from .jwt_tokens import user_from_access_token
from .ui_jwt_constants import get_requires_jwt


class UiJwtMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith("/ui/"):
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        bearer = ""
        if auth_header.startswith("Bearer "):
            bearer = auth_header[7:].strip()

        if bearer:
            user = user_from_access_token(bearer)
            if user is not None:
                request.user = user
            else:
                return JsonResponse(
                    {"ok": False, "code": "invalid_token", "message": "Invalid or expired access token."},
                    status=401,
                )

        if get_requires_jwt(request):
            if not getattr(request.user, "is_authenticated", False):
                return JsonResponse(
                    {"ok": False, "code": "jwt_required", "message": "Authorization Bearer token required."},
                    status=401,
                )

        return self.get_response(request)
