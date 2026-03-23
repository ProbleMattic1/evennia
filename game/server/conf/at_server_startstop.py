"""
Server startstop hooks

Called by Evennia at various points during its startup, reload and shutdown
sequence.

at_server_cold_start  — every cold start (shutdown → restart, NOT reload)
                        runs idempotent world bootstraps (hub, economy, marcus, catalog, shipyard, shops).
"""

import traceback


def _run(label, fn):
    """Call fn(), printing a clear success or failure line to the server log."""
    try:
        fn()
        print(f"[startup] OK  — {label}")
    except Exception:
        print(f"[startup] FAIL — {label}")
        traceback.print_exc()


def at_server_init():
    """Called first on every startup, regardless of how."""
    pass


def at_server_start():
    """Called every time the server starts up, regardless of how it was shut down."""
    pass


def at_server_stop():
    """Called just before the server shuts down, regardless of type."""
    pass


def at_server_reload_start():
    """Called only when the server starts back up after a reload."""
    pass


def at_server_reload_stop():
    """Called only when the server stops before a reload."""
    pass


def at_server_cold_start():
    """
    Called only on cold start (after shutdown or reset, not after a reload).

    All bootstrap functions are idempotent (check before create), so running
    them on every cold start is safe and ensures world data always exists.
    """
    from world.bootstrap_economy import bootstrap_economy
    from world.bootstrap_hub import bootstrap_hub
    from world.bootstrap_marcus_killstar import bootstrap_marcus_killstar
    from world.bootstrap_shipyard import bootstrap_shipyard
    from world.bootstrap_shops import bootstrap_shops
    from world.bootstrap_vehicle_catalog import bootstrap_vehicle_catalog

    _run("NanoMegaPlex hub (#2 → Promenade)", bootstrap_hub)
    _run("global economy script", bootstrap_economy)
    _run("Marcus Killstar (admin character + credits)", bootstrap_marcus_killstar)
    _run("vehicle catalog CSV import", bootstrap_vehicle_catalog)
    _run("shipyard rooms + stock templates", bootstrap_shipyard)
    _run("general catalog shops (tech, mining, supply, toy)", bootstrap_shops)


def at_server_cold_stop():
    """Called only when the server goes down due to a shutdown or reset."""
    pass
