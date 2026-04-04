"""
Central numeric defaults for engine interval patching at server start.

Typeclasses remain authoritative; this module is used only where startup historically
forced intervals (legacy DB drift).
"""

MINING_ENGINE_INTERVAL_SEC = 60
FLORA_ENGINE_INTERVAL_SEC = 60
FAUNA_ENGINE_INTERVAL_SEC = 60
