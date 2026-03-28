"""
Player-facing property operation rules (web + in-game commands).

Single source for zone ↔ kind validation vs OPERATION_HANDLERS.
CamelCase serializer for UI (property detail / start-operation response).
"""

from typeclasses.property_claim_market import (
    collect_property_construction_payment,
    get_construction_builder,
    refund_property_construction_payment,
)
from typeclasses.property_development import (
    install_structure,
    next_extra_structure_slot_price_cr,
    purchase_extra_structure_slot,
    retool_operation,
    set_operation_paused,
    start_operation,
)
from typeclasses.property_structure_upgrades import purchase_structure_upgrade
from typeclasses.property_holdings import PROPERTY_HOLDING_CATEGORY, PROPERTY_HOLDING_TAG
from typeclasses.property_operation_handlers import OPERATION_HANDLERS
from typeclasses.property_transfer_fee import PROPERTY_DEED_TRANSFER_FEE_CR
from typeclasses.economy import get_economy
from world.property_incident_templates import trim_property_event_queue
from world.property_structure_catalog import catalog_row_by_id, catalog_rows_for_zone
from world.property_structure_upgrade_registry import STRUCTURE_UPGRADE_DEFS
from world.time import to_iso, utc_now

RETOOL_FEE_CR = 1000

DEFAULT_KIND_BY_ZONE = {
    "residential": "rent",
    "commercial": "floor",
    "industrial": "line",
}


def normalized_zone(holding):
    return (holding.db.zone or "residential").lower()


def resolve_kind_for_holding(holding, kind_explicit: str | None):
    """
    Returns (kind: str | None, error_message: str | None).
    If kind_explicit is None, use DEFAULT_KIND_BY_ZONE.
    """
    zone = normalized_zone(holding)
    if kind_explicit:
        k = kind_explicit.strip().lower()
        if (zone, k) not in OPERATION_HANDLERS:
            return None, f"Operation {k!r} is not valid for a {zone} parcel."
        return k, None
    k = DEFAULT_KIND_BY_ZONE.get(zone)
    if (zone, k) not in OPERATION_HANDLERS:
        return None, f"No default operation for zone {zone!r}."
    return k, None


def start_property_operation_for_owner(owner, holding, *, kind_explicit: str | None):
    """
    Returns (success: bool, message: str).
    """
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."

    op = holding.db.operation or {}
    if op.get("kind"):
        return False, "This parcel already has an active operation type set."

    kind, err = resolve_kind_for_holding(holding, kind_explicit)
    if err:
        return False, err

    start_operation(holding, kind=kind)
    return True, f"Started {kind} income for your {normalized_zone(holding)} parcel."


def purchase_and_install_structure(owner, holding, blueprint_id):
    """
    Charge catalog price and install a structure on the holding.
    Returns (success: bool, message: str, structure_or_none).
    """
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel.", None

    zone = normalized_zone(holding)
    row = catalog_row_by_id(blueprint_id)
    if not row or zone not in row["zones"]:
        return False, "That blueprint is not available for this parcel.", None

    slot_w = int(row["slotWeight"])
    if not holding.can_install(slot_w):
        return False, "Not enough structure capacity on this parcel.", None

    price = int(row["priceCr"])
    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(owner)
    econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
    balance = econ.get_character_balance(owner)
    if balance < price:
        return False, f"You need {price:,} cr but only have {balance:,} cr.", None

    builder = get_construction_builder()
    net_amount = tax_amount = None
    if builder:
        net_amount, tax_amount = collect_property_construction_payment(
            owner,
            price,
            builder,
            tx_type="property_structure_install",
            withdraw_memo=f"property structure {row['id']}",
            record_memo=f"{owner.key} structure {row['id']}",
        )
    else:
        econ.withdraw(acct, price, memo=f"property structure {row['id']}")
        owner.db.credits = econ.get_character_balance(owner)

    try:
        st = install_structure(holding, row["id"], slot_weight=slot_w)
    except Exception:
        if builder and net_amount is not None:
            refund_property_construction_payment(
                owner, price, builder, net_amount=net_amount, tax_amount=tax_amount
            )
        else:
            econ.deposit(acct, price, memo="Refund: structure install failed")
            owner.db.credits = econ.get_character_balance(owner)
        return False, "Structure install failed; payment refunded.", None

    if not builder:
        owner.db.credits = econ.get_character_balance(owner)
    return True, f"Installed {row['name']} ({row['id']}).", st


