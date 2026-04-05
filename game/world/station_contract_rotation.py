"""
Rotation pool for ``StationContractsScript`` — JSON under ``world/data/station_contracts.d/``.
"""

from __future__ import annotations

from pathlib import Path

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY = _DATA_DIR / "station_contracts_rotation.json"
_CHUNK_SUBDIR = "station_contracts.d"

_CORE_CONTRACTS: list[dict] = [
    {
        "id": "PKG-001",
        "title": "List a mining package at this venue",
        "payout": 500,
        "predicate_key": "list_package",
        "venue_id": "nanomega_core",
    },
    {
        "id": "REF-001",
        "title": "Collect refined output at the processing plant",
        "payout": 350,
        "predicate_key": "refine_collect",
        "venue_id": None,
    },
    {
        "id": "CLM-001",
        "title": "List a mining claim deed at this venue",
        "payout": 400,
        "predicate_key": "list_claim",
        "venue_id": "nanomega_core",
    },
    {
        "id": "PDE-001",
        "title": "List a property deed at this venue",
        "payout": 400,
        "predicate_key": "list_property_deed",
        "venue_id": "nanomega_core",
    },
]

_REQUIRED = frozenset({"id", "title", "payout", "predicate_key"})


def _validate_row(raw: dict, ref: str) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, f"{ref}: not an object"
    missing = _REQUIRED - raw.keys()
    if missing:
        return None, f"{ref}: missing {sorted(missing)}"
    cid = str(raw["id"]).strip()
    if not cid:
        return None, f"{ref}: empty id"
    row = {
        "id": cid,
        "title": str(raw["title"] or "").strip(),
        "payout": int(raw["payout"] or 0),
        "predicate_key": str(raw["predicate_key"] or "").strip(),
        "venue_id": raw.get("venue_id"),
    }
    if row["venue_id"] is not None:
        row["venue_id"] = str(row["venue_id"]).strip() or None
    return row, None


def core_station_contracts() -> list[dict]:
    return [dict(c) for c in _CORE_CONTRACTS]


def rotation_source_paths() -> list[Path]:
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir=_CHUNK_SUBDIR,
        legacy_file=_LEGACY,
    )


def load_rotation_pool() -> list[dict]:
    paths = rotation_source_paths()
    if not paths:
        return []
    rows, errors = merge_validated_rows(paths, validate_row=_validate_row)
    if errors:
        from evennia.utils import logger

        for e in errors[:20]:
            logger.log_warn(f"[station_contract_rotation] {e}")
    return list(rows)


def pick_rotating_contracts(
    pool: list[dict],
    rotation_index: int,
    *,
    count: int = 2,
    occupied_ids: set[str],
) -> list[dict]:
    """
    Pick ``count`` contracts from pool by round-robin, skipping ids in ``occupied_ids``.
    """
    if not pool or count <= 0:
        return []
    n = len(pool)
    out: list[dict] = []
    seen: set[str] = set(occupied_ids)
    for i in range(n):
        row = pool[(rotation_index + i) % n]
        cid = row["id"]
        if cid in seen:
            continue
        seen.add(cid)
        out.append(dict(row))
        if len(out) >= count:
            break
    return out


def build_visible_contracts(
    *,
    rotation_index: int,
    previous_contracts: list[dict],
    in_flight_ids: set[str],
) -> tuple[list[dict], int]:
    """
    Merge core, in-flight non-core rows still needed for completion, and fresh rotation slice.
    Returns (new_contracts_list, next_rotation_index).
    """
    core = core_station_contracts()
    core_ids = {c["id"] for c in core}
    pool = load_rotation_pool()

    prev_by_id = {c["id"]: c for c in previous_contracts if isinstance(c, dict) and c.get("id")}
    preserved: list[dict] = []
    for cid in in_flight_ids:
        if cid in core_ids:
            continue
        if cid in prev_by_id:
            preserved.append(dict(prev_by_id[cid]))

    occupied = set(core_ids) | {c["id"] for c in preserved}
    fresh = pick_rotating_contracts(pool, rotation_index, count=2, occupied_ids=occupied)

    merged: dict[str, dict] = {}
    for c in core + preserved + fresh:
        merged[c["id"]] = dict(c)
    ordered = core + preserved + fresh
    final: list[dict] = []
    seen: set[str] = set()
    for c in ordered:
        cid = c["id"]
        if cid in seen:
            continue
        seen.add(cid)
        final.append(merged[cid])
    return final, rotation_index + 1
