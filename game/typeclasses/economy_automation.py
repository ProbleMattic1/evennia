from __future__ import annotations

from evennia import search_script

from world.econ_automation.rebalancer import decide_rebalance
from world.econ_automation.sim_metrics import normalized_pressures_for_automation
from world.econ_automation.settlement import settle_passive_income_asset
from world.time import utc_now

from .scripts import Script


class PassiveIncomeMixin:
    """
    Optional mixin for passive earning assets.

    This mixin does not move money into the player's ledger directly.
    It only settles value into obj.db.stored_earnings.
    """

    def at_object_creation(self):
        super().at_object_creation()
        if getattr(self.db, "automation_enabled", None) is None:
            self.db.automation_enabled = True
        if getattr(self.db, "base_daily_profit", None) is None:
            self.db.base_daily_profit = 0
        if getattr(self.db, "base_upkeep_daily", None) is None:
            self.db.base_upkeep_daily = 0
        if getattr(self.db, "efficiency", None) is None:
            self.db.efficiency = 1.0
        if getattr(self.db, "stored_earnings", None) is None:
            self.db.stored_earnings = 0
        if getattr(self.db, "last_settled_iso", None) is None:
            self.db.last_settled_iso = None

    def settle_income(self):
        controller = get_economy_automation_controller(create_missing=True)
        return settle_passive_income_asset(
            self,
            now=utc_now(),
            phase=getattr(controller.db, "phase", "stable") or "stable",
            global_payout_multiplier=float(getattr(controller.db, "global_payout_multiplier", 1.0) or 1.0),
            global_upkeep_multiplier=float(getattr(controller.db, "global_upkeep_multiplier", 1.0) or 1.0),
        )


class EconomyAutomationController(Script):
    """
    Small bounded balancing script.

    This script should not become a giant world simulator.
    Its job is to hold balancing policy and occasionally recompute global knobs.
    """

    def at_script_creation(self):
        self.key = "economy_automation_controller"
        self.desc = "Global economy automation controller."
        self.persistent = True
        self.interval = 1800
        self.start_delay = True
        self.repeats = 0

        self.db.phase = "stable"
        self.db.global_price_multiplier = 1.0
        self.db.global_upkeep_multiplier = 1.0
        self.db.global_payout_multiplier = 1.0
        self.db.rebalance_history = []
        self.db.max_history = 100

    def at_repeat(self):
        inflation_pressure = self._read_inflation_pressure()
        treasury_health = self._read_treasury_health()
        passive_payout_pressure = self._read_passive_payout_pressure()

        c_press, l_press, p_press, sim_snapshot = normalized_pressures_for_automation()

        decision = decide_rebalance(
            current_phase=self.db.phase or "stable",
            inflation_pressure=inflation_pressure,
            treasury_health=treasury_health,
            passive_payout_pressure=passive_payout_pressure,
            commodity_pressure=c_press,
            logistics_pressure=l_press,
            property_pressure=p_press,
        )

        self.db.phase = decision.next_phase
        self.db.global_price_multiplier = decision.global_price_multiplier
        self.db.global_upkeep_multiplier = decision.global_upkeep_multiplier
        self.db.global_payout_multiplier = decision.global_payout_multiplier

        history = list(self.db.rebalance_history or [])
        history.append(
            {
                "timestamp": utc_now().isoformat(),
                "phase": decision.next_phase,
                "reason": decision.reason,
                "inflation_pressure": inflation_pressure,
                "treasury_health": treasury_health,
                "passive_payout_pressure": passive_payout_pressure,
                "commodity_pressure": c_press,
                "logistics_pressure": l_press,
                "property_pressure": p_press,
                "simMetricsSnapshot": sim_snapshot,
                "global_price_multiplier": decision.global_price_multiplier,
                "global_upkeep_multiplier": decision.global_upkeep_multiplier,
                "global_payout_multiplier": decision.global_payout_multiplier,
            }
        )
        self.db.rebalance_history = history[-int(self.db.max_history or 100) :]

    def _read_inflation_pressure(self) -> float:
        econ = get_global_economy(create_missing=False)
        if not econ:
            return 0.0
        tax_pool = int(getattr(econ.db, "tax_pool", 0) or 0)
        miner_slot = int(getattr(econ.db, "miner_payout_this_slot_cr", 0) or 0)
        return min(1.0, max(0.0, (miner_slot / 500000.0) + (tax_pool / 5000000.0) * 0.10))

    def _read_treasury_health(self) -> float:
        econ = get_global_economy(create_missing=False)
        if not econ:
            return 0.50
        alpha = econ.get_treasury_account("alpha-prime")
        balance = int(econ.get_balance(alpha) or 0)
        return min(1.0, max(0.0, balance / 5000000.0))

    def _read_passive_payout_pressure(self) -> float:
        econ = get_global_economy(create_missing=False)
        if not econ:
            return 0.0
        total = int(getattr(econ.db, "miner_payout_total_cr", 0) or 0)
        return min(1.0, max(0.0, total / 50000000.0))



def get_economy_automation_controller(create_missing: bool = True):
    found = search_script("economy_automation_controller")
    if found:
        return found[0]
    if not create_missing:
        return None
    from world.econ_automation.bootstrap import bootstrap_economy_automation

    return bootstrap_economy_automation()



def get_global_economy(create_missing: bool = False):
    from typeclasses.economy import get_economy

    return get_economy(create_missing=create_missing)
