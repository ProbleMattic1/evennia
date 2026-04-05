r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

INSTALLED_APPS = INSTALLED_APPS + ["world.apps.WorldConfig"]

_mw = list(MIDDLEWARE)
for _i, _entry in enumerate(_mw):
    if _entry == "evennia.web.utils.middleware.SharedLoginMiddleware":
        _mw[_i] = "web.middleware_shared_login.SharedLoginMiddleware"
        break
else:
    raise RuntimeError(
        "evennia.web.utils.middleware.SharedLoginMiddleware missing from MIDDLEWARE; "
        "Evennia defaults may have changed — re-merge manually."
    )
MIDDLEWARE = _mw + ["web.ui.slow_request_logging_middleware.SlowUiRequestLoggingMiddleware"]

######################################################################
# Evennia base server config
######################################################################

# Show detailed error pages (e.g. CSRF failure reason). Turn off in production.
DEBUG = True

# This is the name of your game. Make it catchy!
SERVERNAME = "game"
ROOT_URLCONF = "web.urls"

# Trusted reverse-proxy IPs only (see Evennia UPSTREAM_IPS + ip_from_request).
# Never list your entire Docker bridge CIDR here — the Next.js container is the
# TCP peer, not a hop to strip unless it adds X-Forwarded-For (see frontend proxy).
UPSTREAM_IPS = ["127.0.0.1", "::1"]

# Room #2: NanoMegaPlex Promenade after world.bootstrap_hub. Player/guest puppet spawn and home
# are set in typeclasses.accounts (Frontier Transit Shell) when location is not passed explicitly.
DEFAULT_HOME = "#2"
START_LOCATION = "#2"
GUEST_HOME = "#2"
GUEST_START_LOCATION = "#2"

# Mirror outbound client text into Character.web_msg_buffer (see server.conf.serversession).
SERVER_SESSION_CLASS = "server.conf.serversession.ServerSession"


######################################################################
# Docker/PostgreSQL: override DATABASES when POSTGRES_HOST env var is set
######################################################################
try:
    from server.conf.docker_settings import *
except ImportError:
    pass

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

######################################################################
# CSRF: allow login from localhost and host IP (required when accessing via IP)
######################################################################
_CSRF_ORIGINS = [
    "http://localhost",
    "http://localhost:4001",
    "http://127.0.0.1",
    "http://127.0.0.1:4001",
    "http://10.0.0.94",
    "http://10.0.0.94:4001",
    "http://10.0.0.94:3000",
]
_extra = os.environ.get("CSRF_TRUSTED_ORIGIN", "")
if _extra:
    for _origin in _extra.split(","):
        _origin = _origin.strip()
        if _origin:
            _CSRF_ORIGINS.append(_origin)

CSRF_TRUSTED_ORIGINS = sorted(set(_CSRF_ORIGINS))

# In-character time: epoch = IC 2200-01-01 00:00 UTC; 1 real second = 24 IC seconds.
TIME_GAME_EPOCH = 7257609600.0
TIME_FACTOR = 24.0

######################################################################
# Global Scripts (Evennia singletons)
#
# Keep each entry to typeclass + persistent only. Evennia hashes this dict;
# adding interval/repeats here can delete and recreate DB scripts on deploy.
# Tune tick intervals in each typeclass at_script_creation instead.
######################################################################

GLOBAL_SCRIPTS = {
    "global_economy": {"typeclass": "typeclasses.economy.EconomyEngine", "persistent": True},
    "commodity_demand": {"typeclass": "typeclasses.commodity_demand.CommodityDemandEngine", "persistent": True},
    "manufacturing_engine": {"typeclass": "typeclasses.manufacturing.ManufacturingEngine", "persistent": True},
    "economy_world_telemetry": {"typeclass": "typeclasses.economy_world_telemetry.EconomyWorldTelemetry", "persistent": True},
    "economy_automation_controller": {
        "typeclass": "typeclasses.economy_automation.EconomyAutomationController",
        "persistent": True,
    },
    "mining_engine": {"typeclass": "typeclasses.mining.MiningEngine", "persistent": True},
    "flora_engine": {"typeclass": "typeclasses.flora.FloraEngine", "persistent": True},
    "fauna_engine": {"typeclass": "typeclasses.fauna.FaunaEngine", "persistent": True},
    "hauler_engine": {"typeclass": "typeclasses.haulers.HaulerEngine", "persistent": True},
    "refinery_engine": {"typeclass": "typeclasses.refining.RefineryEngine", "persistent": True},
    "site_discovery_engine": {"typeclass": "typeclasses.site_discovery.SiteDiscoveryEngine", "persistent": True},
    "flora_site_discovery_engine": {
        "typeclass": "typeclasses.flora_site_discovery.FloraSiteDiscoveryEngine",
        "persistent": True,
    },
    "fauna_site_discovery_engine": {
        "typeclass": "typeclasses.fauna_site_discovery.FaunaSiteDiscoveryEngine",
        "persistent": True,
    },
    "claims_market_snapshot": {"typeclass": "typeclasses.claims_market_snapshot.ClaimsMarketSnapshotScript", "persistent": True},
    "npc_miner_registry": {"typeclass": "world.npc_miner_registry.NpcMinerRegistryScript", "persistent": True},
    "property_operation_registry": {
        "typeclass": "typeclasses.property_operation_registry.PropertyOperationRegistry",
        "persistent": True,
    },
    "property_operations_engine": {
        "typeclass": "typeclasses.property_operations_engine.PropertyOperationsEngine",
        "persistent": True,
    },
    "property_events_engine": {"typeclass": "typeclasses.property_events_engine.PropertyEventsEngine", "persistent": True},
    "property_lot_discovery_engine": {
        "typeclass": "typeclasses.property_lot_discovery.PropertyLotDiscoveryEngine",
        "persistent": True,
    },
    "ambient_world_engine": {"typeclass": "typeclasses.ambient_world_engine.AmbientWorldEngine", "persistent": True},
    "crime_world_engine": {"typeclass": "typeclasses.crime_world_engine.CrimeWorldEngine", "persistent": True},
    "battlespace_world_engine": {
        "typeclass": "typeclasses.battlespace_world_engine.BattlespaceWorldEngine",
        "persistent": True,
    },
    "mission_seeds": {"typeclass": "typeclasses.mission_seeds.MissionSeedsScript", "persistent": True},
    "system_alerts": {"typeclass": "typeclasses.system_alerts.SystemAlertsScript", "persistent": True},
    "station_contracts": {"typeclass": "typeclasses.station_contracts.StationContractsScript", "persistent": True},
    "world_clock_script": {"typeclass": "typeclasses.world_clock_script.WorldClockScript", "persistent": True},
    "world_environment_engine": {
        "typeclass": "typeclasses.world_environment_engine.WorldEnvironmentEngine",
        "persistent": True,
    },
    "instance_manager": {"typeclass": "typeclasses.instance_manager.InstanceManager", "persistent": True},
    "party_registry": {"typeclass": "typeclasses.party_registry.PartyRegistry", "persistent": True},
}

######################################################################
# Evennia contribs (structural alignment)
######################################################################

ACHIEVEMENT_CONTRIB_MODULES = ("world.achievement_data",)

# Session auditing (contrib): disabled by default; enable AUDIT_IN / AUDIT_OUT for forensics.
AUDIT_CALLBACK = "evennia.contrib.utils.auditing.outputs.to_file"
AUDIT_IN = False
AUDIT_OUT = False
