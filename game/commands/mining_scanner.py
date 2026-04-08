"""Deploy / recover stationary mining scanners."""

from __future__ import annotations

from commands.command import Command
from world.mining_scanner_ops import attempt_deploy_scanner, attempt_undeploy_scanner


class CmdDeployMiningScanner(Command):
    """
    Deploy a Mining Scanner in your current mine room (binds to this deposit).

    Usage:
      deployminingscanner <scanner name fragment>

    You must carry the scanner. The room must contain exactly one mining deposit.
    You may deploy on an unclaimed site or on a site you own.
    """

    key = "deployminingscanner"
    aliases = ["deployscanner"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        if not self.args.strip():
            caller.msg("Usage: deployminingscanner <scanner name fragment>")
            return
        ok, msg = attempt_deploy_scanner(caller, name_fragment=self.args)
        if ok:
            caller.msg(msg)
        else:
            caller.msg(msg)


class CmdUndeployMiningScanner(Command):
    """
    Recover your deployed Mining Scanner to inventory.

    Usage:
      undeplyminingscanner <scanner name fragment>
      pickupminingscanner <fragment>
    """

    key = "undeplyminingscanner"
    aliases = ["pickupminingscanner", "pickupscanner"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        if not self.args.strip():
            caller.msg("Usage: undeplyminingscanner <scanner name fragment>")
            return
        ok, msg = attempt_undeploy_scanner(caller, key_fragment=self.args)
        caller.msg(msg)
