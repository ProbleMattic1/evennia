"""
Cross-check crime template ids vs crime-triggered mission templates.
"""

from __future__ import annotations

from evennia.utils import logger

from world.crime_registry import get_crime_snapshot
from world.mission_loader import all_mission_templates


def log_crime_mission_coverage() -> None:
    snap = get_crime_snapshot()
    crime_ids = set(snap.get("valid_ids") or ())
    if not crime_ids:
        logger.log_warn("[crime↔mission] no crime ids in registry (check JSON sources).")
        return

    covered: set[str] = set()
    orphans: list[tuple[str, str]] = []

    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != "crime":
            continue
        for sid in trig.get("seedIdsAny") or []:
            sid = str(sid).strip()
            if not sid:
                continue
            if sid in crime_ids:
                covered.add(sid)
            else:
                orphans.append((tmpl.get("id") or "", sid))

    missing = sorted(crime_ids - covered)
    if missing:
        logger.log_warn(
            "[crime↔mission] crime ids with no crime mission (seedIdsAny): "
            f"{missing[:40]}{' …' if len(missing) > 40 else ''}"
        )

    if orphans:
        logger.log_warn(
            "[crime↔mission] mission crime triggers reference unknown crime ids "
            f"(first 25): {orphans[:25]}{' …' if len(orphans) > 25 else ''}"
        )

    if not missing and not orphans:
        logger.log_info(
            f"[crime↔mission] OK — {len(crime_ids)} crime ids, "
            f"{len(covered)} linked to at least one crime mission."
        )
