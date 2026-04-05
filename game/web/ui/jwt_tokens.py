"""
HS256 JWT issue/validate for `/ui/*` JSON. Denylist entries use Django cache (Redis in Docker).
"""

from __future__ import annotations

import os
import time
import uuid

import jwt
from django.contrib.auth import get_user_model
from django.core.cache import cache

JWT_ISSUER = "aurnom-ui"
JWT_ALG = "HS256"


def _secret() -> str:
    s = (os.environ.get("AURNOM_JWT_SECRET") or "").strip()
    if s:
        return s
    if os.environ.get("POSTGRES_HOST"):
        # Docker dev default — replace in production
        return "aurnom-dev-jwt-secret-change-me"
    return "aurnom-local-jwt-secret"


def access_ttl_sec() -> int:
    return int(os.environ.get("AURNOM_JWT_ACCESS_TTL_SEC", "900"))


def refresh_ttl_sec() -> int:
    return int(os.environ.get("AURNOM_JWT_REFRESH_TTL_SEC", str(7 * 24 * 3600)))


def deny_cache_key(jti: str) -> str:
    return f"aurnom:jwt:deny:{jti}"


def deny_jti(jti: str, ttl_sec: int) -> None:
    cache.set(deny_cache_key(jti), 1, timeout=max(1, int(ttl_sec)))


def is_jti_denied(jti: str) -> bool:
    return bool(cache.get(deny_cache_key(jti)))


def issue_pair(account_id: int) -> tuple[str, str]:
    now = int(time.time())
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    secret = _secret()
    access = jwt.encode(
        {
            "sub": str(account_id),
            "typ": "access",
            "jti": access_jti,
            "iat": now,
            "exp": now + access_ttl_sec(),
            "iss": JWT_ISSUER,
        },
        secret,
        algorithm=JWT_ALG,
    )
    refresh = jwt.encode(
        {
            "sub": str(account_id),
            "typ": "refresh",
            "jti": refresh_jti,
            "iat": now,
            "exp": now + refresh_ttl_sec(),
            "iss": JWT_ISSUER,
        },
        secret,
        algorithm=JWT_ALG,
    )
    if isinstance(access, bytes):
        access = access.decode("utf-8")
    if isinstance(refresh, bytes):
        refresh = refresh.decode("utf-8")
    return access, refresh


def decode_token(token: str, *, expected_typ: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[JWT_ALG],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "sub", "jti", "typ"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != expected_typ:
        return None
    jti = payload.get("jti")
    if not jti or is_jti_denied(str(jti)):
        return None
    return payload


def user_from_access_token(token: str):
    payload = decode_token(token, expected_typ="access")
    if not payload:
        return None
    User = get_user_model()
    try:
        pk = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return None


def user_from_refresh_token(token: str):
    payload = decode_token(token, expected_typ="refresh")
    if not payload:
        return None
    User = get_user_model()
    try:
        pk = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return None


def revoke_refresh_token(token: str) -> bool:
    payload = decode_token(token, expected_typ="refresh")
    if not payload:
        # still try to decode without deny check for jti
        try:
            payload = jwt.decode(
                token,
                _secret(),
                algorithms=[JWT_ALG],
                issuer=JWT_ISSUER,
                options={"verify_exp": False},
            )
        except jwt.PyJWTError:
            return False
    jti = payload.get("jti")
    if not jti:
        return False
    deny_jti(str(jti), refresh_ttl_sec())
    return True
