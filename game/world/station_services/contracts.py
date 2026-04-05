from __future__ import annotations

from datetime import UTC, datetime

from typeclasses.economy import grant_character_credits
from typeclasses.station_contracts import (
    get_contracts_script,
    register_station_contract_in_flight,
    unregister_station_contract_in_flight,
)

from world.station_services.service_result import StationServiceResult


def handle(character, args: str, extra_switches: tuple[str, ...]) -> str | StationServiceResult:
    script = get_contracts_script()
    if not script:
        return "Contract board is offline."

    parts = (args or "").strip().split()
    contracts = list(script.db.contracts or [])

    if not parts or parts[0].lower() == "list":
        if not contracts:
            return "No open contracts. Check back later."
        lines = ["|wOpen contracts:|n"]
        for c in contracts[:20]:
            lines.append(
                f"  |w{c['id']}|n — {c['title']} — |y{int(c.get('payout', 0) or 0):,}|n cr"
            )
        return "\n".join(lines)

    if parts[0].lower() == "accept" and len(parts) > 1:
        cid = parts[1]
        active = dict(character.db.station_contracts_active or {})
        contracts_by_id = {c["id"]: c for c in contracts}
        c = contracts_by_id.get(cid)
        if not c:
            return "No such contract."
        if cid in active:
            return "You already took that contract."
        active[cid] = {"accepted_at": datetime.now(UTC).isoformat()}
        character.db.station_contracts_active = active
        register_station_contract_in_flight(cid)
        return StationServiceResult(
            private=(
                f"You accepted |w{cid}|n: {c['title']}. Complete it in play; payout on success."
            ),
            room_echo_template="{npc} hands {player} a stamped work order.",
        )

    if parts[0].lower() == "progress":
        prog = character.db.station_contracts_active or {}
        if not prog:
            return "No active contracts."
        lines = ["|wActive contracts:|n"]
        for k, meta in prog.items():
            lines.append(f"  |w{k}|n — accepted {meta.get('accepted_at', '?')}")
        return "\n".join(lines)

    return "Usage: |wstation/contracts list|n, |waccept <id>|n, |wprogress|n."


def try_complete_contract(character, predicate_key: str, *, venue_id: str | None = None) -> None:
    """
    Call from gameplay hooks when a milestone matches an active contract's predicate_key.
    Awards payout once per contract id, then removes from active.
    """
    script = get_contracts_script(create_missing=False)
    if not script:
        return

    contracts_by_id = {c["id"]: c for c in (script.db.contracts or [])}
    active = dict(character.db.station_contracts_active or {})
    if not active:
        return

    to_remove = []
    for cid, _meta in list(active.items()):
        c = contracts_by_id.get(cid)
        if not c:
            to_remove.append(cid)
            continue
        if c.get("predicate_key") != predicate_key:
            continue
        req_venue = c.get("venue_id")
        if req_venue and venue_id and req_venue != venue_id:
            continue
        payout = int(c.get("payout", 0) or 0)
        if payout > 0:
            grant_character_credits(character, payout, memo=f"contract:{cid}")
        xp_award = int(c.get("xp", 0) or 0)
        if xp_award > 0:
            try:
                from world.progression import apply_reward_xp

                apply_reward_xp(character, {"xp": xp_award}, reason=f"contract:{cid}")
            except Exception as exc:
                from evennia.utils import logger

                logger.log_err(f"[contracts] XP reward apply failed for {character.key}: {exc}")
        to_remove.append(cid)

    for cid in to_remove:
        active.pop(cid, None)
        unregister_station_contract_in_flight(cid)
    character.db.station_contracts_active = active
