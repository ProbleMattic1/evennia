"""
Reload ambient world templates from JSON (no full server reload).
"""

from pathlib import Path

from commands.command import Command
from world.ambient_loader import load_ambient_from_json
from world.ambient_registry import get_ambient_snapshot


class CmdReloadAmbient(Command):
    """
    Reload ambient world templates from JSON (no full server reload).

    With no arguments, loads ``world/data/ambient.d/*.json`` (sorted) plus
    optional ``world/data/ambient_templates.json``. With a path, loads that
    file only.

    Usage:
      reloadambient
      reloadambient /absolute/or/server/path/some_file.json
    """

    key = "reloadambient"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
        ver = load_ambient_from_json(path)
        snap = get_ambient_snapshot()
        errs = snap.get("errors") or ()
        self.caller.msg(
            f"Ambient registry v{ver}: tick={len(snap['by_cadence']['tick'])} "
            f"strong={len(snap['by_cadence']['strong'])} errors={len(errs)}."
        )
        for e in errs[:10]:
            self.caller.msg(f"  ! {e}")
        if len(errs) > 10:
            self.caller.msg(f"  ... and {len(errs) - 10} more (see server log).")
