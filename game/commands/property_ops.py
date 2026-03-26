"""
Property income, structures, pause/retool, deed resale (in-game; mirrors web UI).
"""

from commands.command import Command

from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
from typeclasses.property_deed_market import (
    buy_listed_property_deed,
    list_property_deed_for_sale,
)
from typeclasses.property_player_ops import (
    pause_property_operation_for_owner,
    purchase_and_install_structure,
    purchase_extra_structure_slot_for_owner,
    purchase_structure_upgrade_for_owner,
    resolve_property_incident_for_owner,
    retool_property_operation_for_owner,
    start_property_operation_for_owner,
)


class CmdStartPropertyOperation(Command):
    """
    Start periodic property income for a carried deed (zone selects default operation).

    Usage:
      startproperty
      startproperty <deed fragment>
      startproperty <fragment> rent|floor|line

    Residential → rent, Commercial → floor, Industrial → line unless you override kind.
    """

    key = "startproperty"
    aliases = ["startpropertyop", "propertystart"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        parts = self.args.strip().split()
        kind_explicit = None
        if parts and parts[-1].lower() in ("rent", "floor", "line"):
            kind_explicit = parts[-1].lower()
            parts = parts[:-1]
        fragment = " ".join(parts).strip().lower()

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
                    "You carry multiple deeds. Usage: startproperty <fragment> [rent|floor|line]"
                )
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = start_property_operation_for_owner(
            caller, holding, kind_explicit=kind_explicit
        )
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdBuildProperty(Command):
    """
    Purchase and install a catalog structure on your parcel (deed must be carried).

    Usage:
      buildproperty <blueprintId>
      buildproperty <blueprintId> <deed fragment>
    """

    key = "buildproperty"
    aliases = ["propertybuild", "propertbuild"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        raw = self.args.strip().split()
        if not raw:
            caller.msg("Usage: buildproperty <blueprintId> [deed fragment]")
            return
        blueprint_id = raw[0]
        fragment = " ".join(raw[1:]).strip().lower()

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
                caller.msg(f"No property deed matches '{fragment}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg("You carry multiple deeds. Usage: buildproperty <blueprintId> <fragment>")
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg, _st = purchase_and_install_structure(caller, holding, blueprint_id)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdPausePropertyOperation(Command):
    """Pause property income ticks for a carried deed. Usage: pauseproperty [deed fragment]"""

    key = "pauseproperty"
    aliases = ["propertypause"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        fragment = self.args.strip().lower()

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
                caller.msg("You carry multiple deeds. Usage: pauseproperty <fragment>")
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = pause_property_operation_for_owner(caller, holding, True)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdResumePropertyOperation(Command):
    """Resume property income ticks. Usage: resumeproperty [deed fragment]"""

    key = "resumeproperty"
    aliases = ["propertyresume"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        fragment = self.args.strip().lower()

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
                caller.msg("You carry multiple deeds. Usage: resumeproperty <fragment>")
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = pause_property_operation_for_owner(caller, holding, False)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdRetoolPropertyOperation(Command):
    """
    Change operation type (fee applies). Usage:
      retoolproperty rent|floor|line [deed fragment]
    """

    key = "retoolproperty"
    aliases = ["propertyretool"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        parts = self.args.strip().split()
        if not parts or parts[0].lower() not in ("rent", "floor", "line"):
            caller.msg("Usage: retoolproperty rent|floor|line [deed fragment]")
            return
        kind = parts[0].lower()
        fragment = " ".join(parts[1:]).strip().lower()

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
                caller.msg(f"No property deed matches '{fragment}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg("You carry multiple deeds. Usage: retoolproperty <kind> <fragment>")
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = retool_property_operation_for_owner(caller, holding, kind)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdListPropertyDeed(Command):
    """
    List a carried property deed on the hub market. Usage:
      listpropertydeed <price> [deed fragment]
    """

    key = "listpropertydeed"
    aliases = ["propertydeedlist"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        parts = self.args.strip().split()
        if not parts:
            caller.msg("Usage: listpropertydeed <price> [deed fragment]")
            return

        price_token = parts[0]
        try:
            price = int(price_token)
        except ValueError:
            caller.msg("Price must be a number.")
            return

        fragment = " ".join(parts[1:]).strip().lower()
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
                caller.msg(f"No property deed matches '{fragment}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg("You carry multiple deeds. Usage: listpropertydeed <price> <fragment>")
                return
            claim = deeds[0]

        ok, msg = list_property_deed_for_sale(caller, claim.id, price)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdBuyPropertyDeed(Command):
    """
    Buy a property deed listed on the hub market. Usage:
      buypropertydeed <claim dbref #id or numeric id>
    """

    key = "buypropertydeed"
    aliases = ["propertydeedbuy"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        arg = self.args.strip()
        if not arg:
            caller.msg("Usage: buypropertydeed <claim id>")
            return
        arg = arg.lstrip("#")
        try:
            cid = int(arg)
        except ValueError:
            caller.msg("Claim id must be a number (e.g. #123 or 123).")
            return

        ok, msg = buy_listed_property_deed(caller, cid)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdUpgradePropertyStructure(Command):
    """
    Buy the next level of a structure upgrade (deed carried).

    Usage:
      upgradeproperty <structure id> <upgrade_key> [deed fragment]
    """

    key = "upgradeproperty"
    aliases = ["propertyupgrade", "propertystuctureupgrade"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        raw = self.args.strip().split(None, 2)
        if len(raw) < 2:
            caller.msg("Usage: upgradeproperty <structure id> <upgrade_key> [deed fragment]")
            return
        try:
            sid = int(raw[0].lstrip("#"))
        except ValueError:
            caller.msg("Structure id must be a number.")
            return
        upgrade_key = raw[1].lower()
        fragment = raw[2].strip().lower() if len(raw) > 2 else ""

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
                caller.msg(f"No property deed matches '{fragment}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg(
                    "You carry multiple deeds. Usage: upgradeproperty <id> <upgrade_key> <fragment>"
                )
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = purchase_structure_upgrade_for_owner(caller, holding, sid, upgrade_key)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdBuyPropertyExtraSlot(Command):
    """
    Purchase +1 structure capacity slot on a carried deed's parcel.

    Usage:
      buypropertyslot [deed fragment]
    """

    key = "buypropertyslot"
    aliases = ["propertyslot", "propertyextrslot"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        fragment = self.args.strip().lower()

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
                caller.msg("You carry multiple deeds. Usage: buypropertyslot <fragment>")
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = purchase_extra_structure_slot_for_owner(caller, holding)
        caller.msg(msg if ok else f"|r{msg}|n")


class CmdResolvePropertyIncident(Command):
    """
    Resolve an open incident on a carried deed's parcel (may charge credits).

    Usage:
      resolveincident <event_id>
      resolveincident <event_id> <deed fragment>
    """

    key = "resolveincident"
    aliases = ["resolvepropertyincident", "propertyresolve"]
    help_category = "Property"

    def func(self):
        caller = self.caller
        parts = self.args.strip().split()
        if len(parts) < 1:
            caller.msg("Usage: resolveincident <event_id> [deed fragment]")
            return
        event_id = parts[0].strip()
        fragment = " ".join(parts[1:]).strip().lower()

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
                caller.msg(f"No property deed matches '{fragment}'.")
                return
        else:
            if len(deeds) > 1:
                caller.msg(
                    "You carry multiple deeds. Usage: resolveincident <event_id> <deed fragment>"
                )
                return
            claim = deeds[0]

        lot = getattr(claim.db, "lot_ref", None)
        holding = getattr(lot.db, "holding_ref", None) if lot else None
        if not holding:
            caller.msg("No development record for that parcel.")
            return

        ok, msg = resolve_property_incident_for_owner(caller, holding, event_id)
        caller.msg(msg if ok else f"|r{msg}|n")
