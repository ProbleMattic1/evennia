from __future__ import annotations


def ensure_economy_automation():
    """
    Idempotent startup hook.

    Import and call this from the game's preferred startup path.
    """
    from world.econ_automation.bootstrap import bootstrap_economy_automation

    return bootstrap_economy_automation()
