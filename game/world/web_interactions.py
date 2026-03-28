"""
Shared web-interaction handlers.

Each handler receives a Character and an optional payload dict,
validates preconditions (location, NPC presence, etc.), and returns
an ``InteractionLine`` with dialogue text, interaction key, and speaker.

Raising ``InteractionError`` signals a user-visible failure.
"""

from dataclasses import dataclass

from typeclasses.characters import (
    GENERAL_SUPPLY_CLERK_CHARACTER_KEY,
    PARCEL_COMMUTER_CHARACTER_KEY,
    PROMENADE_GUIDE_CHARACTER_KEY,
)
from world.bootstrap_frontier import START_ROOM_KEY
from world.bootstrap_hub import HUB_ROOM_KEY

PROCESSING_PLANT_ROOM_KEY = "Aurnom Ore Processing Plant"


class InteractionError(Exception):
    """Raised when an interaction cannot proceed (missing NPC, wrong room, etc.)."""


@dataclass(frozen=True)
class InteractionLine:
    dialogue: str
    interaction_key: str
    speaker_key: str | None = None


# ---------------------------------------------------------------------------
# askguide variants
# ---------------------------------------------------------------------------

_GUIDE_REPLIES = {
    "property": "Try the Sovereign property exchange — the broker in the realty office lives for paperwork.",
    "mining": "Ashfall Basin keeps the independents busy. Mining Outfitters sells the boring but vital bits.",
    "security": "Station Security has a desk in the transit hub — ask for Patrol Sergeant Nwosu.",
    "transit": "The shuttle concourse is one level up. Timetable boards update every thirty seconds.",
}

_GUIDE_DEFAULT = "Kiran taps a holo-slate. 'Transit, permits, or profit — pick one and I'll narrow it down.'"


def handle_askguide(char, payload=None):
    loc = char.location
    if not loc:
        raise InteractionError("You are not in a place where a guide could help.")
    guides = [o for o in loc.contents if o.key == PROMENADE_GUIDE_CHARACTER_KEY]
    if not guides:
        raise InteractionError("The station guide is not here.")

    topic = str((payload or {}).get("topic", "")).strip().lower()
    msg = _GUIDE_REPLIES.get(topic, _GUIDE_DEFAULT)
    interaction_key = "askguide" if not topic else f"askguide:{topic}"
    dialogue = f'{PROMENADE_GUIDE_CHARACTER_KEY} says, "{msg}"'
    return InteractionLine(dialogue, interaction_key, PROMENADE_GUIDE_CHARACTER_KEY)


# ---------------------------------------------------------------------------
# parcel mission NPCs
# ---------------------------------------------------------------------------

def handle_parcel_commuter(char, payload=None):
    loc = char.location
    if not loc:
        raise InteractionError("You are not anywhere public enough to ask.")
    if str(loc.key) != HUB_ROOM_KEY:
        raise InteractionError("Mira is only on the main promenade when she is looking for help.")
    found = [o for o in loc.contents if o.key == PARCEL_COMMUTER_CHARACTER_KEY]
    if not found:
        raise InteractionError("Mira is not here.")
    dialogue = (
        f'{PARCEL_COMMUTER_CHARACTER_KEY} lowers her voice. "The trace dead-ends at '
        f'General Supply — kiosk shelf, not the clinic. Whoever coded the pouch '
        f'used a medical routing glyph. If you go, do not flash the seal around."'
    )
    return InteractionLine(dialogue, "parcel:commuter", PARCEL_COMMUTER_CHARACTER_KEY)


def handle_parcel_clerk(char, payload=None):
    loc = char.location
    if not loc:
        raise InteractionError("You are not in a shop.")
    found = [o for o in loc.contents if o.key == GENERAL_SUPPLY_CLERK_CHARACTER_KEY]
    if not found:
        raise InteractionError("The supply clerk is not on duty here.")
    dialogue = (
        f'{GENERAL_SUPPLY_CLERK_CHARACTER_KEY} squints at a handheld scanner. "Last ping '
        f'was holding bay gamma — seal still intact. Contents flagged confidential '
        f'upstream; we are not supposed to open it. You did not hear that from me."'
    )
    return InteractionLine(dialogue, "parcel:supply_clerk", GENERAL_SUPPLY_CLERK_CHARACTER_KEY)


# ---------------------------------------------------------------------------
# frontier arrival
# ---------------------------------------------------------------------------


def handle_frontier_kiosk(char, payload=None):
    loc = char.location
    if not loc or str(loc.key) != START_ROOM_KEY:
        raise InteractionError("There is no patched kiosk here.")
    dialogue = (
        "The display strobes once, then offers a stingy stipend buffer "
        "and a cached line of coreward routing noise."
    )
    return InteractionLine(dialogue, "frontier:kiosk", None)


