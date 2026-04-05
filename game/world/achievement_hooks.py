"""Thin wrappers around ``track_achievements`` (stable category/tracking strings)."""

from __future__ import annotations

from typing import Any

from evennia.contrib.game_systems.achievements.achievements import track_achievements


def track_mission_completed(character: Any) -> None:
    track_achievements(character, category="missions", tracking="mission_completed", count=1)


def track_quest_completed(character: Any) -> None:
    track_achievements(character, category="quests", tracking="quest_completed", count=1)


def track_catalog_purchase(character: Any) -> None:
    track_achievements(character, category="economy", tracking="catalog_purchase", count=1)


def track_mining_site_claimed(character: Any) -> None:
    track_achievements(character, category="mining", tracking="mining_site_claimed", count=1)
