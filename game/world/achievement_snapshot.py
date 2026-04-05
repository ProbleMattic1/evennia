"""
Achievement list + summary for web dashboards (control surface).

Builds on ``evennia.contrib.game_systems.achievements`` definitions and the
character's persisted progress attribute.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from evennia.contrib.game_systems.achievements import achievements as ach
from evennia.utils.utils import is_iter, make_iter


def _player_progress_blob(achiever: Any) -> dict[str, Any]:
    """Full achievement progress dict (same shape as contrib internal store)."""
    attr = make_iter(getattr(settings, "ACHIEVEMENT_CONTRIB_ATTRIBUTE", "achievements"))
    key = attr[0]
    cat = attr[1] if len(attr) > 1 else None
    data = achiever.attributes.get(key, default={}, category=cat)
    if data and hasattr(data, "deserialize"):
        data = data.deserialize()
    return dict(data) if isinstance(data, dict) else {}


def _prereqs_satisfied(progress: dict[str, Any], prereqs: Any) -> bool:
    for p in make_iter(prereqs or []):
        pk = str(p).lower()
        if not progress.get(pk, {}).get("completed"):
            return False
    return True


def _row_for_achievement(
    achieve_key: str,
    defn: dict[str, Any],
    progress: dict[str, Any],
) -> dict[str, Any]:
    row_progress = progress.get(achieve_key, {}) or {}
    completed_ach = bool(row_progress.get("completed"))
    target = int(defn.get("count") or 1)
    if target < 1:
        target = 1

    separate = defn.get("tracking_type", "sum") == "separate"
    raw_p = row_progress.get("progress")
    locked = not _prereqs_satisfied(progress, defn.get("prereqs"))

    progress_list: list[int] | None = None
    if locked:
        progress_out = 0
    elif completed_ach:
        progress_out = target
    elif separate and is_iter(defn.get("tracking")) and isinstance(raw_p, list):
        progress_list = [int(x) for x in raw_p]
        progress_out = min(progress_list) if progress_list else 0
    else:
        progress_out = int(raw_p) if raw_p is not None else 0

    cat = defn.get("category", "")
    if isinstance(cat, (list, tuple)):
        cat_str = ",".join(str(c) for c in cat)
    else:
        cat_str = str(cat or "")

    row: dict[str, Any] = {
        "key": achieve_key,
        "name": defn.get("name") or achieve_key,
        "desc": defn.get("desc") or "",
        "category": cat_str,
        "completed": completed_ach,
        "locked": locked,
        "progress": progress_out,
        "target": target,
    }
    if progress_list is not None:
        row["progressList"] = progress_list
    return row


def achievement_dashboard_block(achiever: Any) -> dict[str, Any]:
    """
    Summary + per-achievement rows for ``get_rpg_dashboard_snapshot`` / control surface.

    Sort: category, name (case-insensitive), then incomplete before complete.
    """
    defs = ach.all_achievements()
    progress = _player_progress_blob(achiever)
    items = [_row_for_achievement(k, defs[k], progress) for k in defs]
    items.sort(key=lambda r: (r["category"], r["name"].lower(), r["completed"]))
    completed_n = sum(1 for r in items if r["completed"])
    return {
        "completed": completed_n,
        "total": len(items),
        "items": items,
    }
