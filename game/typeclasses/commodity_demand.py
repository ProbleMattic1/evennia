"""
Commodity demand engine — Phase 1.

Global script: tracks per-commodity supply/demand pressure, market multipliers,
and procurement contracts. Raw keys match RESOURCE_CATALOG; refined keys match
REFINING_RECIPES.
"""

from __future__ import annotations

import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from evennia import GLOBAL_SCRIPTS, create_script, search_script

from typeclasses.scripts import Script

SCRIPT_KEY = "commodity_demand"
TICK_SECONDS = 3600

DEFAULT_STATE = {
    "version": 1,
    "commodities": {},
    "contracts": {},
    "history": [],
}

STATE_BANDS = (
    ("surplus", 0.82),
    ("normal", 1.00),
    ("tight", 1.12),
    ("shortage", 1.28),
    ("emergency", 1.55),
)


def _utc_now():
    return datetime.now(UTC)


def _build_commodity_catalog():
    from typeclasses.manufacturing import MANUFACTURED_CATALOG
    from typeclasses.mining import RESOURCE_CATALOG
    from typeclasses.refining import REFINING_RECIPES

    rows = {}
    for key, row in RESOURCE_CATALOG.items():
        rows[key] = {
            "key": key,
            "name": row["name"],
            "kind": "raw",
            "base_price_cr": int(row["base_price_cr_per_ton"]),
            "target_daily_volume": 100,
            "supply_today": 0.0,
            "demand_today": 0.0,
            "price_multiplier": 1.00,
            "state": "normal",
            "updated_at": None,
        }
    for key, row in REFINING_RECIPES.items():
        rows[key] = {
            "key": key,
            "name": row["name"],
            "kind": "refined",
            "base_price_cr": int(row["base_value_cr"]),
            "target_daily_volume": 40,
            "supply_today": 0.0,
            "demand_today": 0.0,
            "price_multiplier": 1.00,
            "state": "normal",
            "updated_at": None,
        }
    for key, row in MANUFACTURED_CATALOG.items():
        rows[key] = {
            "key": key,
            "name": row["name"],
            "kind": "manufactured",
            "base_price_cr": int(row["base_value_cr"]),
            "target_daily_volume": 25,
            "supply_today": 0.0,
            "demand_today": 0.0,
            "price_multiplier": 1.00,
            "state": "normal",
            "updated_at": None,
        }
    return rows


