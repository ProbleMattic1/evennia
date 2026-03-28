"""
Autonomous Hauler system.

HaulerEngine   - Global script; processes hauler routes on schedule.
Helpers        - effective_capacity, effective_cycle_seconds (nominal tier), resolve_room.

Schedule: pickup at MiningSite.db.last_ore_deposit_at + HAULER_PICKUP_OFFSET_SEC when that
instant is still in the future; otherwise mine next_cycle_at + HAULER_PICKUP_OFFSET_SEC.
arm_hauler_pickup_after_mining_deposit calls set_hauler_next_cycle for matching haulers.
"""

from datetime import UTC, datetime, timedelta

from evennia import search_object, search_tag

from world.time import (
    HOUR,
    HAULER_ENGINE_INTERVAL_SEC,
    MINING_DELIVERY_PERIOD,
    to_iso,
    utc_now,
)
from evennia.utils import logger

from .scripts import Script


HAULER_ENGINE_INTERVAL = HAULER_ENGINE_INTERVAL_SEC
HAULER_CYCLE_BASE_HOURS = 4.0  # legacy Mk tier field on packages
CYCLE_REDUCTION_PER_AUTOMATION = 0.5  # kept for effective_cycle_seconds() compatibility
CAPACITY_BONUS_PER_EXPANSION = 0.25  # +25% per cargo_expansion level

HAULER_STAGGER_WINDOW_BASE_SEC = 6 * HOUR
HAULER_STAGGER_WINDOW_MIN_SEC = HOUR
HAULER_MAX_PIPELINE_STEPS = 12

HAULER_PICKUP_OFFSET_SEC = MINING_DELIVERY_PERIOD // 2

# Player-assigned ore silo at haul destination (plant or parcel). Ingested into
# per-owner refinery queues by RefineryEngine; not mixed into pooled plant input.
PLANT_PLAYER_STORAGE_TAG = "plant_player_ore_storage"
PLANT_PLAYER_STORAGE_CATEGORY = "mining"


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
    """
    Nominal "tier" interval in seconds (legacy Mk I/II/III hours field).
    Pickup cadence follows last_ore_deposit_at or mine next_cycle_at + HAULER_PICKUP_OFFSET_SEC; tier display only.
    """
    base_hours = float(hauler.db.hauler_base_cycle_hours or HAULER_CYCLE_BASE_HOURS)
    upgrades = hauler.db.hauler_upgrades or {}
    aut_level = int(upgrades.get("automation", 0) or 0)
    reduction = CYCLE_REDUCTION_PER_AUTOMATION * aut_level
    hours = max(1.0, base_hours - reduction)
    return int(hours * 3600)


def stagger_window_seconds(hauler):
    """Legacy helper used by hauler upgrades / status copy (not used for hauler run scheduling)."""
    upgrades = hauler.db.hauler_upgrades or {}
    aut_level = int(upgrades.get("automation", 0) or 0)
    window = HAULER_STAGGER_WINDOW_BASE_SEC >> aut_level
    return max(HAULER_STAGGER_WINDOW_MIN_SEC, window)


def compute_next_hauler_run_at(hauler, after: datetime | None = None) -> datetime:
    mine_room = resolve_room(hauler.db.hauler_mine_room)
    site = get_site_in_room(mine_room)
    owner = hauler.db.hauler_owner
    now_ref = (after or utc_now()).astimezone(UTC)
    if not site or site.db.owner != owner:
        raise RuntimeError(
            f"Hauler {hauler.key!r} has no owned mining site at hauler_mine_room"
        )
    mining_next = _parse_ts(site.db.next_cycle_at)
    if mining_next is None:
        raise RuntimeError(f"Mining site {site.key!r} has no next_cycle_at")
    mining_next = mining_next.astimezone(UTC)

    last_dep = _parse_ts(site.db.last_ore_deposit_at)
    if last_dep is not None:
        last_dep = last_dep.astimezone(UTC)
        from_deposit = last_dep + timedelta(seconds=HAULER_PICKUP_OFFSET_SEC)
        if from_deposit > now_ref:
            return from_deposit
        candidate = mining_next + timedelta(seconds=HAULER_PICKUP_OFFSET_SEC)
    else:
        candidate = mining_next

    while candidate <= now_ref:
        candidate += timedelta(seconds=MINING_DELIVERY_PERIOD)
    return candidate


def get_hauler_next_cycle_at(hauler):
    return _parse_ts(hauler.db.hauler_next_cycle_at)


def set_hauler_next_cycle(hauler, after: datetime | None = None):
    hauler.db.hauler_next_cycle_at = to_iso(compute_next_hauler_run_at(hauler, after=after))


def arm_hauler_pickup_after_mining_deposit(site):
    room = site.location
    owner = site.db.owner
    if not room or not owner:
        return
    for obj in room.contents:
        if not obj.tags.has("autonomous_hauler", category="mining"):
            continue
        if obj.db.hauler_owner != owner:
            continue
        if resolve_room(obj.db.hauler_mine_room) != room:
            continue
        set_hauler_next_cycle(obj)


