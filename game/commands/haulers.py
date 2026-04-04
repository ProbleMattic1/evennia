"""
Hauler commands — assign, upgrade, status, release.

CmdBuyHauler has been removed; haulers are now bundled inside mining packages
and delivered automatically via CmdBuy at the Mining Outfitters.
"""

from commands.command import Command
from evennia import search_object

from typeclasses.haulers import (
    HAULER_ENGINE_INTERVAL,
    HAULER_PICKUP_OFFSET_SEC,
    effective_capacity,
    format_next_hauler_run_utc,
    resolve_room,
    set_hauler_next_cycle,
)


# ---------------------------------------------------------------------------
# Upgrade catalog (slot -> level -> price_cr)
# ---------------------------------------------------------------------------

HAULER_UPGRADES = {
    "cargo_expansion": {1: 5000, 2: 12000},
    "automation": {1: 8000, 2: 12000},
    "reliability": {1: 4000},
}


def _find_owned_hauler(caller, name):
    owned = caller.db.owned_vehicles or []
    candidates = []
    for entry in owned:
        obj = entry if hasattr(entry, "key") else (search_object(entry)[0] if search_object(entry) else None)
        if not obj:
            continue
        if not obj.tags.has("autonomous_hauler", category="mining"):
            continue
        if not name or name.lower() in (obj.key or "").lower():
            candidates.append(obj)
    return candidates[0] if candidates else None


def _update_owned_vehicles(owner, vehicle):
    owned = owner.db.owned_vehicles or []
    if vehicle not in owned:
        owned.append(vehicle)
    owner.db.owned_vehicles = owned


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class CmdAssignHauler(Command):
    """
    Assign a hauler to a mine->refinery route.

    Usage:
      assignhauler <hauler> <mine> <refinery>

    Example:
      assignhauler Mk Vektor Aurnom
    """

    key = "assignhauler"
    aliases = ["sethauler", "haulerroute"]
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        if len(args) < 3:
            caller.msg("Usage: assignhauler <hauler> <mine> <refinery>")
            return

        hauler_name = args[0]
        mine_key = args[1]
        refinery_key = args[2]

        hauler = _find_owned_hauler(caller, hauler_name)
        if not hauler:
            caller.msg(f"You don't own an autonomous hauler matching '{hauler_name}'.")
            return

        mine_room = resolve_room(mine_key)
        refinery_room = resolve_room(refinery_key)
        if not mine_room:
            caller.msg(f"Mine room '{mine_key}' not found.")
            return
        if not refinery_room:
            caller.msg(f"Refinery room '{refinery_key}' not found.")
            return

        site = None
        for obj in mine_room.contents:
            if obj.tags.has("mining_site", category="mining") and obj.db.owner == caller:
                site = obj
                break
        if not site:
            caller.msg(f"You don't own a mining site in {mine_room.key}.")
            return

        site.schedule_next_cycle()
        hauler.db.hauler_mine_room = mine_room
        hauler.db.hauler_refinery_room = refinery_room
        hauler.db.hauler_destination_room = None
        hauler.db.hauler_state = "at_mine"
        hauler.move_to(mine_room, quiet=True)
        set_hauler_next_cycle(hauler)

        caller.msg(
            f"|w{hauler.key}|n assigned: {mine_room.key} -> {refinery_room.key}. "
            f"Next autonomous run: |c{format_next_hauler_run_utc(hauler)}|n "
            f"(backlog or in-flight = as fast as the {HAULER_ENGINE_INTERVAL // 60}m dispatch loop allows; "
            f"empty hopper at mine = grid: last deposit + {HAULER_PICKUP_OFFSET_SEC // 60}m or next slot)."
        )


class CmdUpgradeHauler(Command):
    """
    Apply an upgrade to a hauler (costs credits).

    Usage:
      upgradehauler <hauler> <upgrade> [level]

    Upgrades: cargo_expansion (1-2), automation (1-2, legacy tier interval display),
    reliability (1)
    """

    key = "upgradehauler"
    aliases = ["haulerupgrade"]
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        args = self.args.strip().split(None, 2)
        if len(args) < 2:
            caller.msg("Usage: upgradehauler <hauler> <upgrade> [level]")
            caller.msg("Upgrades: cargo_expansion, automation, reliability")
            return

        hauler = _find_owned_hauler(caller, args[0])
        if not hauler:
            caller.msg(f"You don't own a hauler matching '{args[0]}'.")
            return

        upgrade_slot = args[1].lower().replace("-", "_")
        level = int(args[2]) if len(args) > 2 else 1

        if upgrade_slot not in HAULER_UPGRADES:
            caller.msg(f"Unknown upgrade '{upgrade_slot}'. Valid: {', '.join(HAULER_UPGRADES)}")
            return

        levels = HAULER_UPGRADES[upgrade_slot]
        if level not in levels:
            caller.msg(f"Level {level} not available. Options: {list(levels.keys())}")
            return

        price = levels[level]
        current = (hauler.db.hauler_upgrades or {}).get(upgrade_slot, 0)
        if current >= level:
            caller.msg(f"|w{hauler.key}|n already has {upgrade_slot} level {current} or higher.")
            return

        from typeclasses.economy import get_economy
        econ = get_economy(create_missing=True)
        balance = econ.get_character_balance(caller)
        if balance < price:
            caller.msg(f"{upgrade_slot} level {level} costs |y{price:,}|n cr. You have |y{balance:,}|n cr.")
            return

        acct = econ.get_character_account(caller)
        econ.withdraw(acct, price, memo=f"Hauler upgrade: {upgrade_slot} L{level}")
        caller.db.credits = econ.get_character_balance(caller)

        upgrades = dict(hauler.db.hauler_upgrades or {})
        upgrades[upgrade_slot] = level
        hauler.db.hauler_upgrades = upgrades

        caller.msg(f"|g{hauler.key}|n upgraded: {upgrade_slot} level {level} (|y{price:,}|n cr).")


