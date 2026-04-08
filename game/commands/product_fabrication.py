"""Catalog fabrication hold (parts) and station fabricator."""

from __future__ import annotations

from commands.command import Command

from typeclasses.fabricator import STATION_FABRICATOR_TAG, STATION_FABRICATOR_TAG_CATEGORY
from typeclasses.processors import PortableProcessor
from typeclasses.refining import Refinery
from world.part_inventory import part_inventory_for_json
from world.part_withdraw import withdraw_attributed_refinery_parts, withdraw_portable_processor_parts
from world.product_catalog import FABRICATION_RECIPES


def _main_refinery_in_room(room):
    if not room:
        return None
    for o in room.contents:
        if o.is_typeclass(Refinery, exact=False):
            return o
    return None


def _fabricator_in_room(room):
    if not room:
        return None
    for o in room.contents:
        if o.tags.has(STATION_FABRICATOR_TAG, category=STATION_FABRICATOR_TAG_CATEGORY):
            return o
    return None


def _match_fabrication_recipe(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    for rid, row in FABRICATION_RECIPES.items():
        if q == rid.lower():
            return rid
        name = (row.get("name") or "").lower()
        if q in name or q in rid.lower():
            return rid
    return None


class CmdPartsHold(Command):
    """
    Show refined parts held for fabrication (not physical inventory).

    Usage:
      partshold
    """

    key = "partshold"
    aliases = ["parts", "fabparts"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        rows = part_inventory_for_json(self.caller)
        if not rows:
            self.caller.msg("Your fabrication hold is empty.")
            return
        lines = ["|wFabrication hold:|n"]
        for r in rows:
            lines.append(f"  {r['partId']}: {r['units']} units")
        self.caller.msg("\n".join(lines))


class CmdWithdrawRefinedParts(Command):
    """
    Move attributed refinery output into your fabrication hold (no credits).

    Usage:
      withdrawrefinedparts all
      withdrawrefinedparts <part_key> <units> [<part_key> <units> ...]

    Use at the refinery chamber (same room as the plant refinery).
    Part keys match refining outputs (e.g. refined_iron).
    """

    key = "withdrawrefinedparts"
    aliases = ["withdrawparts", "refinedtoparts"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        loc = caller.location
        ref = _main_refinery_in_room(loc)
        if not ref:
            self.caller.msg("You must be in a refinery chamber with a plant refinery.")
            return

        args = (self.args or "").strip().split()
        if not args:
            self.caller.msg("Usage: withdrawrefinedparts all  OR  withdrawrefinedparts refined_iron 2 ...")
            return

        if args[0].lower() == "all":
            ok, msg = withdraw_attributed_refinery_parts(ref, caller, withdraw_all=True)
        else:
            if len(args) % 2 != 0:
                self.caller.msg("Usage: pairs of <part_key> <units>.")
                return
            amounts = {}
            i = 0
            while i < len(args):
                k = args[i]
                try:
                    u = float(args[i + 1])
                except ValueError:
                    self.caller.msg(f"Invalid number: {args[i + 1]!r}")
                    return
                amounts[k] = amounts.get(k, 0.0) + u
                i += 2
            ok, msg = withdraw_attributed_refinery_parts(
                ref, caller, withdraw_all=False, amounts=amounts
            )

        if ok:
            self.caller.msg(msg)
        else:
            self.caller.msg(f"|r{msg}|n")


class CmdWithdrawProcessorParts(Command):
    """
    Move your portable processor output into your fabrication hold.

    Usage:
      withdrawprocessorparts <processor name fragment> all
      withdrawprocessorparts <fragment> <part_key> <units> ...
    """

    key = "withdrawprocessorparts"
    aliases = ["processorparts"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Usage: withdrawprocessorparts <name fragment> all|...")
            return
        parts = raw.split()
        frag = parts[0]
        rest = parts[1:]
        if not rest:
            self.caller.msg("Specify all or part amounts.")
            return

        candidates = []
        for parent in (caller.location, caller):
            if not parent:
                continue
            for o in parent.contents:
                if not o.is_typeclass(PortableProcessor, exact=False):
                    continue
                if getattr(o.db, "owner", None) != caller:
                    continue
                if frag.lower() in o.key.lower():
                    candidates.append(o)

        if not candidates:
            self.caller.msg("No matching portable processor found here or in your inventory.")
            return
        proc = candidates[0]

        if rest[0].lower() == "all":
            ok, msg = withdraw_portable_processor_parts(proc, caller, withdraw_all=True)
        else:
            if len(rest) % 2 != 0:
                self.caller.msg("Usage: pairs of <part_key> <units> after the fragment.")
                return
            amounts = {}
            i = 0
            while i < len(rest):
                k = rest[i]
                try:
                    u = float(rest[i + 1])
                except ValueError:
                    self.caller.msg(f"Invalid number: {rest[i + 1]!r}")
                    return
                amounts[k] = amounts.get(k, 0.0) + u
                i += 2
            ok, msg = withdraw_portable_processor_parts(
                proc, caller, withdraw_all=False, amounts=amounts
            )

        if ok:
            self.caller.msg(msg)
        else:
            self.caller.msg(f"|r{msg}|n")


class CmdFabricateProduct(Command):
    """
    Fabricate a catalog product at a Station Fabrication Kiosk using your hold.

    Usage:
      fabricateproduct <recipe id or name fragment> [<batches>]

    Example:
      fabricateproduct multitool
      fabricateproduct fab.supply_multitool_v1 2
    """

    key = "fabricateproduct"
    aliases = ["fabproduct", "makeproduct"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        loc = caller.location
        fab = _fabricator_in_room(loc)
        if not fab:
            self.caller.msg("No station fabricator here. Try the refinery chamber kiosk.")
            return

        args = (self.args or "").strip().split()
        if not args:
            self.caller.msg("Usage: fabricateproduct <recipe> [batches]")
            return

        batches = 1
        if len(args) >= 2:
            try:
                batches = int(args[-1])
                query = " ".join(args[:-1])
            except ValueError:
                query = " ".join(args)
        else:
            query = args[0]

        rid = _match_fabrication_recipe(query)
        if not rid:
            self.caller.msg(f"No fabrication recipe matches {query!r}.")
            return

        n, msg = fab.fabricate(caller, rid, batches=batches)
        if n > 0:
            self.caller.msg(msg)
        else:
            self.caller.msg(f"|r{msg}|n")
