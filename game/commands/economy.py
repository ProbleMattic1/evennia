"""
Economy commands: balance, etc.
"""

from evennia.commands.default.muxcommand import MuxCommand


class CmdBalance(MuxCommand):
    """
    Check your current wealth.

    Usage:
      balance

    Shows your credits (cr).
    """

    key = "balance"
    aliases = ["bal", "credits", "cr"]
    locks = "cmd:all()"

    def func(self):
        credits = self.caller.db.credits
        if credits is None:
            credits = 0
        self.caller.msg(f"You currently have |y{credits:,}|n credits (cr).")
