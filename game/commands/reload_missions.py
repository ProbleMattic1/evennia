"""
Reload mission templates from JSON (no full server reload).
"""

from pathlib import Path

from commands.command import Command
from world.ambient_mission_coverage import log_ambient_mission_coverage
from world.mission_loader import load_mission_templates, mission_registry_errors


class CmdReloadMissions(Command):
    """
    Reload mission templates from JSON chunks (no full server reload).

    Usage:
      reloadmissions
      reloadmissions /absolute/path/to/mission_templates.json
    """

    key = "reloadmissions"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
        ver = load_mission_templates(path)
        errs = mission_registry_errors()
        self.caller.msg(f"Mission registry v{ver}: errors={len(errs)}.")
        for e in errs[:12]:
            self.caller.msg(f"  ! {e}")
        if len(errs) > 12:
            self.caller.msg(f"  ... and {len(errs) - 12} more (see server log).")
        log_ambient_mission_coverage()
        self.caller.msg("Coverage re-checked (see server log for ambient↔mission summary).")
