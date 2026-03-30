"""
Sync PropertyHolding.title_owner (and lot.db.owner) from where the deed is.

Rule:
  - Deed on a Character → that character is the titled owner; lot.db.owner
    is updated to match so the primary-market and deed-market queries stay
    consistent.
  - Deed anywhere else (room, hub escrow, etc.) → title_owner is cleared on
    the holding; lot.db.owner is intentionally left unchanged so the last
    known owner remains traceable (e.g. broker retains ownership while deed
    sits in escrow awaiting a buyer).
"""

from typeclasses.characters import CHARACTER_TYPECLASS_PATH
from typeclasses.property_operation_registry import register_property_holding


def sync_property_title_from_deed_location(claim):
    """
    If the deed is on a Character, update both the holding's title_owner and
    lot.db.owner to that character.  If the deed is in a non-character
    container (room, escrow) clear title_owner but leave lot.db.owner
    unchanged.
    """
    lot = getattr(claim.db, "lot_ref", None)
    if not lot:
        return
    holding = getattr(lot.db, "holding_ref", None)
    if not holding:
        return
    loc = claim.location
    if loc and loc.is_typeclass(CHARACTER_TYPECLASS_PATH, exact=False):
        holding.set_title_owner(loc)
        lot.db.owner = loc
    else:
        holding.set_title_owner(None)
    register_property_holding(holding)
