"""
Challenge point store (character): spend lifetime/season points from cadence challenges.

  pointbuy <offer_id>     Purchase one offer from the catalog (no credits).
"""

from commands.command import Command
from world.point_store import (
    all_point_offers,
    load_perk_defs,
    load_point_offers,
    perk_def_registry_errors,
    point_offer_registry_errors,
    serialize_offer_for_web,
)


class CmdPointBuy(Command):
    """
    Spend challenge points on a catalog offer (credits are never used).

    Usage:
      pointbuy <offer_id>
      pointshop
      pointshop/list
    """

    key = "pointbuy"
    aliases = ["pointshop"]
    help_category = "Challenges"

    def func(self):
        caller = self.caller
        arg = (self.args or "").strip()
        if not arg or arg.lower() in ("list", "ls", "catalog"):
            snap = caller.challenges.serialize_for_web()
            plb = int(snap.get("pointsLifetime") or 0)
            psb = int(snap.get("pointsSeason") or 0)
            rows = []
            for off in all_point_offers():
                if not off.get("enabled", True):
                    continue
                ser = serialize_offer_for_web(off)
                cid = ser["id"]
                aff = plb >= int(off.get("costLifetime") or 0) and psb >= int(off.get("costSeason") or 0)
                rows.append(
                    f"  |y{cid}|n — {ser['title']}  "
                    f"(LT {ser['costLifetime']} / SS {ser['costSeason']})"
                    f"{'  |g(affordable)|n' if aff else ''}"
                )
            head = f"|wChallenge point offers|n (lifetime {plb}, season {psb})\n"
            caller.msg(head + ("\n".join(rows) if rows else "  (none loaded)"))
            return

        oid = arg.split()[0].strip()
        ok, msg = caller.challenges.purchase_offer(oid)
        if ok:
            caller.msg(f"|g{msg}|n")
        else:
            caller.msg(f"|r{msg}|n")


class CmdReloadPointOffers(Command):
    """Hot-reload point offer and perk definition JSON (Admin)."""

    key = "reloadpointoffers"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        pv = load_point_offers()
        pe = point_offer_registry_errors()
        self.caller.msg(f"Point offers registry v{pv}: errors={len(pe)}.")
        for x in pe[:10]:
            self.caller.msg(f"  ! {x}")
        kv = load_perk_defs()
        ke = perk_def_registry_errors()
        self.caller.msg(f"Perk defs registry v{kv}: errors={len(ke)}.")
        for x in ke[:10]:
            self.caller.msg(f"  ! {x}")


class CmdSetChallengeSeason(Command):
    """
    Set active challenge season id (Developer). Optionally reset seasonal points.

    Usage:
      setchallengeseason <season_id>
      setchallengeseason <season_id> / resetpoints
    """

    key = "setchallengeseason"
    locks = "cmd:perm(Developer)"
    help_category = "Admin"

    def func(self):
        char = self.session.puppet if self.session else None
        if not char:
            self.msg("You need an active character in-game to set season on that character.")
            return
        raw = (self.args or "").strip()
        if not raw:
            self.msg("Usage: setchallengeseason <season_id> [/ resetpoints]")
            return
        parts = [p.strip() for p in raw.split("/")]
        season_id = parts[0]
        reset = any(p.lower() in ("resetpoints", "reset") for p in parts[1:])
        if not season_id:
            self.msg("Usage: setchallengeseason <season_id> [/ resetpoints]")
            return
        h = char.challenges
        h._state["season_id"] = season_id
        if reset:
            h._state["points_season"] = 0
        h._save()
        self.msg(
            f"Season for |c{char.key}|n set to |y{season_id}|n"
            f"{' (seasonal points reset)' if reset else ''}."
        )
