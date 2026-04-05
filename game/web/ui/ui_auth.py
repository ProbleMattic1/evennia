"""CSRF bootstrap + JWT issue/refresh/revoke for the Next shell."""

from __future__ import annotations

import json

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .jwt_tokens import access_ttl_sec, issue_pair, refresh_ttl_sec, revoke_refresh_token, user_from_refresh_token


@require_GET
def ui_auth_csrf(request):
    from django.views.decorators.csrf import ensure_csrf_cookie

    ensure_csrf_cookie(request)
    return JsonResponse({"ok": True, "csrfToken": get_token(request)})


@require_GET
def ui_auth_status(request):
    u = request.user
    if u.is_authenticated:
        return JsonResponse({"ok": True, "authenticated": True, "username": getattr(u, "username", "") or ""})
    return JsonResponse({"ok": True, "authenticated": False, "username": None})


@csrf_exempt
@require_POST
def ui_auth_token(request):
    """
    Issue access+refresh. Body optional JSON: { "username", "password" }.
    If session is already authenticated, credentials in body are ignored.
    """
    u = request.user
    if not u.is_authenticated:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if not username:
            return JsonResponse(
                {"ok": False, "code": "auth_required", "message": "Log in or send username/password."},
                status=401,
            )
        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({"ok": False, "code": "invalid_credentials", "message": "Invalid credentials."}, status=401)
        login(request, user)
        u = user

    access, refresh = issue_pair(u.pk)
    return JsonResponse(
        {
            "ok": True,
            "access": access,
            "refresh": refresh,
            "accessExpiresIn": access_ttl_sec(),
            "refreshExpiresIn": refresh_ttl_sec(),
        }
    )


@csrf_exempt
@require_POST
def ui_auth_refresh(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    refresh = (body.get("refresh") or "").strip()
    if not refresh:
        return JsonResponse({"ok": False, "code": "missing_refresh", "message": "Missing refresh token."}, status=400)
    user = user_from_refresh_token(refresh)
    if not user:
        return JsonResponse({"ok": False, "code": "invalid_refresh", "message": "Invalid refresh token."}, status=401)
    # rotate: revoke old refresh jti
    revoke_refresh_token(refresh)
    access, new_refresh = issue_pair(user.pk)
    return JsonResponse(
        {
            "ok": True,
            "access": access,
            "refresh": new_refresh,
            "accessExpiresIn": access_ttl_sec(),
            "refreshExpiresIn": refresh_ttl_sec(),
        }
    )


@csrf_exempt
@require_POST
def ui_auth_revoke(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}
    refresh = (body.get("refresh") or "").strip()
    if not refresh:
        return JsonResponse({"ok": False, "code": "missing_refresh", "message": "Missing refresh token."}, status=400)
    revoke_refresh_token(refresh)
    return JsonResponse({"ok": True, "message": "Refresh token revoked."})
