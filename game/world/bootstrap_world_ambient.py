"""Verify AmbientWorldEngine + environment config (created via settings.GLOBAL_SCRIPTS)."""

from world.environment_loader import load_world_environment_config
from world.global_scripts_util import require_global_script
from world.instance_prototypes import load_instance_prototypes


def bootstrap_world_ambient():
    load_world_environment_config()
    load_instance_prototypes()
    require_global_script("ambient_world_engine")
    require_global_script("world_environment_engine")
    require_global_script("instance_manager")
    require_global_script("party_registry")
    print("[world-ambient] Ambient + environment + instance + party ok.")
