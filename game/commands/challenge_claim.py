"""
Claim rewards for a completed cadence challenge (current UTC window).

Usage:
  challengeclaim <challenge_id>
  challengeclaim daily.vendor_purchase

Uses the template's cadence to resolve the current UTC window key — you do not
type the window. For claiming a past window, use the web UI or a staff tool.
"""

from commands.command import Command
from world.challenges.challenge_loader import get_challenge_template
from world.time import window_key_for_cadence


class CmdChallengeClaim(Command):
    key = "challengeclaim"
    aliases = ["chclaim", "cclaim"]
    locks = "cmd:all()"
    help_category = "Challenges"

    def func(self):
        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Usage: challengeclaim <challenge_id>")
            return

        challenge_id = raw.split()[0].strip()
        tmpl = get_challenge_template(challenge_id)
        if not tmpl:
            self.caller.msg(f"No challenge named {challenge_id!r}.")
            return

        cadence = tmpl.get("cadence") or "daily"
        try:
            window_key = window_key_for_cadence(cadence)
        except Exception:
            self.caller.msg("Invalid cadence on template.")
            return

        ok, msg = self.caller.challenges.mark_claimed(challenge_id, window_key)
        if ok:
            self.caller.msg(f"|g{msg}|n (window |w{window_key}|n)")
            snap = self.caller.challenges.serialize_for_web()
            pl = snap.get("pointsLifetime", 0)
            self.caller.msg(f"Challenge points (lifetime): |y{pl}|n")
        else:
            self.caller.msg(f"|r{msg}|n")
