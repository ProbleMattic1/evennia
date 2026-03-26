"""
Property structure upgrades: pricing, caps, blueprint eligibility, tick effect hooks.

Single source for commands, web API, and property_operation_handlers.
"""

STRUCTURE_UPGRADE_DEFS = {
    "tenancy_marketing": {
        "max_level": 5,
        "level_cost_cr": {
            1: 500,
            2: 1_500,
            3: 4_000,
            4: 10_000,
            5: 25_000,
        },
        "allowed_blueprint_ids": None,
    },
}

STRUCTURE_UPGRADE_TICK = {
    "tenancy_marketing": {"income_mult_per_level": 0.05},
}


def structure_income_multiplier_from_upgrades(holding):
    mult = 1.0
    for st in holding.structures():
        ups = dict(st.db.upgrades or {})
        for key, raw_level in ups.items():
            spec = STRUCTURE_UPGRADE_TICK.get(key)
            if not spec:
                continue
            per = float(spec.get("income_mult_per_level") or 0)
            if per:
                mult += per * int(raw_level or 0)
    return mult


def upgrade_def(key):
    return STRUCTURE_UPGRADE_DEFS.get((key or "").strip().lower())


def next_upgrade_level_cost_cr(upgrade_key, current_level):
    d = upgrade_def(upgrade_key)
    if not d:
        return None, None
    nxt = int(current_level or 0) + 1
    if nxt > int(d["max_level"]):
        return None, None
    costs = d["level_cost_cr"]
    price = costs.get(nxt)
    if price is None:
        return None, None
    return nxt, int(price)


def blueprint_allows_upgrade(d, blueprint_id):
    allowed = d.get("allowed_blueprint_ids")
    if allowed is None:
        return True
    return (blueprint_id or "") in allowed
