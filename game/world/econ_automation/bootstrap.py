from __future__ import annotations

SCRIPT_KEY = "economy_automation_controller"


def bootstrap_economy_automation():
    from world.global_scripts_util import require_global_script

    controller = require_global_script(SCRIPT_KEY)

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
