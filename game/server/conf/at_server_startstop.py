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

        # Patch MiningEngine interval
        found = search_script("mining_engine")
        if found:
            engine = found[0]
            if engine.interval != 60:
                engine.interval = 60
                engine.restart()
                print("[startup] MiningEngine interval patched to 60s and restarted.")

        flora_eng = search_script("flora_engine")
        if flora_eng:
            fe = flora_eng[0]
            if fe.interval != 60:
                fe.interval = 60
                fe.restart()
                print("[startup] FloraEngine interval patched to 60s and restarted.")

        fauna_eng = search_script("fauna_engine")
        if fauna_eng:
            fae = fauna_eng[0]
            if fae.interval != 60:
                fae.interval = 60
                fae.restart()
                print("[startup] FaunaEngine interval patched to 60s and restarted.")

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

    _run("frontier player arrival", bootstrap_frontier)
    _run("NanoMegaPlex hub (#2 → Promenade)", bootstrap_hub)
    _run("frontier ↔ hub exits", bootstrap_frontier_hub_links)
    _run("global economy script", bootstrap_economy)
    _run("economy automation controller", ensure_economy_automation)
    # Marcus before other admin-account NPC bootstraps so his Character id stays lowest after admin.
    _run("Marcus Killstar (account link; credits on create only)", bootstrap_marcus_killstar)
    _run("promenade guide NPC", bootstrap_promenade_guide)
    _run("promenade room ambience", bootstrap_promenade_room_ambience)
    _run("station service NPCs and contracts", bootstrap_station_services)
    _run("character ability baselines (STR–CHA)", bootstrap_character_abilities)
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
    _run(
        "Frontier service NPCs (realty, construction, advertising)",
        bootstrap_frontier_service_npcs,
    )
    _run("Frontier advertising agency wiring + agent placement", bootstrap_frontier_advertising_wiring)
    _run("NanoMegaPlex Real Estate Office room and base lots", bootstrap_realty_office)
    from world.bootstrap_nmp_charter import bootstrap_nmp_charter
    _run("NanoMegaPlex charter (broker-held flagship parcels)", bootstrap_nmp_charter)
    _run("vehicle catalog CSV import", bootstrap_vehicle_catalog)
    _run("shipyard rooms + stock templates", bootstrap_shipyard)
    _run("general catalog shops (tech, mining, supply, toy)", bootstrap_shops)
    _run("parcel mission NPCs", bootstrap_parcel_mission_npcs)
    _run("mining engine + sample sites + Industrial Basin", bootstrap_mining)
    _run("hauler engine + refinery engine + receiving bay", bootstrap_haulers)
    _run("flora harvest engine", bootstrap_flora_engine)
    _run("fauna harvest engine", bootstrap_fauna_engine)
    _run("mining sale packages (Starter Pack, Pro Pack)", bootstrap_mining_packages)
    _run("Marcus Killstar mining pads", bootstrap_marcus_mines)
    _run("Marcus Killstar flora stands", bootstrap_marcus_flora)
    _run("Marcus Killstar fauna ranges", bootstrap_marcus_fauna)
    _run("NPC industrial miners (plant supply)", bootstrap_npc_industrial_miners)
    _run(
        "NanoMegaPlex NPC industrial miners (plant supply)",
        bootstrap_npc_nanomega_industrial_miners,
    )
    _run(
        "Resource colony flora/fauna (venues + industrial grid)",
        bootstrap_npc_resource_colony_bio,
    )
    _run("random mining claim deed at Mining Outfitters", bootstrap_mining_claim_sale)
    _run("ore processor models Mk I–III at Mining Outfitters", bootstrap_processors)
    _run("system alerts queue", lambda: get_system_alerts_script(create_missing=True))
    _run("mission templates (JSON)", load_mission_templates)
    _run("quest templates (JSON)", load_quest_templates)
    _run("mission seeds queue", lambda: get_mission_seeds_script(create_missing=True))
    _run("crime registry (JSON)", bootstrap_crime_registry_at_startup)
    _run("battlespace registry (JSON)", bootstrap_battlespace_registry_at_startup)
    _run("ambient world engine", bootstrap_world_ambient)
    _run("crime world engine", bootstrap_crime_world)
    _run("battlespace world engine", bootstrap_battlespace_world)
    _run("venue controller scripts", bootstrap_venue_controllers)


def at_server_cold_stop():
    """Called only when the server goes down due to a shutdown or reset."""
    pass
