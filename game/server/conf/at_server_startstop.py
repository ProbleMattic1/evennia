"""
Server startstop hooks

Called by Evennia at various points during its startup, reload and shutdown
sequence.

at_server_cold_start  — every cold start (shutdown → restart, NOT reload)
                        runs world bootstraps via ``_run_strict``; any failure aborts startup
                        so deploy never leaves a half-built world without a loud error.

at_server_start / reload hooks still use soft ``_run`` (log and continue) where used.
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


def _run_strict(label, fn):
    """
    Like ``_run`` but re-raises after logging. Used from ``at_server_cold_start`` only so
    bootstrap errors fail deploy/start instead of continuing with missing rooms or vendors.
    """
    try:
        fn()
        print(f"[startup] OK  — {label}")
    except Exception:
        print(f"[startup] FAIL — {label}")
        traceback.print_exc()
        raise


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
        from world.crime_loader import bootstrap_crime_registry_at_startup
        from world.crime_mission_coverage import log_crime_mission_coverage
        from world.battlespace_loader import bootstrap_battlespace_registry_at_startup
        from world.battlespace_mission_coverage import log_battlespace_mission_coverage
        from world.mission_loader import load_mission_templates
        from world.quest_loader import load_quest_templates
        from typeclasses.mission_seeds import get_mission_seeds_script
        from server.conf.economy_automation_hook import ensure_economy_automation

        _run("ambient registry (JSON)", bootstrap_ambient_registry_at_startup)
        _run("crime registry (JSON)", bootstrap_crime_registry_at_startup)
        _run("battlespace registry (JSON)", bootstrap_battlespace_registry_at_startup)
        _run("mission templates (JSON)", load_mission_templates)
        _run("quest templates (JSON)", load_quest_templates)
        log_ambient_mission_coverage()
        log_crime_mission_coverage()
        log_battlespace_mission_coverage()
        _run("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))
        _run("economy automation controller", ensure_economy_automation)

        from evennia import search_script

        from world.engine_tuning import (
            FAUNA_ENGINE_INTERVAL_SEC,
            FLORA_ENGINE_INTERVAL_SEC,
            MINING_ENGINE_INTERVAL_SEC,
        )

        # Patch MiningEngine interval
        found = search_script("mining_engine")
        if found:
            engine = found[0]
            if engine.interval != MINING_ENGINE_INTERVAL_SEC:
                engine.interval = MINING_ENGINE_INTERVAL_SEC
                engine.restart()
                print(
                    f"[startup] MiningEngine interval patched to {MINING_ENGINE_INTERVAL_SEC}s and restarted."
                )

        flora_eng = search_script("flora_engine")
        if flora_eng:
            fe = flora_eng[0]
            if fe.interval != FLORA_ENGINE_INTERVAL_SEC:
                fe.interval = FLORA_ENGINE_INTERVAL_SEC
                fe.restart()
                print(
                    f"[startup] FloraEngine interval patched to {FLORA_ENGINE_INTERVAL_SEC}s and restarted."
                )

        fauna_eng = search_script("fauna_engine")
        if fauna_eng:
            fae = fauna_eng[0]
            if fae.interval != FAUNA_ENGINE_INTERVAL_SEC:
                fae.interval = FAUNA_ENGINE_INTERVAL_SEC
                fae.restart()
                print(
                    f"[startup] FaunaEngine interval patched to {FAUNA_ENGINE_INTERVAL_SEC}s and restarted."
                )

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

        wcs = search_script("world_clock_script")
        if wcs:
            wc = wcs[0]
            if not wc.is_active:
                wc.start()
                print("[startup] WorldClockScript was stopped — restarted.")
        else:
            print(
                "[startup] WARNING: WorldClockScript not found. "
                "It must be listed in settings.GLOBAL_SCRIPTS."
            )

        wenv = search_script("world_environment_engine")
        if wenv:
            we = wenv[0]
            if not we.is_active:
                we.start()
                print("[startup] WorldEnvironmentEngine was stopped — restarted.")
        else:
            print(
                "[startup] WARNING: WorldEnvironmentEngine not found. "
                "It must be listed in settings.GLOBAL_SCRIPTS."
            )

        for key, label in (
            ("instance_manager", "InstanceManager"),
            ("party_registry", "PartyRegistry"),
        ):
            found = search_script(key)
            if found:
                sc = found[0]
                if not sc.is_active:
                    sc.start()
                    print(f"[startup] {label} was stopped — restarted.")
            else:
                print(
                    f"[startup] WARNING: {label} not found. It must be listed in settings.GLOBAL_SCRIPTS."
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
    from world.crime_loader import bootstrap_crime_registry_at_startup
    from world.crime_mission_coverage import log_crime_mission_coverage
    from world.mission_loader import load_mission_templates
    from world.quest_loader import load_quest_templates
    from typeclasses.mission_seeds import get_mission_seeds_script

    _run("ambient registry (JSON)", bootstrap_ambient_registry_at_startup)
    _run("crime registry (JSON)", bootstrap_crime_registry_at_startup)
    _run("mission templates (JSON)", load_mission_templates)
    _run("quest templates (JSON)", load_quest_templates)
    log_ambient_mission_coverage()
    log_crime_mission_coverage()
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
    from server.conf.economy_automation_hook import ensure_economy_automation
    from world.bootstrap_frontier import bootstrap_frontier, bootstrap_frontier_hub_links
    from world.bootstrap_haulers import bootstrap_haulers
    from world.bootstrap_hub import bootstrap_hub
    from world.bootstrap_marcus_killstar import bootstrap_marcus_killstar
    from world.bootstrap_marcus_fauna import bootstrap_marcus_fauna
    from world.bootstrap_marcus_flora import bootstrap_marcus_flora
    from world.bootstrap_marcus_mines import bootstrap_marcus_mines
    from world.bootstrap_frontier_npcs import bootstrap_frontier_service_npcs
    from world.bootstrap_nanomega_advertising import (
        bootstrap_frontier_advertising_wiring,
        bootstrap_nanomega_advertising,
    )
    from world.bootstrap_nanomega_construction import bootstrap_nanomega_construction
    from world.bootstrap_nanomega_realty import bootstrap_nanomega_realty
    from world.bootstrap_realty_office import bootstrap_realty_office
    from world.bootstrap_venue_controllers import bootstrap_venue_controllers
    from world.bootstrap_mining import bootstrap_mining
    from world.bootstrap_mining_claim_sale import bootstrap_mining_claim_sale
    from world.bootstrap_mining_packages import bootstrap_mining_packages
    from world.bootstrap_fauna import bootstrap_fauna_engine
    from world.bootstrap_flora import bootstrap_flora_engine
    from world.bootstrap_npc_industrial_miners import bootstrap_npc_industrial_miners
    from world.bootstrap_npc_hybrid_buffer_colony import bootstrap_npc_hybrid_buffer_colony
    from world.bootstrap_npc_split_buffer_colony import bootstrap_npc_tiered_split_colonies
    from world.bootstrap_npc_nanomega_industrial_miners import (
        bootstrap_npc_nanomega_industrial_miners,
    )
    from world.bootstrap_npc_resource_colony_bio import bootstrap_npc_resource_colony_bio
    from world.bootstrap_processors import bootstrap_processors
    from world.bootstrap_shipyard import bootstrap_shipyard
    from world.bootstrap_shops import bootstrap_shops
    from world.bootstrap_vehicle_catalog import bootstrap_vehicle_catalog
    from world.bootstrap_crime import bootstrap_crime_world
    from world.bootstrap_battlespace import bootstrap_battlespace_world
    from world.bootstrap_world_ambient import bootstrap_world_ambient
    from world.crime_loader import bootstrap_crime_registry_at_startup
    from world.battlespace_loader import bootstrap_battlespace_registry_at_startup
    from world.bootstrap_parcel_mission_npcs import bootstrap_parcel_mission_npcs
    from world.bootstrap_promenade_guide import (
        bootstrap_promenade_guide,
        bootstrap_promenade_room_ambience,
    )
    from world.bootstrap_station_services import bootstrap_station_services
    from world.mission_loader import load_mission_templates
    from world.quest_loader import load_quest_templates
    from typeclasses.mission_seeds import get_mission_seeds_script
    from typeclasses.system_alerts import get_system_alerts_script

    _run_strict("frontier player arrival", bootstrap_frontier)
    _run_strict("NanoMegaPlex hub (#2 → Promenade)", bootstrap_hub)
    _run_strict("frontier ↔ hub exits", bootstrap_frontier_hub_links)
    _run_strict("global economy script", bootstrap_economy)
    _run_strict("economy automation controller", ensure_economy_automation)
    # Marcus before other admin-account NPC bootstraps so his Character id stays lowest after admin.
    _run_strict("Marcus Killstar (account link; credits on create only)", bootstrap_marcus_killstar)
    _run_strict("promenade guide NPC", bootstrap_promenade_guide)
    _run_strict("promenade room ambience", bootstrap_promenade_room_ambience)
    _run_strict("station service NPCs and contracts", bootstrap_station_services)
    _run_strict("character ability baselines (STR–CHA)", bootstrap_character_abilities)
    _run_strict(
        "NanoMegaPlex Real Estate (account link; credits on create only)",
        bootstrap_nanomega_realty,
    )
    _run_strict(
        "NanoMegaPlex Construction (account link; credits on create only)",
        bootstrap_nanomega_construction,
    )
    _run_strict(
        "NanoMegaPlex Advertising Agent (agency room; credits on create)",
        bootstrap_nanomega_advertising,
    )
    _run_strict(
        "Frontier service NPCs (realty, construction, advertising)",
        bootstrap_frontier_service_npcs,
    )
    _run_strict("Frontier advertising agency wiring + agent placement", bootstrap_frontier_advertising_wiring)
    _run_strict("NanoMegaPlex Real Estate Office room and base lots", bootstrap_realty_office)
    from world.bootstrap_nmp_charter import bootstrap_nmp_charter
    _run_strict("NanoMegaPlex charter (broker-held flagship parcels)", bootstrap_nmp_charter)
    _run_strict("vehicle catalog CSV import", bootstrap_vehicle_catalog)
    _run_strict("shipyard rooms + stock templates", bootstrap_shipyard)
    _run_strict("general catalog shops (tech, mining, supply, toy)", bootstrap_shops)
    _run_strict("parcel mission NPCs", bootstrap_parcel_mission_npcs)
    _run_strict("mining engine + sample sites + Industrial Basin", bootstrap_mining)
    _run_strict("hauler engine + refinery engine + receiving bay", bootstrap_haulers)
    _run_strict("flora harvest engine", bootstrap_flora_engine)
    _run_strict("fauna harvest engine", bootstrap_fauna_engine)
    _run_strict("mining sale packages (Starter Pack, Pro Pack)", bootstrap_mining_packages)
    _run_strict("Marcus Killstar mining pads", bootstrap_marcus_mines)
    _run_strict("Marcus Killstar flora stands", bootstrap_marcus_flora)
    _run_strict("Marcus Killstar fauna ranges", bootstrap_marcus_fauna)
    _run_strict("NPC industrial miners (plant supply)", bootstrap_npc_industrial_miners)
    _run_strict(
        "NanoMegaPlex NPC industrial miners (plant supply)",
        bootstrap_npc_nanomega_industrial_miners,
    )
    _run_strict(
        "Hybrid Buffer Colony NPC miners (split local / plant)",
        bootstrap_npc_hybrid_buffer_colony,
    )
    _run_strict(
        "Tiered split Resource Colonies (10/25/75/100%)",
        bootstrap_npc_tiered_split_colonies,
    )
    _run_strict(
        "Resource colony flora/fauna (venues + industrial grid)",
        bootstrap_npc_resource_colony_bio,
    )
    from world.mission_place_roles import tag_rooms_for_roles_from_registry

    _run_strict("mission place tags on rooms", tag_rooms_for_roles_from_registry)
    _run_strict("random mining claim deed at Mining Outfitters", bootstrap_mining_claim_sale)
    _run_strict("ore processor models Mk I–III at Mining Outfitters", bootstrap_processors)
    _run_strict("system alerts queue", lambda: get_system_alerts_script(create_missing=True))
    _run_strict("mission templates (JSON)", load_mission_templates)
    _run_strict("quest templates (JSON)", load_quest_templates)
    _run_strict("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))
    _run_strict("crime registry (JSON)", bootstrap_crime_registry_at_startup)
    _run_strict("battlespace registry (JSON)", bootstrap_battlespace_registry_at_startup)
    _run_strict("ambient world engine", bootstrap_world_ambient)
    _run_strict("crime world engine", bootstrap_crime_world)
    _run_strict("battlespace world engine", bootstrap_battlespace_world)
    _run_strict("venue controller scripts", bootstrap_venue_controllers)


def at_server_cold_stop():
    """Called only when the server goes down due to a shutdown or reset."""
    pass
