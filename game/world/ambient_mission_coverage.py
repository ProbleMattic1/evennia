"""
Cross-check ambient template ids vs alert-triggered mission templates.

Run after both registries load so typos in seedIdsAny show up in logs immediately.
"""

from __future__ import annotations

from evennia.utils import logger

from world.ambient_registry import get_ambient_snapshot
from world.mission_loader import all_mission_templates


def log_ambient_mission_coverage() -> None:
    snap = get_ambient_snapshot()
    ambient_ids = set(snap.get("valid_ids") or ())
    if not ambient_ids:
        logger.log_warn("[ambient↔mission] no ambient ids in registry (check JSON sources).")
        return

    covered: set[str] = set()
    orphans: list[tuple[str, str]] = []

    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != "alert":
            continue
        for sid in trig.get("seedIdsAny") or []:
            sid = str(sid).strip()
            if not sid:
                continue
            if sid in ambient_ids:
                covered.add(sid)
            else:
                orphans.append((tmpl.get("id") or "", sid))

    missing = sorted(ambient_ids - covered)
    if missing:
        logger.log_warn(
            "[ambient↔mission] ambient ids with no alert mission (seedIdsAny): "
            f"{missing[:40]}{' …' if len(missing) > 40 else ''}"
        )

    if orphans:
        logger.log_warn(
            "[ambient↔mission] mission alert triggers reference unknown ambient ids "
            f"(first 25): {orphans[:25]}{' …' if len(orphans) > 25 else ''}"
        )

    if not missing and not orphans:
        logger.log_info(
            f"[ambient↔mission] OK — {len(ambient_ids)} ambient ids, "
            f"{len(covered)} linked to at least one alert mission."
        )
