"""
Portable ore processor — web API helpers.

Deploy targets the deed's PropertyHolding root interior (claim-scoped).
"""

from __future__ import annotations

from evennia import search_object

from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
from typeclasses.property_places import open_property_shell, resolve_property_root_room
from typeclasses.processors import PortableProcessor
from typeclasses.refining import REFINING_RECIPES, is_plant_raw_resource_key


class ProcessorWebError(Exception):
    """User-visible failure; view maps to 400 + message."""


def portable_processors_carried_for_json(char):
    """Processors in character inventory (O(inventory)); for property detail GET."""
    if not char:
        return []
    out = []
    for o in char.contents:
        if o.is_typeclass(PortableProcessor, exact=False):
            out.append(
                {
                    "id": o.id,
                    "key": o.key,
                    "mk": int(getattr(o.db, "processor_mk", 1) or 1),
                }
            )
    return out


def portable_processors_deployed_for_json(holding, char):
    """Portable processors in parcel root interior owned by char."""
    if not holding or not char:
        return []
    room = resolve_property_root_room(holding)
    if not room:
        return []
    out = []
    for o in room.contents:
        if not o.is_typeclass(PortableProcessor, exact=False):
            continue
        if getattr(o.db, "owner", None) != char:
            continue
        inv = o.db.input_inventory or {}
        out_inv = o.db.output_inventory or {}
        input_tons = round(sum(float(v) for v in inv.values()), 2)
        out_val = 0
        for pk, units in out_inv.items():
            rec = REFINING_RECIPES.get(pk, {})
            out_val += int(float(units) * rec.get("base_value_cr", 0))
        out.append(
            {
                "id": o.id,
                "key": o.key,
                "mk": int(getattr(o.db, "processor_mk", 1) or 1),
                "capacityTons": float(getattr(o.db, "capacity_tons", 200.0) or 200.0),
                "efficiency": float(getattr(o.db, "efficiency", 1.0) or 1.0),
                "inputTons": input_tons,
                "inputInventory": dict(inv),
                "outputInventory": dict(out_inv),
                "outputValueCr": out_val,
                "isInstalled": bool(getattr(o.db, "is_installed", False)),
            }
        )
    return out


def _resolve_portable_processor_by_id(processor_id: int):
    found = search_object("#" + str(int(processor_id)))
    if not found:
        raise ProcessorWebError("Processor not found.")
    obj = found[0]
    if not obj.is_typeclass(PortableProcessor, exact=False):
        raise ProcessorWebError("That is not a portable processor.")
    return obj


def _processor_on_claim_interior(char, claim_id: int, processor_id: int):
    _, holding = _resolve_claim_holding_for_owner(char, claim_id)
    room = resolve_property_root_room(holding)
    if not room:
        raise ProcessorWebError("Could not resolve parcel interior.")
    proc = _resolve_portable_processor_by_id(processor_id)
    if proc.location != room:
        raise ProcessorWebError("That processor is not deployed on this parcel.")
    if getattr(proc.db, "owner", None) != char:
        raise ProcessorWebError("That processor is not yours.")
    return holding, room, proc


def _resolve_owned_processor_in_inventory(char, processor_id: int):
    found = search_object("#" + str(int(processor_id)))
    if not found:
        raise ProcessorWebError("Processor not found.")
    obj = found[0]
    if not obj.is_typeclass(PortableProcessor, exact=False):
        raise ProcessorWebError("That is not a portable processor.")
    if obj.location != char:
        raise ProcessorWebError("You are not carrying that processor.")
    owner = getattr(obj.db, "owner", None)
    if owner is not None and owner != char:
        raise ProcessorWebError("That processor is not yours.")
    return obj


def _resolve_claim_holding_for_owner(char, claim_id: int):
    """Deed on character → lot → holding; title must match (same spirit as structure install)."""
    found = search_object("#" + str(int(claim_id)))
    if not found:
        raise ProcessorWebError("Property claim not found.")
    claim = found[0]
    if not claim.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY):
        raise ProcessorWebError("Property claim not found.")
    if claim.location != char:
        raise ProcessorWebError("You are not carrying that deed.")
    lot = getattr(claim.db, "lot_ref", None)
    if not lot:
        raise ProcessorWebError("That deed is not linked to a parcel.")
    holding = getattr(lot.db, "holding_ref", None)
    if not holding:
        raise ProcessorWebError("No development record exists for that parcel.")
    if getattr(holding.db, "title_owner", None) != char:
        raise ProcessorWebError("This is not your titled parcel.")
    return claim, holding


