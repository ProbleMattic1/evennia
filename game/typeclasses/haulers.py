"""
Autonomous Hauler system.

HaulerEngine   - Global script; processes hauler routes on schedule.
Helpers        - effective_capacity, effective_cycle_seconds (nominal tier), resolve_room.

Mining: pickup at last_ore_deposit_at + HAULER_PICKUP_OFFSET_SEC (half of MINING_DELIVERY_PERIOD)
when still in the future; otherwise next_cycle_at + that offset; grid step MINING_DELIVERY_PERIOD.

Flora: hourly FLORA_DELIVERY_PERIOD grid; pickup at last_flora_deposit_at +
FLORA_HAULER_PICKUP_OFFSET_SEC (fixed 15 min), or next_cycle_at + same offset; grid step
FLORA_DELIVERY_PERIOD.

arm_hauler_pickup_after_mining_deposit / arm_hauler_pickup_after_flora_deposit /
arm_hauler_pickup_after_fauna_deposit arm haulers tagged autonomous_hauler in category
mining / flora / fauna respectively.

At the processing plant, haulers normally unload into the shared Ore Receiving Bay; the treasury
pays the hauler owner (plant raw purchase). Owners with db.haul_delivers_to_local_raw_storage
instead unload into local raw reserve (tag local_raw_ore_storage) in db.haul_destination_room;
no treasury payout on that move. Assigned plant silos are fed via feedprocessor / feedrefinery
silo paths, not by the default autonomous hauler unload.
"""

from datetime import UTC, datetime, timedelta

from django.utils import timezone
from evennia import search_object
from evennia.objects.models import ObjectDB

