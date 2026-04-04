"""
Space combat player commands.

These commands work whenever the character has an active engagement
(db.active_space_engagement_id points to a live SpaceEngagement script).

Usage flow:
  engage <npc_key>    — start a new engagement against a scripted NPC profile
  disengage           — attempt to withdraw (burn_out maneuver + end)
  vstatus             — view current engagement status
  burn                — execute a burn maneuver (in or out)
  coldcoast           — go dark; bleed heat, cannot fire this tick
  jink                — evade; try to gain aspect advantage
  spike               — EW: force your signature up; enemy lock climbs
  ghost               — EW: attempt to break an enemy lock on you
  seduction           — EW: decoy feint to divert enemy lock
  fox                 — launch a missile (FOX call)
  kinetic             — fire kinetic rounds at current solution
  pdc                 — toggle PDC point-defence posture
"""

from commands.command import Command
from typeclasses.space_engagement import create_space_engagement, get_engagement_for_character


class SpaceCombatMixin:
    """Shared guard for all commands that require an active engagement."""

    def _engagement(self):
        eng = get_engagement_for_character(self.caller)
        if not eng:
            self.caller.msg("|y[Space]|n You are not in an active engagement.")
        return eng


class CmdEngage(Command):
    """
    Start a starship engagement against an NPC target.

    Usage:
      engage <target_name>

    <target_name> must be a known NPC profile key. You must be piloting
    a spaceworthy vessel to engage.
    """

    key = "engage"
    help_category = "Space Combat"

    def func(self):
        caller = self.caller
        target_name = (self.args or "").strip()
        if not target_name:
            caller.msg("Engage what? Usage: engage <target>")
            return

        if get_engagement_for_character(caller):
            caller.msg("|y[Space]|n You are already in an engagement. Use |wvstatus|n to check it.")
            return

        # Require the caller to be piloting a vehicle
        vehicle = None
        loc = caller.location
        if loc and getattr(loc.db, "is_vehicle", False):
            if loc.db.pilot == caller:
                vehicle = loc

        if not vehicle:
            caller.msg("|y[Space]|n You must be at the helm of a piloted spacecraft to engage.")
            return

        if not vehicle.is_spaceworthy():
            caller.msg("|y[Space]|n This vessel is not spaceworthy.")
            return

        bravo_config = _npc_profile(target_name)
        if not bravo_config:
            caller.msg(f"|y[Space]|n No known NPC profile for |w{target_name}|n.")
            return

        eng = create_space_engagement(caller, vehicle, bravo_config)
        from evennia import GLOBAL_SCRIPTS

        from world.challenges.challenge_signals import emit as challenge_emit

        preg = GLOBAL_SCRIPTS.get("party_registry")
        pid = preg.party_id_for(caller) if preg else None
        challenge_emit(
            caller,
            "fleet_dispatch",
            {
                "party_id": pid,
                "npc_key": target_name,
                "vehicle_id": vehicle.id,
            },
        )
        caller.msg(
            f"|w[Space]|n Engagement started against |r{bravo_config['label']}|n. "
            f"Use |wvstatus|n, |wburn|n, |wfox|n, |wkinetic|n, |wghost|n etc."
        )
        for line in eng.status_lines():
            caller.msg(line)


class CmdDisengage(SpaceCombatMixin, Command):
    """
    Attempt to disengage from the current engagement.

    Usage:
      disengage

    Executes a burn_out maneuver and ends your participation.
    The engagement closes if no human pilots remain.
    """

    key = "disengage"
    aliases = ["withdraw"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "maneuver", "burn_out")
        # Clear the character's engagement reference
        self.caller.db.active_space_engagement_id = None
        eng.db.participants = [
            p for p in (eng.db.participants or []) if p and p != self.caller
        ]
        self.caller.msg("|y[Space]|n You break off and disengage.")


class CmdVStatus(SpaceCombatMixin, Command):
    """
    View the current engagement status.

    Usage:
      vstatus
    """

    key = "vstatus"
    aliases = ["vstat"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        for line in eng.status_lines():
            self.caller.msg(line)


class CmdBurn(SpaceCombatMixin, Command):
    """
    Execute a burn maneuver to change range.

    Usage:
      burn in      — close range with a hard burn
      burn out     — open range / attempt to create separation

    Both spike heat and signature. Closing to merge range enables
    kinetic solutions but exposes you to the same.
    """

    key = "burn"
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        direction = (self.args or "").strip().lower()
        if direction not in ("in", "out"):
            self.caller.msg("Usage: burn in  |or|  burn out")
            return
        eng.player_action(self.caller, "maneuver", f"burn_{direction}")


class CmdColdCoast(SpaceCombatMixin, Command):
    """
    Go dark — coast without active drives or sensors.

    Usage:
      coldcoast

    Bleeds heat quickly and drops your signature, but you cannot fire
    or lock targets this tick.
    """

    key = "coldcoast"
    aliases = ["cold", "darkrun"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "maneuver", "cold_coast")


class CmdJink(SpaceCombatMixin, Command):
    """
    Execute an evasive jink to gain aspect advantage.

    Usage:
      jink

    Spikes heat slightly. Success depends on your vessel's agility rating.
    """

    key = "jink"
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "maneuver", "jink")


