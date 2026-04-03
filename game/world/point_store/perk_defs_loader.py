"""Static perk definitions for point-store perk resolution (server-only numbers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LEGACY = _DATA_DIR / "perk_defs.json"

# (json_key, min_inclusive, max_inclusive)
_MECHANIC_FLOAT_KEYS: tuple[tuple[str, float, float], ...] = (
    ("miningOutputMult", 0.05, 5.0),
    ("processingFeeMult", 0.05, 2.0),
    ("rawSaleFeeMult", 0.05, 2.0),
    ("extractionTaxMult", 0.05, 2.0),
    ("miningDepletionMult", 0.05, 1.0),
    ("hazardRaidStealMult", 0.05, 1.0),
    ("hazardGeoFloorMult", 0.05, 1.0),
    ("rigWearGainMult", 0.05, 1.0),
    ("missionCreditsMult", 0.05, 5.0),
    ("challengePointsMult", 0.05, 5.0),
    ("challengeCreditsMult", 0.05, 5.0),
    ("refiningBatchOutputMult", 0.05, 5.0),
    ("rigRepairCostMult", 0.05, 2.0),
    ("propertyIncidentBonusMult", 0.05, 5.0),
    ("miningLicenseFeeMult", 0.05, 2.0),
)

_registry: dict[str, Any] = {
    "version": 0,
    "by_id": {},
    "errors": (),
}


def _float_field(raw: dict, key: str, lo: float, hi: float, ref: str) -> tuple[float | None, str | None]:
    if key not in raw:
        return 1.0, None
    try:
        v = float(raw[key])
    except (TypeError, ValueError):
        return None, f"{ref}: {key} must be a number"
    if v < lo or v > hi:
        return None, f"{ref}: {key} must be between {lo} and {hi}, got {v}"
    return v, None


def _normalize_perk_row(raw: dict, ref: str) -> tuple[dict | None, str | None]:
    pid = str(raw.get("id") or "").strip()
    if not pid:
        return None, "empty id"
    title = str(raw.get("title") or "").strip()
    summary = str(raw.get("summary") or "").strip()
    row: dict[str, Any] = {
        "id": pid,
        "title": title or pid,
        "summary": summary,
    }
    for key, lo, hi in _MECHANIC_FLOAT_KEYS:
        val, err = _float_field(raw, key, lo, hi, ref)
        if err:
            return None, err
        row[key] = float(val)
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
    return tuple(_registry.get("errors") or [])
