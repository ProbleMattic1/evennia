"""
Property parcel manufacturing — web API helpers (Phase 4).

Mirrors in-game workshop rules: deed on character inventory, titled holding owner.
"""

from __future__ import annotations

from evennia import search_object

from commands.manufacturing import (
    _refined_sources_for_feed,
    _refined_sources_on_holding_only,
    _withdraw_refined_units,
)
from typeclasses.manufacturing import MANUFACTURING_RECIPES, Workshop, job_queue_for_json
from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG


def resolve_claim_holding_workshop(char, claim_id: int, workshop_id: int):
    found = search_object("#" + str(int(claim_id)))
    assert found
    claim = found[0]
    assert claim.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
    assert claim.location == char
    lot = getattr(claim.db, "lot_ref", None)
    assert lot
    holding = getattr(lot.db, "holding_ref", None)
    assert holding
    assert holding.db.title_owner == char
    ws_found = search_object("#" + str(int(workshop_id)))
    assert ws_found
    ws = ws_found[0]
    assert ws.is_typeclass(Workshop, exact=False)
    assert ws.location == holding
    return holding, ws


def web_queue_job(char, claim_id: int, workshop_id: int, recipe_key: str, runs: int):
    _holding, ws = resolve_claim_holding_workshop(char, claim_id, workshop_id)
    recipe_key = str(recipe_key).strip()
    assert recipe_key in MANUFACTURING_RECIPES
    ws.queue_job(char, recipe_key, int(runs))
    return {"ok": True, "jobQueue": job_queue_for_json(ws.db.job_queue)}


def web_feed(
    char,
    claim_id: int,
    workshop_id: int,
    product_key: str,
    units: float,
    *,
    holding_sources_only: bool = False,
):
    holding, ws = resolve_claim_holding_workshop(char, claim_id, workshop_id)
    pk = str(product_key).strip()
    total = 0.0
    if holding_sources_only:
        sources = _refined_sources_on_holding_only(holding, char)
    else:
        sources = _refined_sources_for_feed(holding, char.location, char)
    for src in sources:
        chunk = _withdraw_refined_units(src, pk, float(units) - total)
        if chunk:
            total += ws.feed(pk, chunk)
        if total + 1e-6 >= float(units):
            break
    assert total > 0
    return {
        "ok": True,
        "fedUnits": total,
        "inputInventory": dict(ws.db.input_inventory or {}),
    }


def web_collect(char, claim_id: int, workshop_id: int, product_key: str | None):
    _holding, ws = resolve_claim_holding_workshop(char, claim_id, workshop_id)
    if not product_key:
        outs = dict(ws.db.output_inventory or {})
        assert outs
        total_cr = 0
        for pk in list(outs.keys()):
            _u, v = ws.collect_manufactured(char, pk, None)
            total_cr += v
        return {
            "ok": True,
            "credits": total_cr,
            "outputInventory": dict(ws.db.output_inventory or {}),
        }
    pk = str(product_key).strip()
    assert pk in (ws.db.output_inventory or {})
    u, v = ws.collect_manufactured(char, pk, None)
    return {
        "ok": True,
        "units": u,
        "credits": v,
        "outputInventory": dict(ws.db.output_inventory or {}),
    }