class CmdHaulerStatus(Command):
    """
    Show status of your haulers.

    Usage:
      haulerstatus [hauler]
    """

    key = "haulerstatus"
    aliases = ["haulers", "myhaulers"]
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        owned = caller.db.owned_vehicles or []
        haulers = []
        for e in owned:
            h = e if hasattr(e, "key") else (search_object(e)[0] if search_object(e) else None)
            if h and h.tags.has("autonomous_hauler", category="mining"):
                haulers.append(h)

        if not haulers:
            caller.msg("You don't own any autonomous haulers. Buy one at a hauler depot.")
            return

        name = self.args.strip()
        if name:
            haulers = [h for h in haulers if name.lower() in (h.key or "").lower()]
            if not haulers:
                caller.msg(f"No hauler matching '{name}'.")
                return

        lines = ["|wYour Haulers|n"]
        for h in haulers:
            loc = h.location.key if h.location else "?"
            state = h.db.hauler_state or "idle"
            mine = resolve_room(h.db.hauler_mine_room)
            dest_ref = getattr(h.db, "hauler_destination_room", None) or h.db.hauler_refinery_room
            ref = resolve_room(dest_ref)
            route = f"{mine.key if mine else '?'} -> {ref.key if ref else '?'}" if (mine or ref) else "unassigned"
            cap = effective_capacity(h)
            next_str = format_next_hauler_run_utc(h)
            upgrades = h.db.hauler_upgrades or {}
            up_str = ", ".join(f"{k}:{v}" for k, v in upgrades.items()) if upgrades else "none"
            lines.append(f"  |w{h.key}|n")
            lines.append(f"    Location: {loc}  State: {state}")
            lines.append(f"    Route: {route}")
            if getattr(caller.db, "haul_delivers_to_local_raw_storage", False) and getattr(
                h.db, "hauler_destination_room", None
            ):
                del_note = "Delivery: local raw reserve (no plant payout on unload)"
            else:
                del_note = "Delivery: Ore Receiving Bay at plant (paid on unload)"
            lines.append(
                f"    Capacity: {cap}t  Schedule: backlog/transit = continuous; empty at mine = grid "
                f"(deposit + {HAULER_PICKUP_OFFSET_SEC // 60}m); dispatch every {HAULER_ENGINE_INTERVAL // 60}m  "
                f"Next: {next_str}  {del_note}  Upgrades: {up_str}"
            )
        caller.msg("\n".join(lines))


class CmdSetDeliveryMode(Command):
    """
    Legacy command — hauler delivery is fixed.

    Usage:
      setdelivery <hauler> <anything>

    Autonomous haulers unload into the plant |wOre Receiving Bay|n; the treasury pays
    you on delivery (plant raw purchase). Use |wfeedrefinery|n to move ore from the bay
    into refining when you want processing; |wcollectrefined|n for refined payout.
    Personal processors still use |wfeedprocessor|n from your assigned storage in that room.
    """

    key = "setdelivery"
    aliases = ["deliverymode", "setdeliverymode"]
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        if len(args) < 1:
            caller.msg(
                "At the processing plant, haulers unload to the Ore Receiving Bay and you are paid on delivery. "
                "Use |wassignhauler|n to set the destination room. "
                "See |whelp feedrefinery|n, |whelp collectrefined|n, and |whelp feedprocessor|n."
            )
            return
        caller.msg(
            "|wDelivery mode is no longer configurable.|n At the plant, haulers unload into the "
            "Ore Receiving Bay and you are paid on delivery. Use |wfeedrefinery|n to feed the "
            "refinery from the bay (or your assigned silo is queued first when you use feedrefinery). "
            "|wcollectrefined|n collects refined output. For a personal processor, use |wfeedprocessor|n."
        )


class CmdReleaseHauler(Command):
    """
    Release a hauler from autonomous duty (keeps the ship).

    Usage:
      releasehauler <hauler>
    """

    key = "releasehauler"
    aliases = ["unassignhauler"]
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        hauler = _find_owned_hauler(caller, self.args.strip())
        if not hauler:
            caller.msg("You don't own an autonomous hauler matching that name.")
            return

        from world.hauler_dispatch import delete_hauler_dispatch_row

        hauler.tags.remove("autonomous_hauler", category="mining")
        hauler.db.hauler_owner = None
        hauler.db.hauler_mine_room = None
        hauler.db.hauler_refinery_room = None
        hauler.db.hauler_destination_room = None
        hauler.db.hauler_state = "idle"

        delete_hauler_dispatch_row(hauler)

        caller.msg(f"|w{hauler.key}|n is no longer an autonomous hauler. You can still pilot it normally.")


class CmdHaulerDueNow(Command):
    """
    Make your hauler eligible on the next HaulerEngine tick (testing / ops).

    Usage:
      haulerduenow <hauler>
    """

    key = "haulerduenow"
    locks = "cmd:perm(Builder)"
    help_category = "Haulers"

    def func(self):
        caller = self.caller
        name = self.args.strip()
        if not name:
            caller.msg("Usage: haulerduenow <hauler>")
            return
        hauler = _find_owned_hauler(caller, name)
        if not hauler:
            caller.msg("You don't own an autonomous hauler matching that name.")
            return
        hauler.db.hauler_next_cycle_at = "1970-01-01T00:00:00+00:00"
        from world.hauler_dispatch import sync_hauler_dispatch_row

        sync_hauler_dispatch_row(hauler)
        caller.msg(
            f"|w{hauler.key}|n is due now (runs on next hauler engine tick, within ~{HAULER_ENGINE_INTERVAL // 60}m)."
        )
