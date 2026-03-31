from __future__ import annotations

from evennia import create_script, search_script

SCRIPT_PATH = "typeclasses.economy_automation.EconomyAutomationController"
SCRIPT_KEY = "economy_automation_controller"



def bootstrap_economy_automation():
    existing = search_script(SCRIPT_KEY)
    if existing:
        controller = existing[0]
    else:
        controller = create_script(SCRIPT_PATH, key=SCRIPT_KEY)

    if getattr(controller.db, "phase", None) is None:
        controller.db.phase = "stable"
    if getattr(controller.db, "global_price_multiplier", None) is None:
        controller.db.global_price_multiplier = 1.0
    if getattr(controller.db, "global_upkeep_multiplier", None) is None:
        controller.db.global_upkeep_multiplier = 1.0
    if getattr(controller.db, "global_payout_multiplier", None) is None:
        controller.db.global_payout_multiplier = 1.0
    if getattr(controller.db, "rebalance_history", None) is None:
        controller.db.rebalance_history = []

    return controller
