"""
Server startstop hooks

Called by Evennia at various points during its startup, reload and shutdown
sequence.

at_server_cold_start  — every cold start (shutdown → restart, NOT reload)
                        runs world bootstraps (hub, economy, ability baselines, marcus link, etc.).
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
    try:
        from evennia import search_script

        # Patch MiningEngine interval
        found = search_script("mining_engine")
        if found:
            engine = found[0]
            if engine.interval != 60:
                engine.interval = 60
                engine.restart()
                print("[startup] MiningEngine interval patched to 60s and restarted.")

        # Verify SiteDiscoveryEngine is running and has a valid future ETA
        from datetime import timedelta

        from django.utils import timezone

        disc = search_script("site_discovery_engine")
        if disc:
            script = disc[0]
            eta = script.db.next_discovery_at
            threshold = timezone.now() - timedelta(seconds=int(script.interval) * 2)
            if eta is None or eta < threshold:
                script.db.next_discovery_at = timezone.now() + timedelta(
                    seconds=int(script.interval)
                )
                print("[startup] SiteDiscoveryEngine ETA was stale — reset.")
            if not script.is_active:
                script.start()
                print("[startup] SiteDiscoveryEngine was stopped — restarted.")
        else:
            print("[startup] WARNING: SiteDiscoveryEngine not found. Run bootstrap_mining.")

    except Exception:
        import traceback

        traceback.print_exc()


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

    Bootstrap functions create missing world data only; they do not reset player
    economy state unless explicitly opted in (e.g. MARCUS_RESET_CREDITS).
    """
    from world.bootstrap_character_abilities import bootstrap_character_abilities
    from world.bootstrap_economy import bootstrap_economy
    from world.bootstrap_haulers import bootstrap_haulers
    from world.bootstrap_hub import bootstrap_hub
    from world.bootstrap_marcus_killstar import bootstrap_marcus_killstar
    from world.bootstrap_nanomega_realty import bootstrap_nanomega_realty
    from world.bootstrap_mining import bootstrap_mining
    from world.bootstrap_mining_claim_sale import bootstrap_mining_claim_sale
    from world.bootstrap_mining_packages import bootstrap_mining_packages
    from world.bootstrap_processors import bootstrap_processors
    from world.bootstrap_shipyard import bootstrap_shipyard
    from world.bootstrap_shops import bootstrap_shops
    from world.bootstrap_vehicle_catalog import bootstrap_vehicle_catalog
    from typeclasses.system_alerts import get_system_alerts_script

    _run("NanoMegaPlex hub (#2 → Promenade)", bootstrap_hub)
    _run("global economy script", bootstrap_economy)
    _run("character ability baselines (STR–CHA)", bootstrap_character_abilities)
    _run("Marcus Killstar (account link; credits on create only)", bootstrap_marcus_killstar)
    _run(
        "NanoMegaPlex Real Estate (account link; credits on create only)",
        bootstrap_nanomega_realty,
    )
    _run("vehicle catalog CSV import", bootstrap_vehicle_catalog)
    _run("shipyard rooms + stock templates", bootstrap_shipyard)
    _run("general catalog shops (tech, mining, supply, toy)", bootstrap_shops)
    _run("mining engine + sample sites + Ashfall Basin", bootstrap_mining)
    _run("hauler engine + refinery engine + receiving bay", bootstrap_haulers)
    _run("mining sale packages (Starter Pack, Pro Pack)", bootstrap_mining_packages)
    _run("random mining claim deed at Mining Outfitters", bootstrap_mining_claim_sale)
    _run("ore processor models Mk I–III at Mining Outfitters", bootstrap_processors)
    _run("system alerts queue", lambda: get_system_alerts_script(create_missing=True))


def at_server_cold_stop():
    """Called only when the server goes down due to a shutdown or reset."""
    pass
