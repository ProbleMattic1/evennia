"""
HTTP read model for the plant ``Refinery`` (main ``typeclasses.refining.Refinery`` only).

Excludes ``PortableProcessor`` — different typeclass. Used by ``/ui/refinery``.

Web payload omits refinery-wide pooled inventory snapshots; in-game feeding is from
the Processor (ore bay) or personal plant storage via ``feedrefinery``.
"""

from __future__ import annotations

from typing import Any

from typeclasses.refining import (
    PROCESSING_FEE_RATE,
    REFINERY_ENGINE_INTERVAL,
    REFINING_RECIPES,
    Refinery,
    plant_raw_resource_display_name,
    refined_payout_breakdown,
)
from web.ui.control_surface import _empty_personal_storage_payload, _serialize_personal_storage
from world.venue_resolve import processing_plant_room_for_object, processing_plant_room_for_venue


def serialize_refining_recipes_catalog() -> list[dict[str, Any]]:
    """Full ``REFINING_RECIPES`` as JSON rows for the UI."""
    rows: list[dict[str, Any]] = []
    for key in sorted(REFINING_RECIPES.keys(), key=str):
        recipe = REFINING_RECIPES[key]
        rows.append(
            {
                "key": key,
                "name": recipe.get("name", key),
                "desc": recipe.get("desc", "") or "",
                "inputs": {str(k): float(v) for k, v in (recipe.get("inputs") or {}).items()},
                "outputUnits": int(recipe.get("output_units", 1)),
                "baseValueCrPerUnit": int(recipe.get("base_value_cr", 0) or 0),
                "category": recipe.get("category", "") or "",
            }
        )
    return rows


def _iter_main_refineries_in_room(room):
    for o in getattr(room, "contents", []) or []:
        if o.is_typeclass(Refinery, exact=False):
            yield o


def _serialize_input_lines(inv_in: dict) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for key in sorted(inv_in.keys(), key=str):
        tons = float(inv_in.get(key) or 0.0)
        if tons <= 0:
            continue
        sk = str(key)
        lines.append(
            {
                "key": sk,
                "displayName": plant_raw_resource_display_name(sk),
                "tons": round(tons, 2),
            }
        )
    return lines


def _serialize_output_lines(inv_out: dict) -> tuple[list[dict[str, Any]], int]:
    lines: list[dict[str, Any]] = []
    total_cr = 0
    for key in sorted(inv_out.keys(), key=str):
        units = float(inv_out.get(key) or 0.0)
        if units <= 0:
            continue
        sk = str(key)
        recipe = REFINING_RECIPES.get(sk, {})
        bvc = int(recipe.get("base_value_cr", 0) or 0)
        line_cr = int(units * bvc)
        total_cr += line_cr
        lines.append(
            {
                "key": sk,
                "displayName": recipe.get("name", sk),
                "units": round(units, 2),
                "lineValueCr": line_cr,
            }
        )
    return lines, total_cr


def build_main_refinery_payload(room, *, char=None, venue_id: str | None = None) -> dict[str, Any] | None:
    """
    First ``Refinery`` in the plant room. Returns ``None`` if none present.

    Per-character queue, output, and collect preview only when ``char`` is set.
    """
    refineries = list(_iter_main_refineries_in_room(room))
    if not refineries:
        return None

    ref = refineries[0]
    recipes = serialize_refining_recipes_catalog()

    out: dict[str, Any] = {
        "plantName": room.key,
        "refineryKey": ref.key,
        "refineryCountInRoom": len(refineries),
        "recipes": recipes,
        "constants": {
            "processingFeeRate": float(PROCESSING_FEE_RATE),
            "refineryEngineIntervalSeconds": int(REFINERY_ENGINE_INTERVAL),
        },
        "myMinerOreQueueLines": None,
        "myMinerOutputLines": None,
        "collectPreview": None,
        "personalStorage": _empty_personal_storage_payload(),
        "refineryWebActionsAllowed": False,
    }
    if venue_id is not None:
        out["venueId"] = venue_id

    if char is not None:
        oid = str(char.id)
        q = dict((ref.db.miner_ore_queue or {}).get(oid, {}))
        out["myMinerOreQueueLines"] = _serialize_input_lines(q)
        mo = ref.get_miner_output(oid)
        mo_lines, _ = _serialize_output_lines(mo)
        out["myMinerOutputLines"] = mo_lines
        gross = ref.get_miner_output_value(char.id)
        out["collectPreview"] = refined_payout_breakdown(gross, PROCESSING_FEE_RATE)
        out["personalStorage"] = _serialize_personal_storage(char)
        if venue_id is not None:
            t = processing_plant_room_for_venue(venue_id)
            a = processing_plant_room_for_object(char)
            out["refineryWebActionsAllowed"] = bool(t and a and t.id == a.id)
        else:
            out["refineryWebActionsAllowed"] = False

    return out
