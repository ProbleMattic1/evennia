"""
Autonomous Hauler system.

HaulerEngine   - Global script; processes hauler routes on schedule.
Helpers        - effective_capacity, effective_cycle_seconds, resolve_room.
"""

from datetime import UTC, datetime, timedelta

from evennia import search_object, search_tag

from world.time import MINING_DELIVERY_PERIOD, ceil_period, to_iso, utc_now
from evennia.utils import logger

from .scripts import Script
from .mining import get_commodity_bid


HAULER_ENGINE_INTERVAL = 1800   # 30 min wake
HAULER_CYCLE_BASE_HOURS = 4.0   # base cycle time per hauler
CYCLE_REDUCTION_PER_AUTOMATION = 0.5  # hours saved per automation level
CAPACITY_BONUS_PER_EXPANSION = 0.25   # +25% per cargo_expansion level


def _now():
    return datetime.now(UTC)


def _parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def _fmt_ts(dt):
    return dt.isoformat() if dt else None


def resolve_room(ref):
    """Resolve room from key string, dbref, or object. Returns None if invalid."""
    if ref is None:
        return None
    if hasattr(ref, "contents"):  # already a room/object
        return ref
    key = str(ref).strip()
    if not key:
        return None
    matches = search_object(key)
    for obj in matches:
        if hasattr(obj, "contents"):  # room-like
            return obj
    return None


def effective_capacity(hauler):
    """Cargo capacity including cargo_expansion upgrades."""
    base = float(hauler.db.cargo_capacity_tons or 0)
    if base <= 0:
        return 0.0
    upgrades = hauler.db.hauler_upgrades or {}
    exp_level = int(upgrades.get("cargo_expansion", 0) or 0)
    mod = 1.0 + (CAPACITY_BONUS_PER_EXPANSION * exp_level)
    return round(base * mod, 2)


def effective_cycle_seconds(hauler):
    """Cycle interval in seconds including automation upgrades."""
    base_hours = float(hauler.db.hauler_base_cycle_hours or HAULER_CYCLE_BASE_HOURS)
    upgrades = hauler.db.hauler_upgrades or {}
    aut_level = int(upgrades.get("automation", 0) or 0)
    reduction = CYCLE_REDUCTION_PER_AUTOMATION * aut_level
    hours = max(1.0, base_hours - reduction)
    return int(hours * 3600)


def get_hauler_next_cycle_at(hauler):
    return _parse_ts(hauler.db.hauler_next_cycle_at)


def set_hauler_next_cycle(hauler):
    secs = effective_cycle_seconds(hauler)
    raw = utc_now() + timedelta(seconds=secs)
    hauler.db.hauler_next_cycle_at = to_iso(ceil_period(raw, MINING_DELIVERY_PERIOD))


def get_mining_storage_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining"):
            return obj
    return None


def get_refinery_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("refinery", category="mining"):
            return obj
    return None


def get_site_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("mining_site", category="mining"):
            return obj
    return None


