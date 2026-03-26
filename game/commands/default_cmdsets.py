"""
Command sets
"""

from evennia import default_cmds

from commands.chargen_pointbuy import CmdCharCreate, CmdPointBuy
from commands.banking import CmdBalance, CmdTreasury
from commands.mining import (
    CmdAvailableClaims,
    CmdClaimSite,
    CmdDeployMine,
    CmdCollectOre,
    CmdDeployRig,
    CmdLicenseSite,
    CmdLinkStorage,
    CmdMineStatus,
    CmdMines,
    CmdRepairRig,
    CmdSetRig,
    CmdSurvey,
    CmdUndeployMine,
)
from commands.refining import (
    CmdCollectProduct,
    CmdCollectRefined,
    CmdFeedRefinery,
    CmdRefine,
    CmdRefineList,
    CmdRefineStatus,
)
from commands.haulers import (
    CmdAssignHauler,
    CmdHaulerStatus,
    CmdReleaseHauler,
    CmdSetDeliveryMode,
    CmdUpgradeHauler,
)
from commands.shipyard import CmdShipyard, CmdInspectShip, CmdBuyShip
from commands.missions import CmdMissionAccept, CmdMissionChoose, CmdMissions
from commands.property_ops import (
    CmdBuildProperty,
    CmdBuyPropertyDeed,
    CmdBuyPropertyExtraSlot,
    CmdListPropertyDeed,
    CmdPausePropertyOperation,
    CmdResolvePropertyIncident,
    CmdResumePropertyOperation,
    CmdRetoolPropertyOperation,
    CmdStartPropertyOperation,
    CmdUpgradePropertyStructure,
)
from commands.property_place import CmdOpenProperty, CmdVisitProperty
from commands.npc_promenade import CmdAskGuide
from commands.reload_ambient import CmdReloadAmbient
from commands.shop import CmdBuy, CmdShop
from commands.vehicles import (
    CmdBoardVehicle,
    CmdCargoStatus,
    CmdExitVehicle,
    CmdLoadCargo,
    CmdMyShips,
    CmdPilotVehicle,
    CmdUnloadCargo,
    CmdUnpilotVehicle,
    CmdVehicleStatus,
    CmdVehicleTravel,
)


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = 'DefaultCharacter'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdBalance())
        self.add(CmdTreasury())
        self.add(CmdSurvey())
        self.add(CmdClaimSite())
        self.add(CmdDeployRig())
        self.add(CmdLinkStorage())
        self.add(CmdMines())
        self.add(CmdMineStatus())
        self.add(CmdCollectOre())
        self.add(CmdLicenseSite())
        self.add(CmdSetRig())
        self.add(CmdRepairRig())
        self.add(CmdAvailableClaims())
        self.add(CmdDeployMine())
        self.add(CmdUndeployMine())
        self.add(CmdRefineList())
        self.add(CmdRefineStatus())
        self.add(CmdFeedRefinery())
        self.add(CmdRefine())
        self.add(CmdCollectProduct())
        self.add(CmdCollectRefined())
        self.add(CmdAssignHauler())
        self.add(CmdUpgradeHauler())
        self.add(CmdHaulerStatus())
        self.add(CmdReleaseHauler())
        self.add(CmdSetDeliveryMode())
        self.add(CmdBoardVehicle())
        self.add(CmdCargoStatus())
        self.add(CmdLoadCargo())
        self.add(CmdUnloadCargo())
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
        self.add(CmdVisitProperty())
        self.add(CmdOpenProperty())
        self.add(CmdStartPropertyOperation())
        self.add(CmdBuildProperty())
        self.add(CmdPausePropertyOperation())
        self.add(CmdResumePropertyOperation())
        self.add(CmdRetoolPropertyOperation())
        self.add(CmdListPropertyDeed())
        self.add(CmdBuyPropertyDeed())
        self.add(CmdUpgradePropertyStructure())
        self.add(CmdBuyPropertyExtraSlot())
        self.add(CmdResolvePropertyIncident())
        self.add(CmdAskGuide())
        self.add(CmdMissions())
        self.add(CmdMissionAccept())
        self.add(CmdMissionChoose())


class AccountCmdSet(default_cmds.AccountCmdSet):
    key = 'DefaultAccount'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdPointBuy())
        self.add(CmdCharCreate())
        self.add(CmdReloadAmbient())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    key = 'DefaultUnloggedin'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()


class SessionCmdSet(default_cmds.SessionCmdSet):
    key = 'DefaultSession'

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
