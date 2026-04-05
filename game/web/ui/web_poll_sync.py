"""
Throttle expensive mission / quest / challenge sync on web GET polls.

Full sync runs when the puppet's room changes, on the first poll for that character
in the session, or after WEB_HEAVY_SYNC_COOLDOWN_SEC without a sync. POST handlers
that mutate missions should continue to call sync explicitly before serialize.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest

WEB_HEAVY_SYNC_COOLDOWN_SEC = 60.0

_SESSION_KEY_PREFIX = "web_heavy_mc_sync:"


def web_needs_heavy_mission_challenge_sync(request: HttpRequest, char) -> bool:
    """True when control-surface / dashboard should run sync_* and challenge evaluate."""
    if char is None:
        return True
    rid = char.location.id if getattr(char, "location", None) else None
    sk = f"{_SESSION_KEY_PREFIX}{char.id}"
    raw = request.session.get(sk)
    prev_room = None
    prev_t = 0.0
    if isinstance(raw, dict):
        if raw.get("room_id") is not None:
            try:
                prev_room = int(raw["room_id"])
            except (TypeError, ValueError):
                prev_room = None
        try:
            prev_t = float(raw.get("t") or 0)
        except (TypeError, ValueError):
            prev_t = 0.0
    now = time.time()
    room_changed = prev_room != rid
    cooldown_done = (now - prev_t) >= WEB_HEAVY_SYNC_COOLDOWN_SEC
    if not room_changed and not cooldown_done and raw is not None:
        return False
    request.session[sk] = {"room_id": rid, "t": now}
    request.session.modified = True
    return True