def hauler_process_one(hauler):
    """
    Run one step of the hauler's route. Returns (did_work, message).
    State: at_mine -> loading -> transit_refinery -> unloading -> transit_mine
    """
    from typeclasses.mining import RESOURCE_CATALOG

    owner = hauler.db.hauler_owner
    mine_ref = hauler.db.hauler_mine_room
    refinery_ref = hauler.db.hauler_refinery_room
    state = (hauler.db.hauler_state or "at_mine").strip().lower()

    mine_room = resolve_room(mine_ref)
    refinery_room = resolve_room(refinery_ref)

    if not mine_room or not refinery_room:
        return False, "Hauler route invalid (mine or refinery room not found)."

    if not owner:
        return False, "Hauler has no owner."

    loc = hauler.location
    if not loc:
        return False, "Hauler has no location."

    cap = effective_capacity(hauler)
    if cap <= 0:
        return False, "Hauler has no cargo capacity."

    # ---- At mine: load from owner's linked storage ----
    if state == "at_mine":
        if loc != mine_room:
            hauler.move_to(mine_room, quiet=True, move_hooks=False)
            loc = mine_room
        site = get_site_in_room(loc)
        if not site or site.db.owner != owner:
            return False, "No owned mining site at mine location."
        storage = site.db.linked_storage
        if not storage:
            return False, "Mining site has no linked storage."
        inv = storage.db.inventory or {}
        if not inv:
            set_hauler_next_cycle(hauler)
            return True, "No ore in storage — next cycle scheduled."
        space = cap - hauler.cargo_total_mass()
        if space <= 0:
            set_hauler_next_cycle(hauler)
            return True, "Cargo full — next cycle scheduled."
        loaded = {}
        for key, avail in list(inv.items()):
            if space <= 0:
                break
            to_load = min(float(avail), space)
            if to_load <= 0:
                continue
            try:
                actual = hauler.load_cargo(key, to_load)
            except ValueError:
                continue
            if actual > 0:
                storage.withdraw(key, actual)
                loaded[key] = loaded.get(key, 0) + actual
                space -= actual
        if not loaded:
            set_hauler_next_cycle(hauler)
            return True, "Could not load ore — next cycle scheduled."
        hauler.db.hauler_state = "transit_refinery"
        parts = [f"{RESOURCE_CATALOG.get(k, {}).get('name', k)}: {v}t" for k, v in loaded.items()]
        return True, f"Loaded {', '.join(parts)}. En route to refinery."

    # ---- Transit to refinery ----
    if state == "transit_refinery":
        hauler.move_to(refinery_room, quiet=True, move_hooks=False)
        hauler.db.hauler_state = "unloading"
        return True, f"Arrived at {refinery_room.key}. Unloading."

    # ---- At refinery: unload into receiving storage or miner queue ----
    if state == "unloading":
        if loc != refinery_room:
            hauler.move_to(refinery_room, quiet=True, move_hooks=False)
            loc = refinery_room
        cargo = hauler.db.cargo or {}
        if not cargo:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "Cargo empty — returning to mine."

        delivery_mode = (hauler.db.hauler_delivery_mode or "sell").lower()

        if delivery_mode == "process":
            refinery = get_refinery_in_room(loc)
            if refinery:
                ore_queue = dict(refinery.db.miner_ore_queue or {})
                owner_id = str(owner.id) if owner else None
                if owner_id:
                    owner_queue = dict(ore_queue.get(owner_id, {}))
                    total_queued = 0.0
                    for key, tons in list(cargo.items()):
                        removed = hauler.unload_cargo(key, tons)
                        if removed > 0:
                            owner_queue[key] = round(
                                float(owner_queue.get(key, 0)) + removed, 2
                            )
                            total_queued += removed
                    ore_queue[owner_id] = owner_queue
                    refinery.db.miner_ore_queue = ore_queue
                    hauler.db.hauler_state = "transit_mine"
                    set_hauler_next_cycle(hauler)
                    return True, (
                        f"Queued {total_queued:.1f}t for processing at {refinery.key}. "
                        f"Returning to mine."
                    )

        # "sell" mode (default) or fallback when no refinery found for process mode
        storage = get_mining_storage_in_room(loc)
        if not storage:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "No receiving storage at refinery — returning to mine."

        gross_total = 0
        for key, tons in list(cargo.items()):
            removed = hauler.unload_cargo(key, tons)
            if removed > 0:
                inv = storage.db.inventory or {}
                inv[key] = round(float(inv.get(key, 0)) + removed, 2)
                storage.db.inventory = inv
                if delivery_mode == "sell":
                    price = get_commodity_bid(key, location=loc)
                    gross_total += int(removed * price)

        if delivery_mode == "sell" and gross_total > 0 and owner:
            from typeclasses.economy import get_economy
            from typeclasses.refining import RAW_SALE_FEE_RATE, split_raw_sale_payout

            net, fee = split_raw_sale_payout(gross_total, RAW_SALE_FEE_RATE)
            econ = get_economy(create_missing=True)
            owner_acct = econ.get_character_account(owner)
            plant_acct = "vendor:processing-plant"
            econ.ensure_account(plant_acct, opening_balance=0)
            econ.deposit(owner_acct, net, memo=f"Ore sale (net) at {loc.key}")
            if fee > 0:
                econ.deposit(plant_acct, fee, memo=f"Plant raw hassle fee at {loc.key}")
            owner.db.credits = econ.get_character_balance(owner)
            if owner.sessions.count():
                owner.msg(
                    f"|g[Hauler: {hauler.key}]|n Ore sold — gross |y{gross_total:,}|n cr, "
                    f"hassle fee ({int(RAW_SALE_FEE_RATE * 100)}%) |r{fee:,}|n cr, "
                    f"net |g{net:,}|n cr deposited."
                )

        hauler.db.hauler_state = "transit_mine"
        set_hauler_next_cycle(hauler)
        return True, f"Unloaded at {storage.key}. Returning to mine."

    # ---- Transit back to mine ----
    if state == "transit_mine":
        hauler.move_to(mine_room, quiet=True, move_hooks=False)
        hauler.db.hauler_state = "at_mine"
        set_hauler_next_cycle(hauler)
        return True, f"Back at {mine_room.key}. Ready for next load."

    hauler.db.hauler_state = "at_mine"
    return False, "Unknown state; reset to at_mine."


class HaulerEngine(Script):
    """
    Global script for autonomous hauler routes.
    Wakes every 30 min, processes haulers whose next_cycle_at has passed.
    """

    def at_script_creation(self):
        self.key = "hauler_engine"
        self.desc = "Drives autonomous hauler routes (mine <-> refinery)."
        self.persistent = True
        self.interval = HAULER_ENGINE_INTERVAL
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self, **kwargs):
        now = _now()
        haulers = search_tag("autonomous_hauler", category="mining")
        processed = 0
        errors = 0

        for hauler in haulers:
            try:
                if not getattr(hauler.db, "is_vehicle", False):
                    continue
                if not hauler.db.hauler_owner:
                    continue
                next_at = get_hauler_next_cycle_at(hauler)
                if next_at is None:
                    set_hauler_next_cycle(hauler)
                    continue
                if next_at > now:
                    continue

                did_work, msg = hauler_process_one(hauler)
                if did_work:
                    logger.log_info(f"[hauler_engine] {hauler.key}: {msg}")
                    owner = hauler.db.hauler_owner
                    if owner and hasattr(owner, "sessions") and owner.sessions.count():
                        owner.msg(f"|w[Hauler: {hauler.key}]|n {msg}")
                    processed += 1

            except Exception as err:
                errors += 1
                logger.log_err(f"[hauler_engine] Error on {getattr(hauler, 'key', '?')}: {err}")

        if processed or errors:
            logger.log_info(f"[hauler_engine] Tick — {processed} cycle(s), {errors} error(s).")
