"""
Point-offer catalog for challenge point purchases.

Templates live in game/world/data/point_offers.d/*.json (list of objects).

Required keys: id, category, title, summary, effect.
Pricing: at least one of costLifetime, costSeason must be > 0.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LEGACY = _DATA_DIR / "point_offers.json"

_VALID_CATEGORIES = frozenset({
    "trait_step",
    "perk_slot",
    "perk_grant",
    "mission_access",
    "unlock_tag",
    "license",
    "refining",
    "compound",
})

_registry: dict[str, Any] = {
    "version": 0,
    "templates": (),
    "by_id": {},
    "errors": (),
}


def _normalize_point_offer_row(raw: dict, _ref: str) -> tuple[dict | None, str | None]:
    oid = str(raw.get("id") or "").strip()
    if not oid:
        return None, "empty id"

    cat = str(raw.get("category") or "").strip().lower()
    if cat not in _VALID_CATEGORIES:
        return None, f"unsupported category {cat!r}; valid: {sorted(_VALID_CATEGORIES)}"

    title = str(raw.get("title") or oid).strip()
    summary = str(raw.get("summary") or "")

    try:
        cost_life = max(0, int(raw.get("costLifetime") or 0))
    except (TypeError, ValueError):
        return None, "costLifetime must be int"
    try:
        cost_season = max(0, int(raw.get("costSeason") or 0))
    except (TypeError, ValueError):
        return None, "costSeason must be int"
    if cost_life <= 0 and cost_season <= 0:
        return None, "at least one of costLifetime, costSeason must be > 0"

    effect = raw.get("effect")
    if not isinstance(effect, dict) or not str(effect.get("type") or "").strip():
        return None, "effect must be an object with non-empty type"

    prereq = [str(x).strip() for x in list(raw.get("prerequisiteOfferIds") or []) if str(x).strip()]
    try:
        max_purch = raw.get("maxPurchasesPerCharacter")
        max_purchases = None if max_purch is None else max(1, int(max_purch))
    except (TypeError, ValueError):
        return None, "maxPurchasesPerCharacter must be int or null"

    season_offer = str(raw.get("seasonId") or "").strip() or None

    row: dict[str, Any] = {
        "id": oid,
        "category": cat,
        "title": title,
        "summary": summary,
        "costLifetime": cost_life,
        "costSeason": cost_season,
        "prerequisiteOfferIds": prereq,
        "maxPurchasesPerCharacter": max_purchases,
        "seasonId": season_offer,
        "effect": dict(effect),
        "enabled": bool(raw.get("enabled", True)),
    }
    return row, None


def point_offer_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="point_offers.d",
        legacy_file=_LEGACY,
    )


def load_point_offers(path: Path | None = None) -> int:
    global _registry
    explicit = path
    if explicit is not None and not explicit.is_file():
        _registry = {
            "version": 0,
            "templates": (),
            "by_id": {},
            "errors": (f"file missing: {explicit}",),
        }
        return 0

    paths = point_offer_source_paths(path)
    templates, errors = merge_validated_rows(paths, validate_row=_normalize_point_offer_row)
    version = int(_registry.get("version") or 0) + 1
    _registry = {
        "version": version,
        "templates": tuple(templates),
        "by_id": {row["id"]: row for row in templates},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[point_offers] registry v{version} files={len(paths)} "
        f"offers={len(templates)} errors={len(errors)}"
    )
    return version


def _ensure_loaded() -> None:
    if not _registry.get("templates") and not _registry.get("errors"):
        load_point_offers()


def all_point_offers() -> tuple[dict, ...]:
    _ensure_loaded()
    return tuple(_registry.get("templates") or ())


def get_point_offer(offer_id: str) -> dict | None:
    _ensure_loaded()
    return (_registry.get("by_id") or {}).get(str(offer_id or "").strip())


def point_offer_registry_errors() -> tuple[str, ...]:
    _ensure_loaded()
    return tuple(_registry.get("errors") or ())


def point_offer_registry_version() -> int:
    return int(_registry.get("version") or 0)


def serialize_offer_for_web(row: dict) -> dict[str, Any]:
    """Public slice (no effect payload)."""
    return {
        "id": row["id"],
        "category": row["category"],
        "title": row["title"],
        "summary": row["summary"],
        "costLifetime": int(row["costLifetime"] or 0),
        "costSeason": int(row["costSeason"] or 0),
        "prerequisiteOfferIds": list(row.get("prerequisiteOfferIds") or []),
        "seasonId": row.get("seasonId"),
        "enabled": bool(row.get("enabled", True)),
    }
