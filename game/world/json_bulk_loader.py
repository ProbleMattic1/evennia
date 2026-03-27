"""
Merge multiple JSON list files for bulk game data (ambient, missions).

Evennia runs a single server process; loading many small JSON files at startup
is cheap and keeps git history and authoring sane.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def discover_chunk_paths(
    *,
    data_dir: Path,
    chunk_subdir: str,
    legacy_file: Path,
) -> list[Path]:
    """
    Resolve JSON sources: ``data_dir/chunk_subdir/*.json`` (sorted), then
    ``legacy_file`` if it exists.
    """
    chunk_dir = data_dir / chunk_subdir
    paths: list[Path] = []
    if chunk_dir.is_dir():
        paths.extend(sorted(chunk_dir.glob("*.json")))
    if legacy_file.is_file():
        paths.append(legacy_file)
    return paths


def load_json_list_file(path: Path) -> tuple[list | None, str | None]:
    if not path.is_file():
        return None, f"file not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{path.name}: parse error: {exc}"
    if not isinstance(data, list):
        return None, f"{path.name}: root must be a list"
    return data, None


def merge_validated_rows(
    paths: list[Path],
    *,
    validate_row: Callable[[dict, str], tuple[dict | None, str | None]],
) -> tuple[list[dict], list[str]]:
    """
    Load each path as a JSON array; validate each object; detect duplicate ``id``.

    ``validate_row(raw, ref)`` — ref is ``"{file.name} row {i}"``.
    """
    rows: list[dict] = []
    errors: list[str] = []
    seen_id: dict[str, str] = {}

    if not paths:
        return [], ["no JSON source files configured"]

    for path in paths:
        data, err = load_json_list_file(path)
        if err:
            errors.append(err)
            continue
        assert data is not None
        for i, raw in enumerate(data):
            ref = f"{path.name} row {i}"
            if not isinstance(raw, dict):
                errors.append(f"{ref}: not an object")
                continue
            row, row_err = validate_row(raw, ref)
            if row_err:
                errors.append(f"{ref}: {row_err}")
                continue
            assert row is not None
            rid = str(row.get("id") or "").strip()
            if not rid:
                errors.append(f"{ref}: validated row missing id")
                continue
            prev = seen_id.get(rid)
            if prev:
                errors.append(f"duplicate id {rid!r}: first in {prev}, also in {path.name}")
                continue
            seen_id[rid] = path.name
            rows.append(row)

    return rows, errors
