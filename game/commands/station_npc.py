"""
Station service NPCs — thin commands; logic in world.station_services.
"""

from evennia.commands.default.muxcommand import MuxCommand
from typeclasses.characters import (
    CLAIMS_AGENT_CHARACTER_KEY,
    CONTRACT_CLERK_CHARACTER_KEY,
    HAUL_DISPATCHER_CHARACTER_KEY,
    LISTINGS_BROKER_CHARACTER_KEY,
    REFINERY_ANALYST_CHARACTER_KEY,
)
from world.station_services import claims_agent, contracts, haul_dispatcher, listings_broker, refinery_analyst
from world.station_services.npc_gate import StationServiceError, require_npc_in_room
from world.station_services.presence_msg import station_room_echo
from world.station_services.service_result import as_result

ROUTES = {
    "listings": (LISTINGS_BROKER_CHARACTER_KEY, listings_broker.handle),
    "haul": (HAUL_DISPATCHER_CHARACTER_KEY, haul_dispatcher.handle),
    "refine": (REFINERY_ANALYST_CHARACTER_KEY, refinery_analyst.handle),
    "claims": (CLAIMS_AGENT_CHARACTER_KEY, claims_agent.handle),
    "contracts": (CONTRACT_CLERK_CHARACTER_KEY, contracts.handle),
}


class CmdStation(MuxCommand):
    """
    Station service NPCs (stand next to the matching clerk).

    Usage:
      station/listings [<page>] [mine]
      station/haul
      station/refine
      station/claims [search <text>]
      station/contracts [list | accept <id> | progress]
    """

    key = "station"
    aliases = ["svc"]
    locks = "cmd:all()"
    help_category = "Commerce"

    def func(self):
        if not self.switches:
            self.caller.msg(
                "Usage: |wstation/listings|n, |wstation/haul|n, |wstation/refine|n, "
                "|wstation/claims|n, |wstation/contracts|n (see |whelp station|n)."
            )
            return
        sub = self.switches[0].lower()
        row = ROUTES.get(sub)
        if not row:
            self.caller.msg("Unknown station service. See |whelp station|n.")
            return
        npc_key, handler = row
        try:
            npc = require_npc_in_room(self.caller, npc_key)
            raw = handler(self.caller, self.args, tuple(self.switches[1:]))
            result = as_result(raw)
            self.caller.msg(result.private)
            if result.room_echo_template:
                loc = self.caller.location
                station_room_echo(loc, npc, self.caller, result.room_echo_template)
        except StationServiceError as exc:
            self.caller.msg(str(exc))
