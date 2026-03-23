"""
Command sets
"""

from evennia import default_cmds

from commands.banking import CmdBalance, CmdTreasury
from commands.shipyard import CmdShipyard, CmdInspectShip, CmdBuyShip
from commands.shop import CmdBuy, CmdShop
from commands.vehicles import (
    CmdBoardVehicle,
    CmdExitVehicle,
    CmdPilotVehicle,
    CmdUnpilotVehicle,
    CmdVehicleTravel,
    CmdVehicleStatus,
    CmdMyShips,
)


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = 'DefaultCharacter'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdBalance())
        self.add(CmdTreasury())
        self.add(CmdBoardVehicle())
        self.add(CmdExitVehicle())
        self.add(CmdPilotVehicle())
        self.add(CmdUnpilotVehicle())
        self.add(CmdVehicleTravel())
        self.add(CmdVehicleStatus())
        self.add(CmdMyShips())
        self.add(CmdShop())
        self.add(CmdBuy())
        self.add(CmdShipyard())
        self.add(CmdInspectShip())
        self.add(CmdBuyShip())


class AccountCmdSet(default_cmds.AccountCmdSet):
    key = 'DefaultAccount'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    key = 'DefaultUnloggedin'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class SessionCmdSet(default_cmds.SessionCmdSet):
    key = 'DefaultSession'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
