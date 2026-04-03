"""Static perk definitions for point-store perk resolution (server-only numbers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LEGACY = _DATA_DIR / "perk_defs.json"

_registry: dict[str, Any] = {
    "version": 0,
    "by_id": {},
    "errors": (),
}


def _normalize_perk_row(raw: dict, _ref: str) -> tuple[dict | None, str | None]:
    pid = str(raw.get("id") or "").strip()
    if not pid:
        return None, "empty id"
    row: dict[str, Any] = {
        "id": pid,
        "miningOutputMult": float(raw.get("miningOutputMult") or 1.0),
    }
    return row, None


def perk_def_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="perk_defs.d",
        legacy_file=_LEGACY,
    )


def load_perk_defs(path: Path | None = None) -> int:
    global _registry
    explicit = path
    if explicit is not None and not explicit.is_file():
        _registry = {
            "version": 0,
            "by_id": {},
            "errors": (f"file missing: {explicit}",),
        }
        return 0

    paths = perk_def_source_paths(path)
    templates, errors = merge_validated_rows(paths, validate_row=_normalize_perk_row)
    version = int(_registry.get("version") or 0) + 1
    _registry = {
        "version": version,
        "by_id": {row["id"]: row for row in templates},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[perk_defs] registry v{version} files={len(paths)} perks={len(templates)} errors={len(errors)}"
    )
    return version


def _ensure_loaded() -> None:
    if not _registry.get("by_id") and not _registry.get("errors"):
        load_perk_defs()


def get_perk_def(perk_id: str) -> dict | None:
    _ensure_loaded()
    return (_registry.get("by_id") or {}).get(str(perk_id or "").strip())


def perk_def_registry_errors() -> tuple[str, ...]:
    _ensure_loaded()
    return tuple(_registry.get("errors") or ())
