"""
Table-driven property operation ticks (rent / floor / line / …).
"""

import random

from evennia.utils import logger

from world.property_incident_templates import (
    active_incident_income_multiplier,
    expire_property_incidents,
)
from world.property_structure_upgrade_registry import structure_income_multiplier_from_upgrades
from world.time import next_mining_delivery_slot_after, parse_iso, to_iso

# --- Long-term balance knobs (tune without touching handler shape) ---
RESIDENTIAL_RENT_BASE = {1: 50, 2: 120, 3: 280}
RESIDENTIAL_LEASE_MULT = 0.82  # vs same tier as rent; steadier flavor, lower mean

COMMERCIAL_FLOOR_BASE = {1: 58, 2: 145, 3: 335}
COMMERCIAL_FLOOR_VOLATILITY_LOW = 0.82
COMMERCIAL_FLOOR_VOLATILITY_HIGH = 1.28

COMMERCIAL_TRAFFIC_BASE = {1: 40, 2: 100, 3: 240}
COMMERCIAL_TRAFFIC_MISS_CHANCE = 0.12  # no payout this tick
COMMERCIAL_TRAFFIC_JACKPOT_MULT = 2.15  # rare good hour

INDUSTRIAL_LINE_BASE = {1: 48, 2: 115, 3: 305}
INDUSTRIAL_LINE_YIELD_MULT = 1.06  # small premium vs old unified rent

INDUSTRIAL_FAB_CASH_MULT = 0.62  # less passive cash; value in fabrication_units
INDUSTRIAL_FAB_UNITS_PER_TIER = {1: 2, 2: 4, 3: 7}


def schedule_next(holding, now):
    return next_mining_delivery_slot_after(now)


def _owner_and_econ():
    from typeclasses.economy import get_economy

    return get_economy(create_missing=True)


def _deposit_to_title_owner(holding, amount, memo):
    econ = _owner_and_econ()
    owner = holding.db.title_owner
    if not owner or amount <= 0:
        return
    acct = econ.get_character_account(owner)
    econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
    econ.deposit(acct, int(amount), memo=memo)
    owner.db.credits = econ.get_balance(acct)


def _accrue_ledger_credits(holding, amount):
    ledger = dict(holding.db.ledger or {})
    ledger["credits_accrued"] = int(ledger.get("credits_accrued") or 0) + int(amount)
    holding.db.ledger = ledger


def dispatch_property_tick(holding, now):
    expire_property_incidents(holding, now)
    op = holding.db.operation
    if op.get("paused"):
        return None
    if not op.get("kind"):
        return None

    next_at = parse_iso(op.get("next_tick_at"))
    if next_at is not None and now < next_at:
        return None

    if op.get("kind") and not holding.db.title_owner:
        if not holding.db.ops_stale_owner_alerted:
            from typeclasses.system_alerts import enqueue_system_alert

            enqueue_system_alert(
                severity="warning",
                category="system",
                title="Property operation without title owner",
                detail=(
                    f"Holding #{holding.id} ({holding.key}) has operation kind "
                    f"{op.get('kind')!r} but no title_owner."
                ),
                source="property_operations",
                dedupe_key=f"property-ops-no-owner:{holding.id}",
            )
            holding.db.ops_stale_owner_alerted = True

    zone = holding.db.zone
    kind = op.get("kind")
    handler = OPERATION_HANDLERS.get((zone, kind))
    if not handler:
        return None

    msg = handler(holding, now)
    op["next_tick_at"] = to_iso(schedule_next(holding, now))
    holding.db.operation = op
    ledger = dict(holding.db.ledger or {})
    ledger["last_tick_iso"] = to_iso(now)
    holding.db.ledger = ledger
    return msg


def _tick_residential_rent(holding, now):
    tier = int(holding.db.lot_tier or 1)
    base = RESIDENTIAL_RENT_BASE[tier]
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    amount = int(round(base * mult))
    lot = holding.db.lot_ref
    lot_key = lot.key if lot else "?"
    logger.log_info(
        f"[property_ops] kind=rent holding_id={holding.id} lot_key={lot_key} amount={amount}"
    )
    _deposit_to_title_owner(holding, amount, f"Property income ({holding.key})")
    _accrue_ledger_credits(holding, amount)
    return f"rent +{amount} cr"