from world.time import (
    FLORA_DELIVERY_PERIOD,
    FLORA_HAULER_PICKUP_OFFSET_SEC,
    HOUR,
    HAULER_ENGINE_INTERVAL_SEC,
    MAX_HAULERS_PER_ENGINE_TICK,
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

# Player-assigned ore silo at haul destination (plant or parcel). Queued into
# miner_ore_queue via feedrefinery / transfer_owner_plant_silo_to_miner_queue;
# not mixed into pooled plant input until then.
PLANT_PLAYER_STORAGE_TAG = "plant_player_ore_storage"
PLANT_PLAYER_STORAGE_CATEGORY = "mining"

LOCAL_RAW_STORAGE_TAG = "local_raw_ore_storage"
LOCAL_RAW_STORAGE_CATEGORY = "mining"

# Shared plant receiving bay (bootstrap + hauler unload + web UI). Canonical identity is this tag.
ORE_RECEIVING_BAY_TAG = "ore_receiving_bay"
ORE_RECEIVING_BAY_TAG_CATEGORY = "mining"


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
    Actual pickup times follow deposit + offset and the production grid (mining vs flora/fauna);
    this field is tier display / legacy upgrades only.
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


def _hauler_grid_params(hauler):
    """
    Return (site, delivery_period_sec, pickup_offset_sec, last_deposit_attr_name).
    Flora/fauna haulers: autonomous_hauler tag category flora or fauna. Mining: mining.
    """
    mine_room = resolve_room(hauler.db.hauler_mine_room)
    if hauler.tags.has("autonomous_hauler", category="fauna"):
        site = get_fauna_site_in_room(mine_room)
        return site, FLORA_DELIVERY_PERIOD, FLORA_HAULER_PICKUP_OFFSET_SEC, "last_fauna_deposit_at"
    if hauler.tags.has("autonomous_hauler", category="flora"):
        site = get_flora_site_in_room(mine_room)
        return site, FLORA_DELIVERY_PERIOD, FLORA_HAULER_PICKUP_OFFSET_SEC, "last_flora_deposit_at"
    site = get_site_in_room(mine_room)
    return site, MINING_DELIVERY_PERIOD, HAULER_PICKUP_OFFSET_SEC, "last_ore_deposit_at"


def compute_next_hauler_run_at(hauler, after: datetime | None = None) -> datetime:
    mine_room = resolve_room(hauler.db.hauler_mine_room)
    owner = hauler.db.hauler_owner
    now_ref = (after or utc_now()).astimezone(UTC)

    site, period_sec, offset_sec, last_dep_attr = _hauler_grid_params(hauler)

    if not site or site.db.owner != owner:
        raise RuntimeError(
            f"Hauler {hauler.key!r} has no owned production site at hauler_mine_room"
        )

    next_c = _parse_ts(site.db.next_cycle_at)
    if next_c is None:
        raise RuntimeError(f"Site {site.key!r} has no next_cycle_at")
    next_c = next_c.astimezone(UTC)

    last_dep = _parse_ts(getattr(site.db, last_dep_attr, None))
    offset = timedelta(seconds=offset_sec)
    step = timedelta(seconds=period_sec)

    if last_dep is not None:
        last_dep = last_dep.astimezone(UTC)
        from_deposit = last_dep + offset
        if from_deposit > now_ref:
            return from_deposit
        candidate = next_c + offset
    else:
        candidate = next_c

    if candidate <= now_ref:
        step_sec = step.total_seconds()
        delta_sec = (now_ref - candidate).total_seconds()
        k = int(delta_sec // step_sec) + 1
        candidate = candidate + timedelta(seconds=k * step_sec)
        if candidate <= now_ref:
            candidate += step
    return candidate


def get_hauler_next_cycle_at(hauler):
    return _parse_ts(hauler.db.hauler_next_cycle_at)


def set_hauler_next_cycle(hauler, after: datetime | None = None):
    hauler.db.hauler_next_cycle_at = to_iso(compute_next_hauler_run_at(hauler, after=after))
    try:
        from world.hauler_dispatch import sync_hauler_dispatch_row

        sync_hauler_dispatch_row(hauler)
    except Exception:
        logger.log_trace("sync_hauler_dispatch_row failed")


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


def arm_hauler_pickup_after_flora_deposit(site):
    room = site.location
    owner = site.db.owner
    if not room or not owner:
        return
    for obj in room.contents:
        if not obj.tags.has("autonomous_hauler", category="flora"):
            continue
        if obj.db.hauler_owner != owner:
            continue
        if resolve_room(obj.db.hauler_mine_room) != room:
            continue
        set_hauler_next_cycle(obj)


def arm_hauler_pickup_after_fauna_deposit(site):
    room = site.location
    owner = site.db.owner
    if not room or not owner:
        return
    for obj in room.contents:
        if not obj.tags.has("autonomous_hauler", category="fauna"):
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


def iter_plant_aggregated_raw_inventory(plant_room):
    """
    Sum raw tons by resource key for all intake tied to this processing plant room:
    the shared ore receiving bay, every player-assigned plant silo, and every
    local raw reserve in the room. Used for web “market snapshot” / plant intake
    views so totals are not limited to the pooled bay alone.
    """
    merged: dict[str, float] = {}

    def absorb(inv):
        for k, v in (inv or {}).items():
            kr = str(k)
            try:
                tons = float(v or 0)
            except (TypeError, ValueError):
                continue
            if tons <= 0:
                continue
            merged[kr] = merged.get(kr, 0.0) + tons

    bay = get_plant_ore_receiving_bay(plant_room)
    if bay:
        absorb(getattr(bay.db, "inventory", None))

    if not plant_room:
        return merged

    for obj in plant_room.contents:
        if not obj.tags.has("mining_storage", category="mining"):
            continue
        if obj.tags.has(PLANT_PLAYER_STORAGE_TAG, category=PLANT_PLAYER_STORAGE_CATEGORY):
            absorb(getattr(obj.db, "inventory", None))
        elif obj.tags.has(LOCAL_RAW_STORAGE_TAG, category=LOCAL_RAW_STORAGE_CATEGORY):
            absorb(getattr(obj.db, "inventory", None))

    return merged


def get_plant_ore_receiving_bay(room):
    """
    Shared plant raw intake: exactly one object per processing plant room, tagged
    ``ore_receiving_bay`` (and ``mining_storage``). Bootstrap creates it with key
    ``Ore Receiving Bay``; exact key is a secondary predicate for legacy rows
    before re-bootstrap tags exist.
    """
    if not room:
        return None
    for obj in room.contents:
        if not obj.tags.has("mining_storage", category="mining"):
            continue
        if obj.tags.has(PLANT_PLAYER_STORAGE_TAG, category=PLANT_PLAYER_STORAGE_CATEGORY):
            continue
        if obj.tags.has(LOCAL_RAW_STORAGE_TAG, category=LOCAL_RAW_STORAGE_CATEGORY):
            continue
        if obj.tags.has(ORE_RECEIVING_BAY_TAG, category=ORE_RECEIVING_BAY_TAG_CATEGORY):
            return obj
        if obj.key == "Ore Receiving Bay":
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


def get_local_raw_storage(room, owner):
    if not room or not owner:
        return None
    for obj in room.contents:
        if not obj.tags.has(LOCAL_RAW_STORAGE_TAG, category=LOCAL_RAW_STORAGE_CATEGORY):
            continue
        if getattr(obj.db, "owner", None) == owner:
            return obj
    return None


def ensure_local_raw_storage(room, owner, *, capacity_tons=500_000.0):
    """Marcus-style local raw reserve: one MiningStorage per owner in the given room."""
    from evennia import create_object

    from typeclasses.mining import MiningStorage

    existing = get_local_raw_storage(room, owner)
    if existing:
        return existing
    st = create_object(
        MiningStorage,
        key=f"{owner.key} Local Raw Reserve",
        location=room,
        home=room,
    )
    st.db.owner = owner
    st.db.site = None
    st.db.capacity_tons = float(capacity_tons)
    st.db.inventory = st.db.inventory or {}
    st.tags.add(LOCAL_RAW_STORAGE_TAG, category=LOCAL_RAW_STORAGE_CATEGORY)
    st.tags.add("mining_storage", category="mining")
    st.locks.add("get:false()")
    return st


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
    Player-assigned plant silo in this room (e.g. feedprocessor / feedrefinery silo path).
    Default autonomous haulers unload to Ore Receiving Bay; owners with
    haul_delivers_to_local_raw_storage use local raw reserve instead.
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


def get_flora_site_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("flora_site", category="flora"):
            return obj
    return None


def get_fauna_site_in_room(room):
    if not room:
        return None
    for obj in room.contents:
        if obj.tags.has("fauna_site", category="fauna"):
            return obj
    return None


def _hauler_raw_pipeline(hauler):
    if hauler.tags.has("autonomous_hauler", category="fauna"):
        return "fauna"
    if hauler.tags.has("autonomous_hauler", category="flora"):
        return "flora"
    return "mining"


def hauler_process_one(hauler):
    """
    Run one step of the hauler's route. Returns (did_work, message).
    State: at_mine -> loading -> transit_refinery -> unloading -> transit_mine
    """
    from typeclasses.fauna import FAUNA_RESOURCE_CATALOG
    from typeclasses.flora import FLORA_RESOURCE_CATALOG
    from typeclasses.mining import RESOURCE_CATALOG

    owner = hauler.db.hauler_owner
    mine_ref = hauler.db.hauler_mine_room
    dest_ref = getattr(hauler.db, "hauler_destination_room", None) or hauler.db.hauler_refinery_room
    state = (hauler.db.hauler_state or "at_mine").strip().lower()

    mine_room = resolve_room(mine_ref)
    dest_room = resolve_room(dest_ref)

    if not mine_room or not dest_room:
        return False, "Hauler route invalid (mine or destination room not found)."

    if not owner:
        return False, "Hauler has no owner."

    loc = hauler.location
    if not loc:
        return False, "Hauler has no location."

    cap = effective_capacity(hauler)
    if cap <= 0:
        return False, "Hauler has no cargo capacity."

    pipeline = _hauler_raw_pipeline(hauler)
    catalogs = {
        "mining": RESOURCE_CATALOG,
        "flora": FLORA_RESOURCE_CATALOG,
        "fauna": FAUNA_RESOURCE_CATALOG,
    }
    catalog = catalogs[pipeline]
    site_labels = {
        "mining": "mining site",
        "flora": "flora site",
        "fauna": "fauna site",
    }
    site_label = site_labels[pipeline]
    empty_msg = (
        "No harvest in storage — next cycle scheduled."
        if pipeline in ("flora", "fauna")
        else "No ore in storage — next cycle scheduled."
    )
    load_fail_msg = (
        "Could not load harvest — next cycle scheduled."
        if pipeline in ("flora", "fauna")
        else "Could not load ore — next cycle scheduled."
    )

    # ---- At mine: load from owner's linked storage ----
    if state == "at_mine":
        if loc != mine_room:
            hauler.move_to(mine_room, quiet=True, move_hooks=False)
            loc = mine_room
        if pipeline == "fauna":
            site = get_fauna_site_in_room(loc)
        elif pipeline == "flora":
            site = get_flora_site_in_room(loc)
        else:
            site = get_site_in_room(loc)
        if not site or site.db.owner != owner:
            return False, f"No owned {site_label} at mine location."
        storage = site.db.linked_storage
        if not storage:
            return False, f"{site_label.capitalize()} has no linked storage."
        inv = storage.db.inventory or {}
        if not inv:
            set_hauler_next_cycle(hauler)
            return True, empty_msg
        space = cap - hauler.cargo_total_mass()
        if space <= 0:
            hauler.db.hauler_state = "transit_refinery"
            return True, f"Full load — en route to {dest_room.key}."
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
            return True, load_fail_msg
        hauler.db.hauler_state = "transit_refinery"
        parts = [f"{catalog.get(k, {}).get('name', k)}: {v}t" for k, v in loaded.items()]
        return True, f"Loaded {', '.join(parts)}. En route to {dest_room.key}."

    # ---- Transit to destination ----
    if state == "transit_refinery":
        hauler.move_to(dest_room, quiet=True, move_hooks=False)
        hauler.db.hauler_state = "unloading"
        return True, f"Arrived at {dest_room.key}. Unloading."

    # ---- At destination: local raw reserve OR Ore Receiving Bay + treasury ------------
    if state == "unloading":
        if loc != dest_room:
            hauler.move_to(dest_room, quiet=True, move_hooks=False)
            loc = dest_room
        cargo = hauler.db.cargo or {}
        if not cargo:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "Cargo empty — returning to mine."

        use_local = bool(getattr(owner.db, "haul_delivers_to_local_raw_storage", False))
        if use_local:
            target = ensure_local_raw_storage(dest_room, owner)
            cap_tgt = float(getattr(target.db, "capacity_tons", 0) or 0)
            delivered = {}
            for key, tons in list(cargo.items()):
                t = float(tons)
                if t <= 0:
                    continue
                space = max(0.0, cap_tgt - target.total_mass())
                add = round(min(t, space), 2)
                if add <= 0:
                    continue
                removed = hauler.unload_cargo(key, add)
                if removed <= 0:
                    continue
                inv = target.db.inventory or {}
                inv[key] = round(float(inv.get(key, 0)) + removed, 2)
                target.db.inventory = inv
                delivered[key] = round(float(delivered.get(key, 0)) + removed, 2)

            if not delivered:
                hauler.db.hauler_state = "transit_mine"
                set_hauler_next_cycle(hauler)
                return True, "Local raw reserve full — could not unload. Returning to mine."

            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            owner.db.local_raw_storage = target
            try:
                from world.challenges.challenge_signals import emit as _c_emit
                from world.locator_zones import locator_zone_for_room

                mine_zone = locator_zone_for_room(mine_room, has_mining_site=True)
                _c_emit(owner, "hauler_tick", {"mine_zone": mine_zone, "pipeline": pipeline})
            except Exception:
                pass
            return True, (
                f"Unloaded to {target.key} ({sum(delivered.values()):.1f} t). Returning to mine."
            )

        bay = get_plant_ore_receiving_bay(dest_room)
        if not bay:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "No Ore Receiving Bay at destination — returning to mine."

        cap = float(getattr(bay.db, "capacity_tons", 0) or 0)
        delivered = {}
        for key, tons in list(cargo.items()):
            t = float(tons)
            if t <= 0:
                continue
            used = bay.total_mass()
            space = max(0.0, cap - used)
            add = round(min(t, space), 2)
            if add <= 0:
                continue
            removed = hauler.unload_cargo(key, add)
            if removed <= 0:
                continue
            inv = bay.db.inventory or {}
            inv[key] = round(float(inv.get(key, 0)) + removed, 2)
            bay.db.inventory = inv
            delivered[key] = round(float(delivered.get(key, 0)) + removed, 2)

        if not delivered:
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "Ore Receiving Bay full — could not unload. Returning to mine."

        from typeclasses.refining import settle_plant_raw_purchase_from_treasury

        try:
            total_net = settle_plant_raw_purchase_from_treasury(
                owner,
                dest_room,
                delivered,
                raw_pipeline=pipeline,
                memo=f"Plant raw intake ({hauler.key})",
            )
        except ValueError:
            for rk, t in list(delivered.items()):
                bay.withdraw(rk, t)
                hauler.load_cargo(rk, t)
            hauler.db.hauler_state = "transit_mine"
            set_hauler_next_cycle(hauler)
            return True, "Plant treasury could not cover purchase; cargo retained."

        hauler.db.hauler_state = "transit_mine"
        set_hauler_next_cycle(hauler)
        try:
            from world.challenges.challenge_signals import emit as _c_emit
            from world.locator_zones import locator_zone_for_room
            mine_zone = locator_zone_for_room(mine_room, has_mining_site=True)
            _c_emit(owner, "hauler_tick", {"mine_zone": mine_zone, "pipeline": pipeline})
        except Exception:
            pass
        return True, (
            f"Unloaded at {bay.key} ({sum(delivered.values()):.1f} t); "
            f"paid {owner.key} {total_net:,} cr net. Returning to mine."
        )

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
    Wakes every HAULER_ENGINE_INTERVAL seconds. Loads up to MAX_HAULERS_PER_ENGINE_TICK due
    haulers (HaulerDispatchRow next_run <= now), ordered by next_run. Each may advance up to
    HAULER_MAX_PIPELINE_STEPS state transitions per tick.
    """

    def at_script_creation(self):
        self.key = "hauler_engine"
        self.desc = "Drives autonomous hauler routes (mine <-> refinery)."
        self.persistent = True
        self.interval = HAULER_ENGINE_INTERVAL
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self, **kwargs):
        from world.hauler_dispatch import delete_hauler_dispatch_row, fetch_due_hauler_ids

        now = _now()
        now_tz = timezone.now()
        due_ids = fetch_due_hauler_ids(now=now_tz, limit=MAX_HAULERS_PER_ENGINE_TICK)

        processed = 0
        errors = 0
        scanned = 0

        for hid in due_ids:
            try:
                try:
                    hauler = ObjectDB.objects.get(id=hid)
                except ObjectDB.DoesNotExist:
                    delete_hauler_dispatch_row(hid)
                    continue

                if not getattr(hauler.db, "is_vehicle", False):
                    continue
                if not hauler.db.hauler_owner:
                    continue
                if not (
                    hauler.tags.has("autonomous_hauler", category="mining")
                    or hauler.tags.has("autonomous_hauler", category="flora")
                    or hauler.tags.has("autonomous_hauler", category="fauna")
                ):
                    delete_hauler_dispatch_row(hid)
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
            f"[hauler_engine] Tick — due_fetched={len(due_ids)} scanned={scanned} "
            f"step(s)={processed} error(s)={errors}"
        )
