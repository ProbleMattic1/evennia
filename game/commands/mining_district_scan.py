"""District grid scan from a deployed mining scanner."""

from __future__ import annotations

from commands.command import Command

from world.mining_scanner_ops import attempt_district_scan


class CmdDistrictScan(Command):
    """
    Scan from your deployed scanner for adjacent deposits you can buy.

    Usage:
      districtscan

    Lists mining deposits one exit away (same venue) that you can purchase now:
    NPC primary deed or an active player property listing, if you can afford the price.
    Requires the same deployed scanner as |wsurvey|n.
    """

    key = "districtscan"
    aliases = ["probescan", "districtping"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        ok, err, peers, anchor = attempt_district_scan(caller)
        if not ok:
            caller.msg(err or "District scan failed.")
            return
        if not peers:
            caller.msg("|wDistrict scan|n: no adjacent deposits you can purchase from here.")
            return
        lines = [f"|wDistrict scan|n (from |c{anchor or '?'}|n):"]
        for r in peers:
            st = "claimed" if r["isClaimed"] else "open"
            pk = str(r.get("purchaseKind") or "")
            price = r.get("listingPriceCr")
            try:
                price_s = f"{int(price):,} cr" if price is not None else "—"
            except (TypeError, ValueError):
                price_s = "—"
            lines.append(
                f"  |c{r['roomKey']}|n — {r['siteKey']}  [{st}]  survey L{r['surveyLevel']}  "
                f"|w{pk}|n  {price_s}"
            )
        caller.msg("\n".join(lines))
