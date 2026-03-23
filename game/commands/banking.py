from commands.command import Command
from typeclasses.economy import get_economy


class CmdBalance(Command):
    """
    Show your ledger balance.

    Usage:
      balance
    """

    key = "balance"
    aliases = ["credits", "wallet"]
    locks = "cmd:all()"
    help_category = "Economy"

    def func(self):
        econ = get_economy(create_missing=True)
        balance = econ.get_character_balance(self.caller)
        self.caller.msg(f"Your balance: |y{balance:,}|n cr.")


class CmdTreasury(Command):
    """
    Show Alpha Prime treasury balance.

    Usage:
      treasury
    """

    key = "treasury"
    locks = "cmd:perm(Developer)"
    help_category = "Economy"

    def func(self):
        econ = get_economy(create_missing=True)
        balance = econ.get_balance("treasury:alpha-prime")
        self.caller.msg(f"Alpha Prime treasury: |y{balance:,}|n cr.")
