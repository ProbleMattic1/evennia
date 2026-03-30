"""
Visit titled parcel interior (property place layer).
"""

from commands.command import Command

from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
from typeclasses.property_places import open_property_shell, resolve_property_root_room


class CmdVisitProperty(Command):
    """
    Travel to your property parcel interior (opens a shell room on first use).

    Usage:
      visitproperty
      visitproperty <deed name fragment>

    Requires a property claim deed in your inventory. Use |wopenproperty|n first
    if you have not visited before (creates the shell room).
    """

    key = "visitproperty"
    aliases = ["vproperty", "visitparcel"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        fragment = (self.args or "").strip().lower()
        deeds = [
            o
            for o in caller.contents
            if not getattr(o, "destination", None)
            and o.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
        ]
        if not deeds:
            caller.msg("You are not carrying a property deed.")
            return
        claim = None
        if fragment:
            for o in deeds:
                if fragment in (o.key or "").lower():
                    claim = o
                    break
            if not claim:
                caller.msg(f"No property deed matches '{self.args.strip()}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg(
                    "You carry multiple property deeds. Usage: visitproperty <deed name fragment>"
                )
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        if not lot:
            caller.msg("That deed is not linked to a parcel.")
            return
        holding = getattr(lot.db, "holding_ref", None)
        if not holding:
            caller.msg("No development record exists for that parcel.")
            return
        st = dict(holding.db.place_state or {})
        if st.get("mode") == "void":
            caller.msg(
                "This parcel has no interior yet. Use |wopenproperty|n on that deed first."
            )
            return
        room = resolve_property_root_room(holding)
        if not room:
            caller.msg("Could not resolve parcel interior.")
            return
        caller.move_to(room, quiet=True)
        caller.msg(f"You step onto |w{room.key}|n.")
        try:
            from world.challenges.challenge_signals import emit
            emit(caller, "parcel_visited", {"holding_id": holding.id})
        except Exception:
            pass


class CmdOpenProperty(Command):
    """
    Open a visitable shell for a titled parcel (first-time place setup).

    Usage:
      openproperty
      openproperty <deed name fragment>
    """

    key = "openproperty"
    aliases = ["openshell"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        fragment = (self.args or "").strip().lower()
        deeds = [
            o
            for o in caller.contents
            if not getattr(o, "destination", None)
            and o.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
        ]
        if not deeds:
            caller.msg("You are not carrying a property deed.")
            return
        claim = None
        if fragment:
            for o in deeds:
                if fragment in (o.key or "").lower():
                    claim = o
                    break
            if not claim:
                caller.msg(f"No property deed matches '{self.args.strip()}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg(
                    "You carry multiple property deeds. Usage: openproperty <deed name fragment>"
                )
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        if not lot:
            caller.msg("That deed is not linked to a parcel.")
            return
        holding = getattr(lot.db, "holding_ref", None)
        if not holding:
            caller.msg("No development record exists for that parcel.")
            return
        open_property_shell(holding)
        room = resolve_property_root_room(holding)
        if not room:
            caller.msg("Could not create parcel interior.")
            return
        caller.msg(
            f"Parcel shell ready: |w{room.key}|n. Use |wvisitproperty|n to travel there."
        )
