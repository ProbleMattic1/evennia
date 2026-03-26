"""
Sync PropertyHolding.title_owner from where the deed object currently is.
"""

from typeclasses.characters import CHARACTER_TYPECLASS_PATH
from typeclasses.property_operation_registry import register_property_holding


def sync_property_title_from_deed_location(claim):
    """
    If the deed is on a Character, that character is the titled holder.
    Otherwise (room, escrow container, etc.) clear titled holder on the holding.
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
    else:
        holding.set_title_owner(None)
    register_property_holding(holding)
