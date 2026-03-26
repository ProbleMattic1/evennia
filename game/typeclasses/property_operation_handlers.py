"""
Table-driven property operation ticks (rent / floor / line).
"""

from datetime import UTC

from world.time import parse_iso, to_iso, utc_now

from typeclasses.haulers import compute_next_hauler_run_at


def schedule_next(holding, now):
    return compute_next_hauler_run_at(holding, after=now)


def dispatch_property_tick(holding, now):
    op = holding.db.operation
    if op.get("paused"):
        return None
    if not op.get("kind"):
        return None

    next_at = parse_iso(op.get("next_tick_at"))
    if next_at is not None and now < next_at:
        return None

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
    from typeclasses.economy import get_economy

    tier = int(holding.db.lot_tier or 1)
    base = {1: 50, 2: 120, 3: 280}[tier]
    mult = 1.0
    for s in holding.structures():
        ups = s.db.upgrades or {}
        mult += 0.05 * int(ups.get("tenancy_marketing", 0) or 0)
    amount = int(round(base * mult))
    owner = holding.db.title_owner
    if owner:
        econ = get_economy(create_missing=True)
        acct = econ.get_character_account(owner)
        econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
        econ.deposit(acct, amount, memo=f"Property income ({holding.key})")
        owner.db.credits = econ.get_balance(acct)
    ledger = dict(holding.db.ledger or {})
    ledger["credits_accrued"] = int(ledger.get("credits_accrued") or 0) + amount
    holding.db.ledger = ledger
    return f"rent +{amount} cr"


def _tick_commercial_floor(holding, now):
    return _tick_residential_rent(holding, now)


def _tick_industrial_line(holding, now):
    return _tick_residential_rent(holding, now)


OPERATION_HANDLERS = {
    ("residential", "rent"): _tick_residential_rent,
    ("commercial", "floor"): _tick_commercial_floor,
    ("industrial", "line"): _tick_industrial_line,
}
