"""
Load ambient templates from JSON; validate; build cadence buckets.
Call from at_server_start and from reload command.
"""

from __future__ import annotations

import json
from pathlib import Path

from evennia.utils import logger

from typeclasses.system_alerts import ALERT_CATEGORIES, ALERT_SEVERITIES
from world.ambient_registry import replace_ambient_registry

_DEFAULT_JSON = Path(__file__).resolve().parent / "data" / "ambient_templates.json"

REQUIRED_KEYS = frozenset(
    {"id", "cadence", "weight", "cooldown_seconds", "severity", "category", "title", "detail"}
)
ALLOWED_CADENCE = frozenset({"tick", "strong"})


def _validate_row(raw: dict, index: int) -> tuple[dict | None, str | None]:
    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        return None, f"row {index}: missing keys {sorted(missing)}"
    cid = str(raw["id"]).strip()
    if not cid:
        return None, f"row {index}: empty id"
    cadence = str(raw["cadence"]).strip()
    if cadence not in ALLOWED_CADENCE:
        return None, f"row {index}: bad cadence {cadence!r}"
    sev = str(raw["severity"]).strip()
    if sev not in ALERT_SEVERITIES:
        sev = "info"
    cat = str(raw["category"]).strip()
    if cat not in ALERT_CATEGORIES:
        cat = "system"
    try:
        weight = max(1, int(raw["weight"]))
    except (TypeError, ValueError):
        weight = 1
    try:
        cooldown_seconds = max(0, int(raw["cooldown_seconds"]))
    except (TypeError, ValueError):
        cooldown_seconds = 0
    row = {
        "id": cid,
        "cadence": cadence,
        "weight": weight,
        "cooldown_seconds": cooldown_seconds,
        "severity": sev,
        "category": cat,
        "title": str(raw["title"]),
        "detail": str(raw.get("detail") or ""),
        "source": str(raw.get("source") or "ambient_world_engine"),
    }
    if int(raw.get("min_tick") or 0):
        row["min_tick"] = int(raw["min_tick"])
    return row, None


def rows_from_json(path: Path | None = None) -> tuple[list[dict], list[str]]:
    path = path or _DEFAULT_JSON
    if not path.is_file():
        return [], [f"ambient JSON not found: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], [f"ambient JSON parse error: {exc}"]
    if not isinstance(data, list):
        return [], ["ambient JSON root must be a list"]
    rows: list[dict] = []
    errors: list[str] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            errors.append(f"row {i}: not an object")
            continue
        row, err = _validate_row(raw, i)
        if err:
            errors.append(err)
            continue
        rows.append(row)
    return rows, errors


def index_by_cadence(rows: list[dict]) -> dict[str, tuple[dict, ...]]:
    tick: list[dict] = []
    strong: list[dict] = []
    for t in rows:
        if t["cadence"] == "tick":
            tick.append(t)
        else:
            strong.append(t)
    return {"tick": tuple(tick), "strong": tuple(strong)}


def load_ambient_from_json(path: Path | None = None) -> int:
    rows, errs = rows_from_json(path)
    by_c = index_by_cadence(rows)
    vids = frozenset(t["id"] for t in rows)
    ver = replace_ambient_registry(by_cadence=by_c, valid_ids=vids, errors=tuple(errs))
    logger.log_info(
        f"[ambient] registry v{ver} tick={len(by_c['tick'])} "
        f"strong={len(by_c['strong'])} errors={len(errs)}"
    )
    return ver


def bootstrap_ambient_registry_at_startup() -> None:
    """Call from at_server_start (and optionally after migrate)."""
    load_ambient_from_json()