class CmdSpike(SpaceCombatMixin, Command):
    """
    Spike your drive and sensor signature (EW).

    Usage:
      spike

    Deliberately broadcasts a hot profile — enemy lock quality climbs,
    but so does your threat. Useful when you want to draw attention away
    from an ally or force an engagement.
    """

    key = "spike"
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "ew", "spike")


class CmdGhost(SpaceCombatMixin, Command):
    """
    Attempt to break the enemy lock on you (EW ghost run).

    Usage:
      ghost

    Success chance scales with your vessel's stealth rating.
    """

    key = "ghost"
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "ew", "ghost")


class CmdSeduction(SpaceCombatMixin, Command):
    """
    Fire a seduction feint to divert the enemy lock (EW decoy).

    Usage:
      seduction

    Contests your stealth against the enemy sensors rating.
    """

    key = "seduction"
    aliases = ["decoy"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "ew", "seduction")


class CmdFox(SpaceCombatMixin, Command):
    """
    Launch a missile — FOX call.

    Usage:
      fox

    Consumes one hardpoint. Time-to-impact depends on current range band.
    The enemy can defeat the missile with PDC during its run.
    """

    key = "fox"
    aliases = ["fox2", "launch"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "weapon", "fox_missile")


class CmdKinetic(SpaceCombatMixin, Command):
    """
    Fire kinetic rounds at the current target.

    Usage:
      kinetic

    Hit chance is highest at knife/merge range with good lock quality.
    """

    key = "kinetic"
    aliases = ["fire", "guns"]
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "weapon", "kinetic_squeeze")


class CmdPDC(SpaceCombatMixin, Command):
    """
    Toggle point-defence cannon (PDC) posture.

    Usage:
      pdc

    PDC ON significantly improves your chance of defeating inbound missiles
    but raises your emcon and heat profile.
    """

    key = "pdc"
    help_category = "Space Combat"

    def func(self):
        eng = self._engagement()
        if not eng:
            return
        eng.player_action(self.caller, "weapon", "pdc_posture")


# ---------------------------------------------------------------------------
# NPC profile registry (lightweight — expand with JSON data later)
# ---------------------------------------------------------------------------

_NPC_PROFILES: dict[str, dict] = {
    "pirate_fighter": {
        "profile_key": "pirate_fighter",
        "label": "Pirate Fighter",
        "ai_policy_id": "aggressive",
        "vehicle_combat": {
            "hp": 40,
            "shields": 20,
            "armor": 2,
            "agility": 7,
            "sensors": 4,
            "stealth": 3,
            "hardpoints": 2,
        },
    },
    "patrol_corvette": {
        "profile_key": "patrol_corvette",
        "label": "Patrol Corvette",
        "ai_policy_id": "balanced",
        "vehicle_combat": {
            "hp": 90,
            "shields": 40,
            "armor": 5,
            "agility": 5,
            "sensors": 7,
            "stealth": 2,
            "hardpoints": 4,
        },
    },
    "armed_freighter": {
        "profile_key": "armed_freighter",
        "label": "Armed Freighter",
        "ai_policy_id": "defensive",
        "vehicle_combat": {
            "hp": 120,
            "shields": 10,
            "armor": 8,
            "agility": 2,
            "sensors": 4,
            "stealth": 1,
            "hardpoints": 2,
        },
    },
    "ghost_hull": {
        "profile_key": "ghost_hull",
        "label": "Ghost Hull (Unknown)",
        "ai_policy_id": "aggressive",
        "vehicle_combat": {
            "hp": 60,
            "shields": 30,
            "armor": 3,
            "agility": 8,
            "sensors": 9,
            "stealth": 9,
            "hardpoints": 3,
        },
    },
}


def _npc_profile(name: str) -> dict | None:
    return _NPC_PROFILES.get(name.strip().lower().replace(" ", "_"))
