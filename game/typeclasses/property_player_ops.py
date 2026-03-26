"""
Player-facing property operation rules (web + in-game commands).

Single source for zone ↔ kind validation vs OPERATION_HANDLERS.
CamelCase serializer for UI (property detail / start-operation response).
"""

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
from world.property_structure_catalog import catalog_row_by_id, catalog_rows_for_zone
from world.property_structure_upgrade_registry import STRUCTURE_UPGRADE_DEFS

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

    econ.withdraw(acct, price, memo=f"property structure {row['id']}")
    owner.db.credits = econ.get_character_balance(owner)

    st = install_structure(holding, row["id"], slot_weight=slot_w)
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

    econ.withdraw(acct, RETOOL_FEE_CR, memo="property operation retool")
    owner.db.credits = econ.get_character_balance(owner)
    return True, msg


def serialize_property_holding_for_web(holding):
    """CamelCase payload for UI; omit internal script/registry ids."""
    if not holding or not holding.tags.has(PROPERTY_HOLDING_TAG, category=PROPERTY_HOLDING_CATEGORY):
        return None

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
    event_preview = events[-20:]

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
    }
