"""
Staff commands for the cadence-challenge system.

  reloadchallenges          — hot-reload challenge_templates.json without restart
  challengeinfo <character> — inspect challenge state and telemetry for a character
  grantchallenge <character> <challenge_id> — forcibly mark a challenge complete
"""

from pathlib import Path

from evennia import search_object
from evennia.utils import logger

from commands.command import Command
from world.challenges.challenge_loader import (
    challenge_registry_errors,
    challenge_registry_version,
    load_challenge_templates,
)
from world.point_store import (
    load_perk_defs,
    load_point_offers,
    perk_def_registry_errors,
    point_offer_registry_errors,
)
from world.time import window_key_for_cadence


class CmdReloadChallenges(Command):
    """
    Hot-reload challenge templates from JSON (no server restart).

    Usage:
      reloadchallenges
      reloadchallenges /path/to/challenge_templates.json
    """

    key = "reloadchallenges"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        path = None
        arg = (self.args or "").strip()
        if arg:
            path = Path(arg)
        ver = load_challenge_templates(path)
        errs = challenge_registry_errors()
        self.caller.msg(f"Challenge registry v{ver}: errors={len(errs)}.")
        for e in errs[:12]:
            self.caller.msg(f"  ! {e}")
        if len(errs) > 12:
            self.caller.msg(f"  ... and {len(errs) - 12} more.")
        pov = load_point_offers()
        poe = point_offer_registry_errors()
        self.caller.msg(f"Point offers registry v{pov}: errors={len(poe)}.")
        for e in poe[:8]:
            self.caller.msg(f"  ! {e}")
        pkv = load_perk_defs()
        pke = perk_def_registry_errors()
        self.caller.msg(f"Perk defs registry v{pkv}: errors={len(pke)}.")
        for e in pke[:8]:
            self.caller.msg(f"  ! {e}")


class CmdChallengeInfo(Command):
    """
    Inspect cadence challenge state and telemetry for a character.

    Usage:
      challengeinfo <character name>
    """

    key = "challengeinfo"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        target_key = (self.args or "").strip()
        if not target_key:
            self.caller.msg("Usage: challengeinfo <character name>")
            return

        found = search_object(target_key)
        char = next(
            (o for o in found if o.is_typeclass("typeclasses.characters.Character", exact=False)),
            None,
        )
        if not char:
            self.caller.msg(f"No character found matching '{target_key}'.")
            return

        handler = char.challenges
        web = handler.serialize_for_web()
        tel = handler.telemetry

        lines = [
            f"|wChallenges for |c{char.key}|n",
            f"Registry v{challenge_registry_version()} | state schema v{handler._state.get('schema_version', '?')}",
            "",
            "|yActive:|n",
        ]
        for entry in web.get("active") or []:
            lines.append(
                f"  [{entry['status'][:3].upper()}] {entry['challengeId']} ({entry['cadence']}:{entry['windowKey']})"
            )
        if not (web.get("active") or []):
            lines.append("  (none)")
        lines.append("")
        lines.append("|yTelemetry highlights:|n")
        highlights = [
            "balance_snapshot",
            "vendor_sales_today",
            "treasury_touches_today",
            "hauler_events_today",
            "mine_deposits_today",
            "property_ops_today",
            "lifetime_credits_moved",
            "zones_today",
            "venues_ever",
        ]
        for k in highlights:
            v = tel.get(k)
            if isinstance(v, list):
                lines.append(f"  {k}: {len(v)} entries")
            else:
                lines.append(f"  {k}: {v!r}")
        lines.append("")
        lines.append(f"|yWindows:|n {web.get('windows')}")
        self.caller.msg("\n".join(lines))


class CmdGrantChallenge(Command):
    """
    Force-complete a challenge for a character (testing / staff compensation).

    Usage:
      grantchallenge <character> = <challenge_id>
    """

    key = "grantchallenge"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        if "=" not in (self.args or ""):
            self.caller.msg("Usage: grantchallenge <character> = <challenge_id>")
            return
        char_name, cid = [s.strip() for s in self.args.split("=", 1)]
        if not char_name or not cid:
            self.caller.msg("Usage: grantchallenge <character> = <challenge_id>")
            return

        found = search_object(char_name)
        char = next(
            (o for o in found if o.is_typeclass("typeclasses.characters.Character", exact=False)),
            None,
        )
        if not char:
            self.caller.msg(f"No character found matching '{char_name}'.")
            return

        from world.challenges.challenge_loader import get_challenge_template
        tmpl = get_challenge_template(cid)
        if not tmpl:
            self.caller.msg(f"No challenge template found with id '{cid}'.")
            return

        handler = char.challenges
        cadence = tmpl["cadence"]
        window_key = window_key_for_cadence(cadence)
        handler.get_or_create_active(cid, cadence, window_key)
        ok = handler.mark_complete(cid, window_key)
        handler._save()
        if ok:
            self.caller.msg(f"Challenge |y{cid}|n marked complete for |c{char.key}|n (window: {window_key}).")
            logger.log_info(f"[challenges] staff grant: {cid} for {char.key} window={window_key}")
        else:
            self.caller.msg(f"Could not mark complete (already complete/claimed or bad state).")
