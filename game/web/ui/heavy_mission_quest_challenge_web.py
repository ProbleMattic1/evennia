"""
Centralized mission / quest / challenge sync for web GET polls.

``control_surface_state`` and ``dashboard_state`` must stay identical here so
session-based throttling (``web_poll_sync``) and sync ordering stay one place.
This keeps Evennia's Django WSGI layer predictable: the same work is not
maintained twice, and future tightening (e.g. cheaper pre-checks) has a single
call site.

Call only when ``request.user`` is authenticated and ``char`` is the active
web character (same preconditions as the previous inlined blocks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .web_poll_sync import web_needs_heavy_mission_challenge_sync

if TYPE_CHECKING:
    from django.http import HttpRequest


def run_heavy_mission_quest_challenge_sync_if_due(request: HttpRequest, char) -> bool:
    """
    If ``web_needs_heavy_mission_challenge_sync`` is true, run the full sync chain.

    Order (do not reorder without reviewing mission/quest/challenge handlers):
        1. Global mission seeds
        2. Room-scoped missions + quest room enter hook (only when located)
        3. Challenge window sync + evaluation

    Returns:
        True if the heavy block ran, False if throttled/skipped by session policy.
    """
    if not web_needs_heavy_mission_challenge_sync(request, char):
        return False

    char.missions.sync_global_seeds()
    if char.location:
        char.missions.sync_room(char.location)
        char.quests.on_room_enter(char.location)
    char.challenges.sync_all_windows()
    char.challenges.evaluate_window()
    return True


__all__ = ("run_heavy_mission_quest_challenge_sync_if_due",)
