"""
Progression / XP staff utilities.
"""

from commands.command import Command


class CmdGrantXP(Command):
    """
    Grant XP to yourself (staff).

    Usage:
      grantxp <amount>

    """

    key = "grantxp"
    locks = "cmd:perm(Builder)"
    help_category = "Admin"

    def func(self):
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Usage: grantxp <amount>")
            return
        try:
            n = int(arg)
        except ValueError:
            self.caller.msg("Amount must be an integer.")
            return
        if not hasattr(self.caller, "grant_xp"):
            self.caller.msg("Progression is not available for this object.")
            return
        self.caller.grant_xp(n, reason="staff")
