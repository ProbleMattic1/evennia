"""
Load manufacturing catalog and recipe tables from chunked JSON (Phase 3).

Rows use ``table`` of ``catalog`` or ``recipe`` and an ``id`` (product/recipe key).
``merge_validated_rows`` dedupes on ``id``; we use composite keys ``catalog:<id>`` /
``recipe:<id>`` internally then split into MANUFACTURED_CATALOG / MANUFACTURING_RECIPES.
"""

from __future__ import annotations

from pathlib import Path

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CHUNK_DIR = "manufacturing.d"
_LEGACY = _DATA_DIR / "manufacturing_tables.json"


def _validate_row(raw: dict, ref: str) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "not an object"
    kind = str(raw.get("table") or "").strip().lower()
    if kind not in ("catalog", "recipe"):
        return None, f"unknown table {kind!r}"
    rid = str(raw.get("id") or "").strip()
    if not rid:
        return None, "missing id"
    composite_id = f"{kind}:{rid}"
    row = {
        "id": composite_id,
        "table": kind,
        "record_id": rid,
    }
    for k, v in raw.items():
        if k in ("table", "id"):
            continue
        row[k] = v
    return row, None


def load_manufacturing_tables() -> tuple[dict[str, dict], dict[str, dict], tuple[str, ...]]:
    paths = discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir=_CHUNK_DIR,
        legacy_file=_LEGACY,
    )
    rows, merge_errors = merge_validated_rows(paths, validate_row=_validate_row)
    catalog: dict[str, dict] = {}
    recipes: dict[str, dict] = {}
    errors = list(merge_errors)

    for row in rows:
        kind = row["table"]
        rid = row["record_id"]
        body = {k: v for k, v in row.items() if k not in ("id", "table", "record_id")}
        if kind == "catalog":
            catalog[rid] = body
        else:
            recipes[rid] = body

    return catalog, recipes, tuple(errors)


def assert_manufacturing_recipes_use_refined_keys(catalog, recipes):
    from typeclasses.refining import REFINING_RECIPES

    for rid, row in recipes.items():
        assert rid in catalog
        inputs = row["inputs"]
        for inp in inputs:
            assert inp in REFINING_RECIPES, f"recipe {rid}: unknown input {inp!r}"