def serialize_structure_upgrade_catalog_for_web():
    out = []
    for key, d in STRUCTURE_UPGRADE_DEFS.items():
        costs = d["level_cost_cr"]
        allowed = d.get("allowed_blueprint_ids")
        out.append(
            {
                "upgradeKey": key,
                "maxLevel": int(d["max_level"]),
                "levelCostCr": {str(lvl): int(cr) for lvl, cr in sorted(costs.items())},
                "allowedBlueprintIds": list(allowed) if allowed is not None else None,
            }
        )
    return out


def purchase_structure_upgrade_for_owner(owner, holding, structure_id, upgrade_key):
    return purchase_structure_upgrade(owner, holding, structure_id, upgrade_key)


def purchase_extra_structure_slot_for_owner(owner, holding):
    return purchase_extra_structure_slot(holding, owner)


def pause_property_operation_for_owner(owner, holding, paused):
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."
    op = holding.db.operation or {}
    if not op.get("kind"):
        return False, "No active operation to pause or resume."
    set_operation_paused(holding, paused)
    state = "paused" if paused else "resumed"
    return True, f"Income operation {state}."


def retool_property_operation_for_owner(owner, holding, new_kind):
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(owner)
    econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
    balance = econ.get_character_balance(owner)
    if balance < RETOOL_FEE_CR:
        return False, f"You need {RETOOL_FEE_CR:,} cr to retool but only have {balance:,} cr."

    ok, msg = retool_operation(holding, new_kind)
    if not ok:
        return False, msg

    builder = get_construction_builder()
    if builder:
        collect_property_construction_payment(
            owner,
            RETOOL_FEE_CR,
            builder,
            tx_type="property_operation_retool",
            withdraw_memo="property operation retool",
            record_memo=f"{owner.key} property retool",
        )
    else:
        econ.withdraw(acct, RETOOL_FEE_CR, memo="property operation retool")
        owner.db.credits = econ.get_character_balance(owner)
    return True, msg


def resolve_property_incident_for_owner(owner, holding, event_id: str):
    """
    Mark an incident resolved; charge flat_cost_cr on resolve when effects require it.
    Returns (success: bool, message: str).
    """
    if holding.db.title_owner != owner:
        return False, "You are not the titled owner of this parcel."
    eid = (event_id or "").strip()
    if not eid:
        return False, "No incident id given."

    q = list(holding.db.event_queue or [])
    now = utc_now()
    for e in q:
        if e.get("id") != eid:
            continue
        if e.get("resolved"):
            return False, "That incident is already resolved."
        effects = dict(e.get("effects") or {})
        if effects.get("kind") == "flat_cost":
            cost = int(effects.get("flat_cost_cr") or 0)
            if cost > 0:
                econ = get_economy(create_missing=True)
                acct = econ.get_character_account(owner)
                econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
                balance = econ.get_character_balance(owner)
                if balance < cost:
                    return False, f"You need {cost:,} cr to resolve this incident but only have {balance:,} cr."
                builder = get_construction_builder()
                if builder:
                    collect_property_construction_payment(
                        owner,
                        cost,
                        builder,
                        tx_type="property_incident_resolve",
                        withdraw_memo=f"property incident resolve ({e.get('template_id') or eid})",
                        record_memo=f"{owner.key} incident {eid}",
                    )
                else:
                    econ.withdraw(
                        acct,
                        cost,
                        memo=f"property incident resolve ({e.get('template_id') or eid})",
                    )
                    owner.db.credits = econ.get_character_balance(owner)
        e["resolved"] = True
        e["resolved_at_iso"] = to_iso(now)
        holding.db.event_queue = trim_property_event_queue(q)
        return True, f"Resolved: {e.get('title') or eid}."
    return False, "No incident with that id on this parcel."


def _serialize_incident_for_web(raw):
    e = dict(raw) if isinstance(raw, dict) else {}
    eff = dict(e.get("effects") or {})
    if not eff:
        eff = {"kind": "none"}
    sev = e.get("severity") or "info"
    title = e.get("title")
    if not title:
        title = f"Incident ({sev})"
    return {
        "id": e.get("id"),
        "templateId": e.get("template_id"),
        "severity": sev,
        "title": title,
        "summary": e.get("summary") or "",
        "createdAt": e.get("created_at_iso"),
        "dueAt": e.get("due_at_iso"),
        "resolved": bool(e.get("resolved")),
        "resolvedAt": e.get("resolved_at_iso"),
        "zone": e.get("zone"),
        "effects": {
            "kind": eff.get("kind") or "none",
            "incomeMult": eff.get("income_mult"),
            "expiresAt": eff.get("expires_at_iso"),
            "flatCostCr": eff.get("flat_cost_cr"),
            "staffRole": eff.get("staff_role"),
        },
    }


