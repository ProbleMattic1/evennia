"""
Cross-check battlespace template ids vs battlespace-triggered mission templates.
"""

from __future__ import annotations

from evennia.utils import logger

from world.battlespace_registry import get_battlespace_snapshot
from world.mission_loader import all_mission_templates


def log_battlespace_mission_coverage() -> None:
    snap = get_battlespace_snapshot()
    bs_ids = set(snap.get("valid_ids") or ())
    if not bs_ids:
        logger.log_warn("[battlespace↔mission] no battlespace ids in registry (check JSON sources).")
        return

    covered: set[str] = set()
    orphans: list[tuple[str, str]] = []

    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != "battlespace":
            continue
        for sid in trig.get("seedIdsAny") or []:
            sid = str(sid).strip()
            if not sid:
                continue
            if sid in bs_ids:
                covered.add(sid)
            else:
                orphans.append((tmpl.get("id") or "", sid))

    missing = sorted(bs_ids - covered)
    if missing:
        logger.log_warn(
            "[battlespace↔mission] battlespace ids with no mission (seedIdsAny): "
            f"{missing[:40]}{' …' if len(missing) > 40 else ''}"
        )

    if orphans:
        logger.log_warn(
            "[battlespace↔mission] mission battlespace triggers reference unknown ids "
            f"(first 25): {orphans[:25]}{' …' if len(orphans) > 25 else ''}"
        )

    if not missing and not orphans:
        logger.log_info(
            f"[battlespace↔mission] OK — {len(bs_ids)} battlespace ids, "
            f"{len(covered)} linked to at least one mission."
        )
