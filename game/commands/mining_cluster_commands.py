"""Form mining camps (6 sites) and mining bases (4 camps)."""

from __future__ import annotations

from commands.command import Command
from commands.mining import _find_owned_sites
from world.mining_clusters import try_form_base, try_form_camp


def _resolve_site_id(caller, token: str) -> int:
    t = (token or "").strip()
    if t.startswith("#"):
        t = t[1:]
    if t.isdigit():
        return int(t)
    frag = t.lower()
    matches = [s for s in _find_owned_sites(caller) if frag in s.key.lower()]
    if not matches:
        raise ValueError(f"No owned site matches {token!r}.")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous site name {token!r}; use #dbref.")
    return int(matches[0].id)


class CmdFormMiningCamp(Command):
    """
    Register six fully surveyed mines you own in the same district as a Mining Camp.

    Usage:
      formminingcamp <site> <site> <site> <site> <site> <site>

    Each site may be a dbref (#123) or a unique substring of your site's name.
    All must be survey level 3 and not already in a cluster.
    Camp grants +10%% production at those sites.
    """

    key = "formminingcamp"
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        parts = (self.args or "").split()
        if len(parts) != 6:
            caller.msg("Usage: formminingcamp <six site refs>")
            return
        ids = []
        try:
            for p in parts:
                ids.append(_resolve_site_id(caller, p))
        except ValueError as exc:
            caller.msg(str(exc))
            return
        ok, msg = try_form_camp(caller, ids)
        if ok:
            caller.msg(msg)
        else:
            caller.msg(f"|r{msg}|n")


class CmdFormMiningBase(Command):
    """
    Merge four of your mining camps into a Mining Base.

    Usage:
      formminingbase <camp_id> <camp_id> <camp_id> <camp_id>

    Use the camp id shown when you formed the camp (camp:xxxxxxxx...).
    Base grants +21%% production (replaces per-site camp bonus on those sites).
    """

    key = "formminingbase"
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        parts = (self.args or "").split()
        if len(parts) != 4:
            caller.msg("Usage: formminingbase <four camp:… ids>")
            return
        for p in parts:
            if not p.startswith("camp:"):
                caller.msg("Each camp id must start with camp:")
                return
        ok, msg = try_form_base(caller, parts)
        if ok:
            caller.msg(msg)
        else:
            caller.msg(f"|r{msg}|n")
