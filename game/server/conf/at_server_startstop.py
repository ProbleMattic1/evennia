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
    from django.conf import settings
    session_cls = getattr(settings, "SERVER_SESSION_CLASS", "<not set>")
    expected = "server.conf.serversession.ServerSession"
    status = "OK" if session_cls == expected else f"MISMATCH (got {session_cls!r})"
    print(f"[startup] SERVER_SESSION_CLASS: {status}")


def at_server_start():
    """Called every time the server starts up, regardless of how it was shut down."""
    try:
        from world.ambient_loader import bootstrap_ambient_registry_at_startup
        from world.ambient_mission_coverage import log_ambient_mission_coverage
        from world.mission_loader import load_mission_templates
        from typeclasses.mission_seeds import get_mission_seeds_script

        _run("ambient registry (JSON)", bootstrap_ambient_registry_at_startup)
        _run("mission templates (JSON)", load_mission_templates)
        log_ambient_mission_coverage()
        _run("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))

        from evennia import search_script

        # Patch MiningEngine interval
        found = search_script("mining_engine")
        if found:
            engine = found[0]
            if engine.interval != 60:
                engine.interval = 60
                engine.restart()
                print("[startup] MiningEngine interval patched to 60s and restarted.")

        from world.time import HAULER_ENGINE_INTERVAL_SEC

        hauler_scripts = search_script("hauler_engine")
        if hauler_scripts:
            he = hauler_scripts[0]
            need_restart = False
            if int(he.interval) != int(HAULER_ENGINE_INTERVAL_SEC):
                he.interval = HAULER_ENGINE_INTERVAL_SEC
                need_restart = True
            if getattr(he, "start_delay", False):
                he.start_delay = False
                need_restart = True
            if need_restart:
                he.restart()
                print(
                    "[startup] HaulerEngine interval/start_delay synced from world.time and restarted."
                )

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

        prop_disc = search_script("property_lot_discovery_engine")
        if prop_disc:
            ps = prop_disc[0]
            eta = ps.db.next_discovery_at
            threshold = timezone.now() - timedelta(seconds=int(ps.interval) * 2)
            if eta is None or eta < threshold:
                ps.db.next_discovery_at = timezone.now() + timedelta(seconds=int(ps.interval))
                print("[startup] PropertyLotDiscoveryEngine ETA was stale — reset.")
            if not ps.is_active:
                ps.start()
                print("[startup] PropertyLotDiscoveryEngine was stopped — restarted.")
        else:
            print("[startup] WARNING: PropertyLotDiscoveryEngine not found. Run bootstrap_realty_office.")

        prop_ops = search_script("property_operations_engine")
        if prop_ops:
            ps = prop_ops[0]
            if not ps.is_active:
                ps.start()
                print("[startup] PropertyOperationsEngine was stopped — restarted.")
        else:
            print(
                "[startup] WARNING: PropertyOperationsEngine not found. Run bootstrap_realty_office."
            )

        prop_ev = search_script("property_events_engine")
        if prop_ev:
            pe = prop_ev[0]
            if not pe.is_active:
                pe.start()
                print("[startup] PropertyEventsEngine was stopped — restarted.")
        else:
            print(
                "[startup] WARNING: PropertyEventsEngine not found. Run bootstrap_realty_office."
            )

        amb = search_script("ambient_world_engine")
        if amb:
            ae = amb[0]
            if not ae.is_active:
                ae.start()
                print("[startup] AmbientWorldEngine was stopped — restarted.")
        else:
            print(
                "[startup] WARNING: AmbientWorldEngine not found. Run bootstrap_world_ambient."
            )

    except Exception:
        import traceback

        traceback.print_exc()


def at_server_stop():
    """Called just before the server shuts down, regardless of type."""
    pass


def at_server_reload_start():
    """Called only when the server starts back up after a reload."""
    from world.ambient_loader import bootstrap_ambient_registry_at_startup
    from world.ambient_mission_coverage import log_ambient_mission_coverage
    from world.mission_loader import load_mission_templates
    from typeclasses.mission_seeds import get_mission_seeds_script

    _run("ambient registry (JSON)", bootstrap_ambient_registry_at_startup)
    _run("mission templates (JSON)", load_mission_templates)
    log_ambient_mission_coverage()
    _run("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))


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
    from world.bootstrap_frontier import bootstrap_frontier, bootstrap_frontier_hub_links
    from world.bootstrap_haulers import bootstrap_haulers
    from world.bootstrap_hub import bootstrap_hub
    from world.bootstrap_marcus_killstar import bootstrap_marcus_killstar
    from world.bootstrap_nanomega_advertising import bootstrap_nanomega_advertising
    from world.bootstrap_nanomega_construction import bootstrap_nanomega_construction
    from world.bootstrap_nanomega_realty import bootstrap_nanomega_realty
    from world.bootstrap_realty_office import bootstrap_realty_office
    from world.bootstrap_mining import bootstrap_mining
    from world.bootstrap_mining_claim_sale import bootstrap_mining_claim_sale
    from world.bootstrap_mining_packages import bootstrap_mining_packages
    from world.bootstrap_npc_industrial_miners import bootstrap_npc_industrial_miners
    from world.bootstrap_npc_nanomega_industrial_miners import (
        bootstrap_npc_nanomega_industrial_miners,
    )
    from world.bootstrap_processors import bootstrap_processors
    from world.bootstrap_shipyard import bootstrap_shipyard
    from world.bootstrap_shops import bootstrap_shops
    from world.bootstrap_vehicle_catalog import bootstrap_vehicle_catalog
    from world.bootstrap_world_ambient import bootstrap_world_ambient
    from world.bootstrap_parcel_mission_npcs import bootstrap_parcel_mission_npcs
    from world.bootstrap_promenade_guide import (
        bootstrap_promenade_guide,
        bootstrap_promenade_room_ambience,
    )
    from world.mission_loader import load_mission_templates
    from typeclasses.mission_seeds import get_mission_seeds_script
    from typeclasses.system_alerts import get_system_alerts_script

    _run("frontier player arrival", bootstrap_frontier)
    _run("NanoMegaPlex hub (#2 → Promenade)", bootstrap_hub)
    _run("frontier ↔ hub exits", bootstrap_frontier_hub_links)
    _run("promenade guide NPC", bootstrap_promenade_guide)
    _run("promenade room ambience", bootstrap_promenade_room_ambience)
    _run("global economy script", bootstrap_economy)
    _run("character ability baselines (STR–CHA)", bootstrap_character_abilities)
    _run("Marcus Killstar (account link; credits on create only)", bootstrap_marcus_killstar)
    _run(
        "NanoMegaPlex Real Estate (account link; credits on create only)",
        bootstrap_nanomega_realty,
    )
    _run(
        "NanoMegaPlex Construction (account link; credits on create only)",
        bootstrap_nanomega_construction,
    )
    _run(
        "NanoMegaPlex Advertising Agent (agency room; credits on create)",
        bootstrap_nanomega_advertising,
    )
    _run("NanoMegaPlex Real Estate Office room and base lots", bootstrap_realty_office)
    _run("vehicle catalog CSV import", bootstrap_vehicle_catalog)
    _run("shipyard rooms + stock templates", bootstrap_shipyard)
    _run("general catalog shops (tech, mining, supply, toy)", bootstrap_shops)
    _run("parcel mission NPCs", bootstrap_parcel_mission_npcs)
    _run("mining engine + sample sites + Ashfall Basin", bootstrap_mining)
    _run("hauler engine + refinery engine + receiving bay", bootstrap_haulers)
    _run("mining sale packages (Starter Pack, Pro Pack)", bootstrap_mining_packages)
    _run("NPC industrial miners (plant supply)", bootstrap_npc_industrial_miners)
    _run(
        "NanoMegaPlex NPC industrial miners (plant supply)",
        bootstrap_npc_nanomega_industrial_miners,
    )
    _run("random mining claim deed at Mining Outfitters", bootstrap_mining_claim_sale)
    _run("ore processor models Mk I–III at Mining Outfitters", bootstrap_processors)
    _run("system alerts queue", lambda: get_system_alerts_script(create_missing=True))
    _run("mission templates (JSON)", load_mission_templates)
    _run("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))
    _run("ambient world engine", bootstrap_world_ambient)


def at_server_cold_stop():
    """Called only when the server goes down due to a shutdown or reset."""
    pass
