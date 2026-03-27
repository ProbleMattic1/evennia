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

# Default home / start: repurposed by world.bootstrap_hub as NanoMegaPlex Promenade (see #2).
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