def serialize_property_holding_for_web(holding, char=None, feed_room=None):
    """CamelCase payload for UI; omit internal script/registry ids.

    When char is set, manufacturing feed-stock lists are computed for fabrication UI dropdowns.
    feed_room is typically char.location (used when aggregating room + holding sources).
    """
    if not holding or not holding.tags.has(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY):
        return None

    from typeclasses.manufacturing import (
        serialize_manufactured_catalog_for_web,
        serialize_manufacturing_recipes_for_web,
        serialize_workshops_for_web,
    )
    from world.manufacturing_ui import manufacturing_feed_stock_rows
    from world.processor_web import portable_processors_deployed_for_json

    op = dict(holding.db.operation or {})
    ledger = dict(holding.db.ledger or {})
    st = dict(holding.db.place_state or {})
    staff = dict(holding.db.staff or {})
    roles = dict(staff.get("roles") or {})

    structures = []
    for st_obj in holding.structures():
        structures.append(
            {
                "id": st_obj.id,
                "key": st_obj.key,
                "blueprintId": st_obj.db.blueprint_id,
                "slotWeight": int(st_obj.db.slot_weight or 1),
                "upgrades": dict(st_obj.db.upgrades or {}),
                "condition": int(st_obj.db.condition or 0),
            }
        )

    events = list(holding.db.event_queue or [])
    event_preview = [_serialize_incident_for_web(x) for x in events[-20:]]

    zone = normalized_zone(holding)

    build_catalog = []
    for row in catalog_rows_for_zone(zone):
        build_catalog.append(
            {
                "id": row["id"],
                "name": row["name"],
                "structureKind": row["structureKind"],
                "slotWeight": int(row["slotWeight"]),
                "priceCr": int(row["priceCr"]),
            }
        )

    return {
        "holdingId": holding.id,
        "developmentState": holding.db.development_state,
        "zone": zone,
        "lotTier": int(holding.db.lot_tier or 1),
        "sizeUnits": int(holding.db.size_units or 1),
        "structureSlotsUsed": holding.used_structure_slots(),
        "structureSlotsTotal": holding.structure_slots_total(),
        "operation": {
            "kind": op.get("kind"),
            "level": int(op.get("level") or 0),
            "nextTickAt": op.get("next_tick_at"),
            "paused": bool(op.get("paused")),
            "extraSlots": int(op.get("extra_slots") or 0),
        },
        "ledger": {
            "creditsAccrued": int(ledger.get("credits_accrued") or 0),
            "lastTickIso": ledger.get("last_tick_iso"),
        },
        "place": {
            "mode": st.get("mode") or "void",
            "rootRoomId": st.get("root_room_id"),
        },
        "staffRoleKeys": list(roles.keys()),
        "eventQueueLength": len(events),
        "eventQueuePreview": event_preview,
        "structures": structures,
        "defaultOperationKind": DEFAULT_KIND_BY_ZONE.get(zone),
        "allowedOperationKinds": [
            k for (z, k) in OPERATION_HANDLERS.keys() if z == zone
        ],
        "buildCatalog": build_catalog,
        "structureUpgradeCatalog": serialize_structure_upgrade_catalog_for_web(),
        "nextExtraStructureSlotPriceCr": next_extra_structure_slot_price_cr(holding),
        "retoolFeeCr": RETOOL_FEE_CR,
        "deedTransferFeeCr": PROPERTY_DEED_TRANSFER_FEE_CR,
        "workshops": serialize_workshops_for_web(holding),
        "manufacturingRecipes": serialize_manufacturing_recipes_for_web(),
        "manufacturedProducts": serialize_manufactured_catalog_for_web(),
        "manufacturingFeedStockHoldingOnly": (
            manufacturing_feed_stock_rows(holding, char, holding_sources_only=True, room=None)
            if char
            else []
        ),
        "manufacturingFeedStockWithRoom": (
            manufacturing_feed_stock_rows(
                holding, char, holding_sources_only=False, room=feed_room
            )
            if char
            else []
        ),
        "portableProcessorsDeployed": (
            portable_processors_deployed_for_json(holding, char) if char else []
        ),
    }
