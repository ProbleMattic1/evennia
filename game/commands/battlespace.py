"""
Admin battlespace reload command.
"""

from pathlib import Path

from commands.command import Command


class CmdReloadBattlespace(Command):
    """
    Reload battlespace templates from JSON chunks.

    Usage:
      reloadbattlespace
      reloadbattlespace /absolute/path/to/file.json
    """

    key = "reloadbattlespace"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        from world.battlespace_loader import load_battlespace_from_json
        from world.battlespace_registry import get_battlespace_snapshot
        from world.battlespace_mission_coverage import log_battlespace_mission_coverage

        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
            if not path.is_file():
                self.caller.msg(f"|rFile not found:|n {path}")
                return

        ver = load_battlespace_from_json(path)
        snap = get_battlespace_snapshot()
        by_c = snap["by_cadence"]
        errs = snap.get("errors") or ()
        self.caller.msg(
            f"|g[battlespace]|n Registry v{ver} loaded — "
            f"tick={len(by_c['tick'])} strong={len(by_c['strong'])} errors={len(errs)}"
        )
        if errs:
            for e in errs[:10]:
                self.caller.msg(f"  |r{e}|n")
        log_battlespace_mission_coverage()
        self.caller.msg("|g[battlespace]|n Coverage logged (see server log).")