def format_next_hauler_run_utc(hauler) -> str:
    """Short UTC timestamp for player messages."""
    dt = get_hauler_next_cycle_at(hauler)
    if not dt:
        return "not scheduled"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def get_mining_storage_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining"):
            return obj
    return None


def get_plant_player_storage(room, owner):
    """
    Player-assigned ore storage in the destination room (one object per owner per room).
    """
    if not room or not owner:
        return None
    for obj in room.contents:
        if not obj.tags.has(PLANT_PLAYER_STORAGE_TAG, category=PLANT_PLAYER_STORAGE_CATEGORY):
            continue
        if getattr(obj.db, "owner", None) == owner:
            return obj
    return None


def get_or_create_plant_player_storage(room, owner):
    """Create a tagged MiningStorage for this owner in room on first haul delivery."""
    from evennia import create_object

    from typeclasses.mining import MiningStorage

    existing = get_plant_player_storage(room, owner)
    if existing:
        return existing
    key = f"{owner.key}'s plant ore storage"
    st = create_object(
        MiningStorage,
        key=key,
        location=room,
        home=room,
    )
    st.db.owner = owner
    st.db.site = None
    st.tags.add(PLANT_PLAYER_STORAGE_TAG, category=PLANT_PLAYER_STORAGE_CATEGORY)
    st.tags.add("mining_storage", category="mining")
    st.locks.add("get:false()")
    return st


def get_player_destination_storage(room, owner):
    """
    Haulers always unload here: the player's assigned storage in this room.
    Prefers tagged plant silo; else any mining_storage with same owner; else creates silo.
    """
    if not room or not owner:
        return None
    p = get_plant_player_storage(room, owner)
    if p:
        return p
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining") and getattr(obj.db, "owner", None) == owner:
            return obj
    return get_or_create_plant_player_storage(room, owner)


def get_refinery_in_room(room):
    if not room:
        return None
    candidates = [
        o for o in room.contents if o.tags.has("refinery", category="mining")
    ]
    for o in candidates:
        if o.is_typeclass("typeclasses.refining.Refinery", exact=False):
            return o
    return candidates[0] if candidates else None


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

    # ---- At destination: always player-assigned storage (then distribution) ----
    if state == "unloading":
        if loc != refinery_room:
            hauler.move_to(refinery_room, quiet=True, move_hooks=False)
            loc = refinery_room
        cargo = hauler.db.cargo or {}
        if not cargo:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "Cargo empty — returning to mine."

        storage = get_player_destination_storage(loc, owner)
        if not storage:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "No player-assigned storage at destination — returning to mine."

        for key, tons in list(cargo.items()):
            removed = hauler.unload_cargo(key, tons)
            if removed > 0:
                inv = storage.db.inventory or {}
                inv[key] = round(float(inv.get(key, 0)) + removed, 2)
                storage.db.inventory = inv

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
    Wakes every HAULER_ENGINE_INTERVAL seconds. Each hauler due (hauler_next_cycle_at from last
    deposit or mine next_cycle) may advance up to HAULER_MAX_PIPELINE_STEPS state transitions
    per tick.
    """

    def at_script_creation(self):
        self.key = "hauler_engine"
        self.desc = "Drives autonomous hauler routes (mine <-> refinery)."
        self.persistent = True
        self.interval = HAULER_ENGINE_INTERVAL
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self, **kwargs):
        now = _now()
        haulers = search_tag("autonomous_hauler", category="mining")
        processed = 0
        errors = 0
        scanned = 0

        for hauler in haulers:
            try:
                if not getattr(hauler.db, "is_vehicle", False):
                    continue
                if not hauler.db.hauler_owner:
                    continue

                scanned += 1
                steps = 0
                while steps < HAULER_MAX_PIPELINE_STEPS:
                    next_at = get_hauler_next_cycle_at(hauler)
                    if next_at is None:
                        set_hauler_next_cycle(hauler)
                        break
                    if next_at > now:
                        break

                    did_work, msg = hauler_process_one(hauler)
                    steps += 1
                    if did_work:
                        logger.log_info(f"[hauler_engine] {hauler.key}: {msg}")
                        owner = hauler.db.hauler_owner
                        if owner and hasattr(owner, "sessions") and owner.sessions.count():
                            owner.msg(f"|w[Hauler: {hauler.key}]|n {msg}")
                        processed += 1
                    if not did_work:
                        break

                    next_after = get_hauler_next_cycle_at(hauler)
                    if next_after is not None and next_after > now:
                        break

            except Exception as err:
                errors += 1
                logger.log_err(f"[hauler_engine] Error on {getattr(hauler, 'key', '?')}: {err}")

        logger.log_info(
            f"[hauler_engine] Tick — scanned={scanned} step(s)={processed} error(s)={errors}"
        )
