"""
Cadence challenge template loader.

Templates live in game/world/data/challenge_templates.json (legacy, kept for
single-file authoring) or game/world/data/challenges.d/*.json (preferred for
packs added per phase).

Required template keys: id, cadence, title, summary, predicateKey.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows
from world.time import VALID_CADENCES

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_JSON = _DATA_DIR / "challenge_templates.json"

_REQUIRED_KEYS = frozenset({"id", "cadence", "title", "summary", "predicateKey"})

_registry: dict[str, Any] = {
    "version": 0,
    "templates": (),
    "by_id": {},
    "by_cadence": {},
    "errors": (),
}


def _normalize_challenge_row(raw: dict, _ref: str) -> tuple[dict | None, str | None]:
    missing = _REQUIRED_KEYS - raw.keys()
    if missing:
        return None, f"missing keys {sorted(missing)}"

    cid = str(raw.get("id") or "").strip()
    if not cid:
        return None, "empty id"

    cadence = str(raw.get("cadence") or "").strip().lower()
    if cadence not in VALID_CADENCES:
        return None, f"unsupported cadence {cadence!r}; valid: {sorted(VALID_CADENCES)}"

    predicate_key = str(raw.get("predicateKey") or "").strip()
    if not predicate_key:
        return None, "empty predicateKey"

    row: dict[str, Any] = {
        "id": cid,
        "cadence": cadence,
        "title": str(raw.get("title") or cid),
        "summary": str(raw.get("summary") or ""),
        "predicateKey": predicate_key,
        "predicateParams": dict(raw.get("predicateParams") or {}),
        "rewards": dict(raw.get("rewards") or {}),
        "eligibility": {
            "once": bool((raw.get("eligibility") or {}).get("once", False)),
            "requiresTags": list((raw.get("eligibility") or {}).get("requiresTags") or []),
        },
        "requiresTelemetry": list(raw.get("requiresTelemetry") or []),
        "weekdayOnly": raw.get("weekdayOnly"),  # 0=Mon..6=Sun or None
        "enabled": bool(raw.get("enabled", True)),
        "missionUnlockIds": list(raw.get("missionUnlockIds") or []),
    }
    return row, None


def challenge_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="challenges.d",
        legacy_file=_DEFAULT_JSON,
    )


def load_challenge_templates(path: Path | None = None) -> int:
    global _registry
    explicit = path
    if explicit is not None and not explicit.is_file():
        _registry = {
            "version": 0,
            "templates": (),
            "by_id": {},
            "by_cadence": {},
            "errors": (f"file missing: {explicit}",),
        }
        return 0

    paths = challenge_source_paths(path)
    templates, errors = merge_validated_rows(paths, validate_row=_normalize_challenge_row)
    version = int(_registry.get("version") or 0) + 1

    by_cadence: dict[str, list[dict]] = {}
    for row in templates:
        by_cadence.setdefault(row["cadence"], []).append(row)

    _registry = {
        "version": version,
        "templates": tuple(templates),
        "by_id": {row["id"]: row for row in templates},
        "by_cadence": {c: tuple(rows) for c, rows in by_cadence.items()},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[challenges] registry v{version} files={len(paths)} "
        f"templates={len(templates)} errors={len(errors)}"
    )
    return version


def _ensure_loaded() -> None:
    if not _registry.get("templates") and not _registry.get("errors"):
        load_challenge_templates()


def all_challenge_templates() -> tuple[dict, ...]:
    _ensure_loaded()
    return tuple(_registry.get("templates") or ())


def get_challenge_template(template_id: str) -> dict | None:
    _ensure_loaded()
    return (_registry.get("by_id") or {}).get(str(template_id or "").strip())


def challenges_for_cadence(cadence: str) -> tuple[dict, ...]:
    _ensure_loaded()
    return tuple((_registry.get("by_cadence") or {}).get(cadence) or ())


def challenge_registry_errors() -> tuple[str, ...]:
    _ensure_loaded()
    return tuple(_registry.get("errors") or ())


def challenge_registry_version() -> int:
    return int(_registry.get("version") or 0)