def _tick_residential_lease(holding, now):
    tier = int(holding.db.lot_tier or 1)
    base = int(round(RESIDENTIAL_RENT_BASE[tier] * RESIDENTIAL_LEASE_MULT))
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    amount = int(round(base * mult))
    lot = holding.db.lot_ref
    lot_key = lot.key if lot else "?"
    logger.log_info(
        f"[property_ops] kind=lease holding_id={holding.id} lot_key={lot_key} amount={amount}"
    )
    _deposit_to_title_owner(holding, amount, f"Lease income ({holding.key})")
    _accrue_ledger_credits(holding, amount)
    return f"lease +{amount} cr"


def _tick_commercial_floor(holding, now):
    tier = int(holding.db.lot_tier or 1)
    base = COMMERCIAL_FLOOR_BASE[tier]
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    v = random.uniform(COMMERCIAL_FLOOR_VOLATILITY_LOW, COMMERCIAL_FLOOR_VOLATILITY_HIGH)
    amount = int(round(base * mult * v))
    logger.log_info(
        f"[property_ops] kind=floor holding_id={holding.id} amount={amount} v={v:.3f}"
    )
    _deposit_to_title_owner(holding, amount, f"Floor traffic ({holding.key})")
    _accrue_ledger_credits(holding, amount)
    return f"floor +{amount} cr"


def _tick_commercial_traffic(holding, now):
    tier = int(holding.db.lot_tier or 1)
    if random.random() < COMMERCIAL_TRAFFIC_MISS_CHANCE:
        return "traffic quiet (0 cr)"

    base = COMMERCIAL_TRAFFIC_BASE[tier]
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    if random.random() < 0.08:
        mult *= COMMERCIAL_TRAFFIC_JACKPOT_MULT
    amount = int(round(base * mult))
    _deposit_to_title_owner(holding, amount, f"Traffic surge ({holding.key})")
    _accrue_ledger_credits(holding, amount)
    return f"traffic +{amount} cr"


def _tick_industrial_line(holding, now):
    tier = int(holding.db.lot_tier or 1)
    base = INDUSTRIAL_LINE_BASE[tier]
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    amount = int(round(base * mult * INDUSTRIAL_LINE_YIELD_MULT))
    logger.log_info(
        f"[property_ops] kind=line holding_id={holding.id} amount={amount}"
    )
    _deposit_to_title_owner(holding, amount, f"Line output ({holding.key})")
    _accrue_ledger_credits(holding, amount)
    return f"line +{amount} cr"


def _tick_industrial_fab(holding, now):
    tier = int(holding.db.lot_tier or 1)
    base = INDUSTRIAL_LINE_BASE[tier]
    mult = structure_income_multiplier_from_upgrades(holding)
    mult *= active_incident_income_multiplier(holding, now)
    cash = int(round(base * mult * INDUSTRIAL_FAB_CASH_MULT))
    units = int(INDUSTRIAL_FAB_UNITS_PER_TIER.get(tier, 1))

    ledger = dict(holding.db.ledger or {})
    prev = int(ledger.get("fabrication_units") or 0)
    ledger["fabrication_units"] = prev + units
    holding.db.ledger = ledger

    _deposit_to_title_owner(holding, cash, f"Fab stipend ({holding.key})")
    _accrue_ledger_credits(holding, cash)
    return f"fab +{cash} cr, +{units} fab units (total {prev + units})"


OPERATION_HANDLERS = {
    ("residential", "rent"): _tick_residential_rent,
    ("residential", "lease"): _tick_residential_lease,
    ("commercial", "floor"): _tick_commercial_floor,
    ("commercial", "traffic"): _tick_commercial_traffic,
    ("industrial", "line"): _tick_industrial_line,
    ("industrial", "fab"): _tick_industrial_fab,
}
