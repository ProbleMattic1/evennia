from __future__ import annotations

from typeclasses.characters import CLAIMS_AGENT_CHARACTER_KEY
from typeclasses.claim_listings import get_claim_listings_rows
from typeclasses.packages import get_package_listings
from typeclasses.property_deed_market import get_property_deed_listings

from world.station_services.npc_gate import venue_id_for_caller
from world.station_services.presence_msg import maybe_desk_ambience

_MAX = 12


def handle(character, args: str, extra_switches: tuple[str, ...]) -> str:
    vid = venue_id_for_caller(character) or "nanomega_core"
    raw = (args or "").strip()
    low = raw.lower()
    q = ""
    if low.startswith("search "):
        q = raw[7:].strip().lower()
    elif raw:
        q = low

    lines = [f"|wClaims agent|n (venue |c{vid}|n):"]

    if not q:
        lines.append("Usage: |wstation/claims search <text>|n to filter listings by name or site.")
        lines.append("Without a query, showing a short sample of current listings.")
        q = ""

    def match_row(row: dict) -> bool:
        if not q:
            return True
        hay = " ".join(
            str(row.get(k, "") or "")
            for k in (
                "siteKey",
                "roomKey",
                "claimKey",
                "key",
                "resources",
                "lotKey",
            )
        ).lower()
        return q in hay

    claims = [r for r in (get_claim_listings_rows(vid) or []) if match_row(r)][: _MAX]
    pkgs = [r for r in (get_package_listings(vid) or []) if match_row(r)][: _MAX]
    deeds = [r for r in (get_property_deed_listings(vid) or []) if match_row(r)][: _MAX]

    if q and not claims and not pkgs and not deeds:
        return "\n".join(lines + [f"No listings match |w{q}|n."])

    if claims:
        lines.append("|wMining claim deeds:|n")
        for row in claims:
            lines.append(
                f"  |y{row.get('claimKey', '?')}|n @ {row.get('siteKey', '?')} "
                f"|w{int(row.get('listingPriceCr', 0) or 0):,}|n cr "
                f"[{row.get('hazardLabel', '?')} hazard]"
            )
    elif q:
        lines.append("|wMining claim deeds:|n (none matching)")

    if pkgs:
        lines.append("|wPackages:|n")
        for row in pkgs:
            lines.append(
                f"  |y{row.get('key', '?')}|n — |w{int(row.get('price', 0) or 0):,}|n cr"
            )
    elif q:
        lines.append("|wPackages:|n (none matching)")

    if deeds:
        lines.append("|wProperty deeds:|n")
        for row in deeds:
            lines.append(
                f"  |y{row.get('key', '?')}|n — |w{int(row.get('price', 0) or 0):,}|n cr"
            )
    elif q:
        lines.append("|wProperty deeds:|n (none matching)")

    if not q:
        lines.append("")
        lines.append("|gTip:|n use |wstation/claims search basin|n (or any substring).")

    maybe_desk_ambience(
        character,
        CLAIMS_AGENT_CHARACTER_KEY,
        "{npc} pulls up registry filings for {player}.",
    )
    return "\n".join(lines)