class CommodityDemandEngine(Script):
    def at_script_creation(self):
        self.key = SCRIPT_KEY
        self.desc = "Commodity demand, procurement, and market pressure."
        self.interval = TICK_SECONDS
        self.persistent = True
        self.start_delay = True
        self.db.state = deepcopy(DEFAULT_STATE)
        self.db.state["commodities"] = _build_commodity_catalog()
        self.db.state["contracts"] = {}
        self.db.last_rollover_at = _utc_now().date().isoformat()

    @property
    def state(self):
        return self.db.state if self.db.state else deepcopy(DEFAULT_STATE)

    def save_state(self, new_state):
        self.db.state = new_state
        return self.db.state

    def _ensure_commodity_rows(self):
        catalog = _build_commodity_catalog()
        state = deepcopy(self.state)
        rows = state.setdefault("commodities", {})
        changed = False
        for k, template in catalog.items():
            if k not in rows:
                rows[k] = deepcopy(template)
                changed = True
        if changed:
            self.save_state(state)

    def get_commodity(self, commodity_key: str) -> dict:
        self._ensure_commodity_rows()
        key = str(commodity_key).strip()
        rows = self.state.get("commodities") or {}
        if key not in rows:
            raise KeyError(f"Unknown commodity '{commodity_key}'")
        return rows[key]

    def get_market_multiplier(self, commodity_key: str) -> float:
        self._ensure_commodity_rows()
        key = str(commodity_key).strip()
        rows = self.state.get("commodities") or {}
        if key not in rows:
            return 1.0
        return float(rows[key].get("price_multiplier", 1.0) or 1.0)

    def get_buy_price(self, commodity_key: str) -> int:
        row = self.get_commodity(commodity_key)
        return max(1, int(round(row["base_price_cr"] * row["price_multiplier"])))

    def record_supply(self, commodity_key: str, quantity: float):
        if quantity <= 0:
            return
        self._ensure_commodity_rows()
        key = str(commodity_key).strip()
        state = deepcopy(self.state)
        rows = state.setdefault("commodities", {})
        if key not in rows:
            return
        row = rows[key]
        row["supply_today"] = round(float(row.get("supply_today", 0.0)) + float(quantity), 2)
        row["updated_at"] = _utc_now().isoformat()
        self.save_state(state)

    def record_demand(self, commodity_key: str, quantity: float):
        if quantity <= 0:
            return
        self._ensure_commodity_rows()
        key = str(commodity_key).strip()
        state = deepcopy(self.state)
        rows = state.setdefault("commodities", {})
        if key not in rows:
            return
        row = rows[key]
        row["demand_today"] = round(float(row.get("demand_today", 0.0)) + float(quantity), 2)
        row["updated_at"] = _utc_now().isoformat()
        self.save_state(state)

    def recalc_market(self):
        self._ensure_commodity_rows()
        state = deepcopy(self.state)
        for row in state["commodities"].values():
            target = max(1.0, float(row["target_daily_volume"]))
            pressure = (float(row["demand_today"]) - float(row["supply_today"])) / target
            mult = 1.0 + max(-0.35, min(0.60, pressure))
            mult = round(mult, 2)
            row["price_multiplier"] = mult
            row["state"] = "surplus"
            for band_name, threshold in STATE_BANDS:
                if mult >= threshold:
                    row["state"] = band_name
            row["updated_at"] = _utc_now().isoformat()
        self.save_state(state)

    def rollover_day(self):
        self._ensure_commodity_rows()
        state = deepcopy(self.state)
        for row in state["commodities"].values():
            row["supply_today"] = 0.0
            row["demand_today"] = 0.0
        self.db.last_rollover_at = _utc_now().date().isoformat()
        self.save_state(state)

    def create_procurement_contract(
        self,
        *,
        commodity_key: str,
        quantity: float,
        reward_cr: int,
        board_id: str,
        delivery_room_key: str,
    ) -> dict:
        self._ensure_commodity_rows()
        key = str(commodity_key).strip()
        if key not in (_build_commodity_catalog()):
            raise KeyError(f"Unknown commodity '{commodity_key}'")
        state = deepcopy(self.state)
        contracts = state.setdefault("contracts", {})
        contract_id = f"{board_id}:{key}:{int(time.time_ns())}"
        contracts[contract_id] = {
            "id": contract_id,
            "commodity_key": key,
            "quantity": round(float(quantity), 2),
            "reward_cr": int(reward_cr),
            "board_id": board_id,
            "delivery_room_key": delivery_room_key,
            "status": "open",
            "accepted_by": None,
            "created_at": _utc_now().isoformat(),
            "expires_at": (_utc_now() + timedelta(hours=12)).isoformat(),
        }
        self.save_state(state)
        return contracts[contract_id]

    def accept_contract(self, character, contract_id: str) -> dict:
        state = deepcopy(self.state)
        contracts = state.get("contracts") or {}
        if contract_id not in contracts:
            raise KeyError(f"Unknown contract '{contract_id}'")
        row = contracts[contract_id]
        if row["status"] != "open":
            raise ValueError("Contract is not open.")
        row["status"] = "active"
        row["accepted_by"] = int(character.id)
        self.save_state(state)
        return row

    def complete_contract(self, character, contract_id: str) -> dict:
        state = deepcopy(self.state)
        contracts = state.get("contracts") or {}
        if contract_id not in contracts:
            raise KeyError(f"Unknown contract '{contract_id}'")
        row = contracts[contract_id]
        if row["status"] != "active" or int(row.get("accepted_by") or 0) != int(character.id):
            raise ValueError("Contract is not assigned to you.")
        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        acct = econ.get_character_account(character)
        econ.ensure_account(acct, opening_balance=int(character.db.credits or 0))
        econ.deposit(acct, int(row["reward_cr"]), memo=f"Procurement contract {row['id']}")
        econ.sync_character_balance(character)

        ckey = str(row["commodity_key"]).strip()
        qty = float(row["quantity"])
        comm_rows = state.setdefault("commodities", {})
        if ckey in comm_rows:
            cr = comm_rows[ckey]
            cr["demand_today"] = round(float(cr.get("demand_today", 0.0)) + qty, 2)
            cr["updated_at"] = _utc_now().isoformat()

        row["status"] = "completed"
        row["completed_at"] = _utc_now().isoformat()
        self.save_state(state)
        return row

    def at_repeat(self, **kwargs):
        today = _utc_now().date().isoformat()
        last = self.db.last_rollover_at
        if last != today:
            self.rollover_day()
        self.recalc_market()


def get_commodity_demand_engine(create_missing=True):
    try:
        eng = GLOBAL_SCRIPTS.commodity_demand
        if eng:
            return eng
    except Exception:
        pass
    found = search_script(SCRIPT_KEY)
    if found:
        return found[0]
    if create_missing:
        return create_script("typeclasses.commodity_demand.CommodityDemandEngine", key=SCRIPT_KEY)
    return None


def seed_procurement_contracts_if_empty():
    """Idempotent starter contracts per venue processing plant (when no contracts yet)."""
    eng = get_commodity_demand_engine(create_missing=True)
    if not eng:
        return
    state = eng.state
    contracts = state.get("contracts") or {}
    if contracts:
        return
    from world.venues import all_venue_ids, get_venue

    for venue_id in all_venue_ids():
        vspec = get_venue(venue_id)
        plant = vspec["processing"]["plant_room_key"]
        board_id = vspec["bank"]["bank_id"]
        eng.create_procurement_contract(
            commodity_key="copper_ore",
            quantity=50.0,
            reward_cr=15000,
            board_id=board_id,
            delivery_room_key=plant,
        )
        eng.create_procurement_contract(
            commodity_key="iron_ore",
            quantity=80.0,
            reward_cr=12000,
            board_id=board_id,
            delivery_room_key=plant,
        )
        eng.create_procurement_contract(
            commodity_key="refined_copper",
            quantity=5.0,
            reward_cr=6000,
            board_id=board_id,
            delivery_room_key=plant,
        )
