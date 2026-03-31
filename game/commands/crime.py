"""
Player crime record and admin crime JSON reload.
"""

from pathlib import Path

from commands.command import Command


class CmdCrime(Command):
    """
    View your abstract crime record (not a full mission list).

    Usage:
      crime
    """

    key = "crime"
    aliases = ["rapsheet", "record"]
    locks = "cmd:all()"
    help_category = "Story"

    def func(self):
        lines = ["|wRecord (abstract)|n", ""]
        lines.extend(self.caller.crime_record.summary_lines())
        self.caller.msg("\n".join(lines))


class CmdReloadCrime(Command):
    """
    Reload crime templates from JSON chunks.

    Usage:
      reloadcrime
      reloadcrime /absolute/path/to/file.json
    """

    key = "reloadcrime"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        from world.crime_loader import load_crime_from_json
        from world.crime_registry import get_crime_snapshot
        from world.crime_mission_coverage import log_crime_mission_coverage

        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
        ver = load_crime_from_json(path)
        errs = tuple(get_crime_snapshot().get("errors") or ())
        self.caller.msg(f"Crime registry v{ver}: errors={len(errs)}.")
        for e in errs[:12]:
            self.caller.msg(f"  ! {e}")
        if len(errs) > 12:
            self.caller.msg(f"  ... and {len(errs) - 12} more (see server log).")
        log_crime_mission_coverage()
        self.caller.msg("Crime↔mission coverage re-checked (see server log).")
