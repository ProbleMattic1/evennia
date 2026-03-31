"""
Load crime templates from JSON chunks; validate; build cadence buckets.
"""

from __future__ import annotations

from pathlib import Path

from evennia.utils import logger

from typeclasses.system_alerts import ALERT_SEVERITIES
from world.crime_registry import replace_crime_registry
from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_JSON = _DATA_DIR / "crime_templates.json"

REQUIRED_KEYS = frozenset(
    {
        "id",
        "cadence",
        "weight",
        "cooldown_seconds",
        "severity",
        "category",
        "title",
        "summary",
    }
)
def _normalize_crime_row(raw: dict, _ref: str) -> tuple[dict | None, str | None]:
    missing = REQUIRED_KEYS - raw.keys()
    if missing:
        return None, f"missing keys {sorted(missing)}"
    cid = str(raw["id"]).strip()
    if not cid:
        return None, "empty id"
    cadence = str(raw["cadence"]).strip()
    if cadence not in {"tick", "strong"}:
        return None, f"bad cadence {cadence!r}"
    sev = str(raw["severity"]).strip()
    if sev not in ALERT_SEVERITIES:
        sev = "info"
    cat = str(raw["category"]).strip().lower() or "general"
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
        "summary": str(raw.get("summary") or ""),
        "source": str(raw.get("source") or "crime_world_engine"),
        "broadcast": bool(raw.get("broadcast", False)),
    }
    if int(raw.get("min_tick") or 0):
        row["min_tick"] = int(raw["min_tick"])
    return row, None


def crime_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="crime.d",
        legacy_file=_DEFAULT_JSON,
    )


def index_by_cadence(rows: list[dict]) -> dict[str, tuple[dict, ...]]:
    tick: list[dict] = []
    strong: list[dict] = []
    for t in rows:
        if t["cadence"] == "tick":
            tick.append(t)
        else:
            strong.append(t)
    return {"tick": tuple(tick), "strong": tuple(strong)}


def load_crime_from_json(path: Path | None = None) -> int:
    paths = crime_source_paths(path)
    rows, errs = merge_validated_rows(paths, validate_row=_normalize_crime_row)
    by_c = index_by_cadence(rows)
    vids = frozenset(t["id"] for t in rows)
    ver = replace_crime_registry(by_cadence=by_c, valid_ids=vids, errors=tuple(errs))
    logger.log_info(
        f"[crime] registry v{ver} files={len(paths)} tick={len(by_c['tick'])} "
        f"strong={len(by_c['strong'])} errors={len(errs)}"
    )
    return ver


def bootstrap_crime_registry_at_startup() -> None:
    load_crime_from_json()
