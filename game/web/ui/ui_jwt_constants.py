"""Paths under `/ui/*` that never require a Bearer access token."""

from __future__ import annotations

# Auth handshake (no JWT yet)
UI_JWT_AUTH_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/ui/auth/csrf",
    "/ui/auth/token",
    "/ui/auth/refresh",
    "/ui/auth/revoke",
    "/ui/auth/status",
)


def path_is_jwt_exempt(path: str) -> bool:
    p = path.rstrip("/") or "/"
    for prefix in UI_JWT_AUTH_EXEMPT_PREFIXES:
        base = prefix.rstrip("/")
        if p == base or p.startswith(base + "/"):
            return True
    return False


# GET without JWT: anonymous browsing (sparse payloads where views support it)
UI_ANON_GET_PREFIXES: tuple[str, ...] = (
    "/ui/control-surface",
    "/ui/world-graph",
    "/ui/nav",
    "/ui/claims-market",
    "/ui/economy-world",
    "/ui/play",
    "/ui/bank",
    "/ui/shop",
    "/ui/market",
    "/ui/real-estate",
    "/ui/processing",
    "/ui/refinery",
    "/ui/resources",
    "/ui/package/listings",
    "/ui/claim/detail",
    "/ui/property/detail",
    "/ui/property/deed-listings",
    "/ui/dashboard",
)


def get_requires_jwt(request) -> bool:
    """True if this request must present a valid Bearer access token."""
    path = request.path.rstrip("/") or "/"
    if path_is_jwt_exempt(path):
        return False
    if request.method == "GET":
        for prefix in UI_ANON_GET_PREFIXES:
            base = prefix.rstrip("/")
            if path == base or path.startswith(base + "/"):
                return False
    return True