def web_deploy_portable_processor(char, claim_id: int, processor_id: int):
    """
    Place processor in this deed's parcel root interior.
    Does not move the character (web UX); optional: open shell if still void.
    """
    _, holding = _resolve_claim_holding_for_owner(char, claim_id)
    proc = _resolve_owned_processor_in_inventory(char, processor_id)

    st = dict(holding.db.place_state or {})
    if st.get("mode") == "void":
        open_property_shell(holding)

    room = resolve_property_root_room(holding)
    if not room:
        raise ProcessorWebError("Could not resolve parcel interior.")

    if proc.location == room:
        return {
            "ok": True,
            "message": "Processor is already deployed in this parcel interior.",
            "processorId": proc.id,
            "roomKey": room.key,
        }

    proc.move_to(room, quiet=True)
    proc.db.is_installed = True

    loc = getattr(char, "location", None)
    if loc and loc == room:
        char.msg(f"You deploy {proc.key} in {room.key}.")
    else:
        char.msg(
            f"You install {proc.key} in your parcel interior ({room.key}). "
            f"Use visitproperty when you want to be there in person."
        )

    return {
        "ok": True,
        "message": f"Deployed {proc.key} to {room.key}.",
        "processorId": proc.id,
        "roomKey": room.key,
    }


def web_processor_status(char, claim_id: int, processor_id: int):
    _, _, proc = _processor_on_claim_interior(char, claim_id, processor_id)
    return {
        "ok": True,
        "report": proc.get_status_report(),
        "processorId": proc.id,
    }


def web_processor_feed(char, claim_id: int, processor_id: int, resource_key: str, tons: float):
    _, _, proc = _processor_on_claim_interior(char, claim_id, processor_id)
    rk = str(resource_key).strip()
    if not is_plant_raw_resource_key(rk):
        raise ProcessorWebError("Unknown resource.")
    actual = proc.feed(rk, float(tons))
    if actual <= 0:
        raise ProcessorWebError("Nothing fed (check capacity or amount).")
    return {
        "ok": True,
        "fedTons": actual,
        "resourceKey": rk,
        "inputInventory": dict(proc.db.input_inventory or {}),
    }


def web_processor_refine(char, claim_id: int, processor_id: int, recipe_key: str, batches: int = 1):
    _, _, proc = _processor_on_claim_interior(char, claim_id, processor_id)
    key = str(recipe_key).strip()
    if key not in REFINING_RECIPES:
        raise ProcessorWebError("Unknown recipe.")
    n, msg = proc.process_recipe(key, max(1, int(batches)))
    if n <= 0:
        raise ProcessorWebError(msg)
    char.msg(msg)
    return {
        "ok": True,
        "message": msg,
        "batches": n,
        "outputInventory": dict(proc.db.output_inventory or {}),
    }


def web_processor_collect(char, claim_id: int, processor_id: int, product_key: str | None):
    from typeclasses.economy import grant_character_credits

    _, _, proc = _processor_on_claim_interior(char, claim_id, processor_id)
    pk = str(product_key).strip() if product_key else None
    total = 0
    if pk:
        collected, value = proc.collect_product(pk)
        if collected <= 0:
            raise ProcessorWebError("Nothing to collect for that product.")
        grant_character_credits(char, value, memo=f"Portable processor output {proc.key}")
        total = value
    else:
        out_keys = list((proc.db.output_inventory or {}).keys())
        if not out_keys:
            raise ProcessorWebError("Output bin is empty.")
        for key in out_keys:
            collected, value = proc.collect_product(key)
            if collected > 0:
                grant_character_credits(char, value, memo=f"Portable processor output {proc.key}")
                total += value
        if total <= 0:
            raise ProcessorWebError("Nothing was collected.")
    return {
        "ok": True,
        "credits": total,
        "balanceCr": int(char.db.credits or 0),
        "outputInventory": dict(proc.db.output_inventory or {}),
    }
