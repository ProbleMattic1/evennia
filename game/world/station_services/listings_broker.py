from __future__ import annotations

from typeclasses.characters import LISTINGS_BROKER_CHARACTER_KEY
from typeclasses.claim_listings import get_claim_listings_rows
from typeclasses.packages import get_package_listings
from typeclasses.property_deed_market import get_property_deed_listings

from world.station_services.npc_gate import venue_id_for_caller
from world.station_services.presence_msg import maybe_desk_ambience

_PAGE_SIZE = 15


def handle(character, args: str, extra_switches: tuple[str, ...]) -> str:
    vid = venue_id_for_caller(character) or "nanomega_core"
    tokens = (args or "").strip().split()
    page = 1
    mine_only = False
    for t in tokens:
        low = t.lower()
        if low == "mine":
            mine_only = True
        elif t.isdigit():
            page = max(1, int(t))

    lines = [f"|wListings broker|n (venue |c{vid}|n):"]

    pkgs = get_package_listings(vid) or []
    if mine_only:
        pkgs = [r for r in pkgs if int(r.get("sellerId") or 0) == character.id]
    start = (page - 1) * _PAGE_SIZE
    slice_pkgs = pkgs[start : start + _PAGE_SIZE]
    if not pkgs:
        lines.append("No mining packages listed here right now.")
    else:
        lines.append(f"|wMining packages|n (page {page}, showing {len(slice_pkgs)} of {len(pkgs)}):")
        for row in slice_pkgs:
            lines.append(
                f"  |y{row.get('key', '?')}|n — |w{int(row.get('price', 0) or 0):,}|n cr "
                f"(seller {row.get('sellerKey', '?')})"
            )
        if start + _PAGE_SIZE < len(pkgs):
            lines.append(f"  |gNext:|n |wstation/listings {page + 1}|n")

    claims = get_claim_listings_rows(vid) or []
    if mine_only:
        claims = [r for r in claims if r.get("sellerKey") == character.key]
    lines.append("")
    if not claims:
        lines.append("|wMining claim deeds:|n none listed here.")
    else:
        lines.append(f"|wMining claim deeds:|n ({len(claims)} total)")
        for row in claims[:10]:
            lines.append(
                f"  |y{row.get('claimKey', '?')}|n @ {row.get('siteKey', '?')} — "
                f"|w{int(row.get('listingPriceCr', 0) or 0):,}|n cr ({row.get('sellerKey', '?')}) "
                f"[hazard {row.get('hazardLabel', '?')}]"
            )
        if len(claims) > 10:
            lines.append(f"  ... and {len(claims) - 10} more.")

    deeds = get_property_deed_listings(vid) or []
    if mine_only:
        deeds = [r for r in deeds if r.get("sellerKey") == character.key]
    lines.append("")
    if not deeds:
        lines.append("|wProperty deeds:|n none listed here.")
    else:
        lines.append(f"|wProperty deeds:|n ({len(deeds)} total)")
        for row in deeds[:10]:
            lines.append(
                f"  |y{row.get('key', '?')}|n — |w{int(row.get('price', 0) or 0):,}|n cr "
                f"({row.get('sellerKey', '?')})"
            )
        if len(deeds) > 10:
            lines.append(f"  ... and {len(deeds) - 10} more.")

    if mine_only:
        lines.append("")
        lines.append("|gFilter:|n showing rows where you are the seller (|wmine|n).")

    maybe_desk_ambience(
        character,
        LISTINGS_BROKER_CHARACTER_KEY,
        "{npc} taps a console as {player} scans market listings.",
    )
    return "\n".join(lines)