# ---------------------------------------------------------------------------
# survey
# ---------------------------------------------------------------------------

def handle_survey(char, payload=None):
    loc = char.location
    if not loc:
        raise InteractionError("There is no minable deposit here.")
    site = None
    for obj in loc.contents:
        if obj.tags.has("mining_site", category="mining"):
            site = obj
            break
    if not site:
        raise InteractionError("There is no minable deposit here.")

    new_level, report = site.advance_survey()
    from typeclasses.mining import SURVEY_LEVELS

    label = SURVEY_LEVELS.get(new_level, "?")
    if new_level >= 3:
        dialogue = f"|wSurvey complete ({label}).|n\n{report}"
    else:
        remaining = 3 - new_level
        dialogue = (
            f"|wSurvey advanced to level {new_level} ({label}).|n  "
            f"({remaining} more survey{'s' if remaining > 1 else ''} to full assessment)\n{report}"
        )
    return InteractionLine(dialogue, "survey", None)


# ---------------------------------------------------------------------------
# procurement board (Phase 1 commodity demand)
# ---------------------------------------------------------------------------


def handle_contract_board(char, payload=None):
    loc = char.location
    if not loc:
        raise InteractionError("You are not at a procurement board.")
    if str(loc.key) != PROCESSING_PLANT_ROOM_KEY:
        raise InteractionError("The procurement board is at the Ore Processing Plant.")

    payload = dict(payload or {})
    action = str(payload.get("action") or "list").strip().lower()
    from typeclasses.commodity_demand import get_commodity_demand_engine

    demand = get_commodity_demand_engine(create_missing=True)

    if action == "list":
        state = demand.state
        rows = [
            row
            for row in (state.get("contracts") or {}).values()
            if row.get("status") in ("open", "active")
        ]
        if not rows:
            return InteractionLine("The procurement board is quiet.", "contractboard", None)
        lines = ["|wProcurement Board|n"]
        for row in sorted(rows, key=lambda r: r.get("created_at", ""))[-8:]:
            lines.append(
                f"  {row['id']}  {row['commodity_key']}  qty {row['quantity']}  "
                f"reward {row['reward_cr']:,} cr  {row['status']}"
            )
        return InteractionLine("\n".join(lines), "contractboard", None)

    if action == "accept":
        contract_id = str(payload.get("contractId") or "").strip()
        if not contract_id:
            raise InteractionError("Missing contract id.")
        try:
            row = demand.accept_contract(char, contract_id)
        except KeyError:
            raise InteractionError("Unknown contract.") from None
        except ValueError as exc:
            raise InteractionError(str(exc)) from exc
        return InteractionLine(
            f"Contract accepted: deliver {row['quantity']}t {row['commodity_key']} to {row['delivery_room_key']}.",
            "contractboard:accept",
            None,
        )

    if action == "complete":
        contract_id = str(payload.get("contractId") or "").strip()
        if not contract_id:
            raise InteractionError("Missing contract id.")
        try:
            row = demand.complete_contract(char, contract_id)
        except KeyError:
            raise InteractionError("Unknown contract.") from None
        except ValueError as exc:
            raise InteractionError(str(exc)) from exc
        return InteractionLine(
            f"Contract completed. Paid {row['reward_cr']:,} cr for {row['commodity_key']}.",
            "contractboard:complete",
            None,
        )

    raise InteractionError("Unsupported procurement-board action.")


# ---------------------------------------------------------------------------
# Registry — maps interaction keys to handlers
# ---------------------------------------------------------------------------

WEB_INTERACTION_HANDLERS = {
    "askguide": handle_askguide,
    "askguide:property": lambda char, payload: handle_askguide(char, {"topic": "property"}),
    "askguide:mining": lambda char, payload: handle_askguide(char, {"topic": "mining"}),
    "askguide:security": lambda char, payload: handle_askguide(char, {"topic": "security"}),
    "askguide:transit": lambda char, payload: handle_askguide(char, {"topic": "transit"}),
    "parcel:commuter": handle_parcel_commuter,
    "parcel:supply_clerk": handle_parcel_clerk,
    "frontier:kiosk": handle_frontier_kiosk,
    "survey": handle_survey,
    "contractboard": handle_contract_board,
    "contractboard:accept": lambda char, payload: handle_contract_board(
        char, {**(payload or {}), "action": "accept"}
    ),
    "contractboard:complete": lambda char, payload: handle_contract_board(
        char, {**(payload or {}), "action": "complete"}
    ),
}
