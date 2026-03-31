"""
Reload quest templates from JSON (no full server reload).
"""

from pathlib import Path

from commands.command import Command
from world.quest_loader import load_quest_templates, quest_registry_errors


class CmdReloadQuests(Command):
    """
    Reload quest templates from JSON chunks (no full server reload).

    Usage:
      reloadquests
      reloadquests /absolute/path/to/quest_templates.json
    """

    key = "reloadquests"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
        ver = load_quest_templates(path)
        errs = quest_registry_errors()
        self.caller.msg(f"Quest registry v{ver}: errors={len(errs)}.")
        for e in errs[:12]:
            self.caller.msg(f"  ! {e}")
        if len(errs) > 12:
            self.caller.msg(f"  ... and {len(errs) - 12} more (see server log).")
