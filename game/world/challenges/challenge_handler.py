"""
Per-character cadence-challenge state handler.

Attached to Character as a lazy_property (same pattern as MissionHandler):
    character.challenges.on_event("vendor_sale", {...})
    character.challenges.evaluate_window("daily")
    character.challenges.serialize_for_web()

State schema (stored under Attribute key "_challenges", category="challenges"):
{
    "schema_version": 1,
    "windows": {cadence: last_window_key},
    "active": [
        {
            "challengeId": str,
            "cadence": str,
            "windowKey": str,
            "progress": {predicate_key: any},
            "status": "in_progress" | "complete" | "claimed",
            "startedAt": iso,
            "completedAt": iso | None,
            "rewardsGranted": bool,  # set after grant phase
            "rewardsGrantedAt": iso | None,
        }
    ],
    "history": [  # ring buffer, capped at HISTORY_CAP
        {"challengeId", "cadence", "windowKey", "completedAt", "claimed"}
    ],
    "telemetry": {
        # daily key:
        "zones_today": [str, ...],         # locator zone ids visited today
        "rooms_today": [int, ...],          # room dbids visited today (capped)
        "balance_snapshot_day_key": str,    # daily key when snapshot taken
        "balance_snapshot": int,            # balance at start of window day
        "hauler_events_day_key": str,
        "hauler_events_today": int,
        "property_ops_day_key": str,
        "property_ops_today": int,
        # incremental counters reset per window key
        "vendor_sales_day_key": str,
        "vendor_sales_today": int,
        "vendor_ids_today": [str, ...],
        "treasury_touches_day_key": str,
        "treasury_touches_today": int,
        "mine_deposits_day_key": str,
        "mine_deposits_today": int,
        "pipelines_today": [str, ...],      # "mining" | "flora" | "fauna"
        # weekly / monthly tallies stored by window key:
        "hauler_throughput_by_window": {window_key: int},
        "deed_actions_by_window": {window_key: int},
        # all-time
        "lifetime_credits_moved": int,
        "rooms_ever": [int, ...],           # capped list of first-seen room dbids
        "venues_ever": [str, ...],          # venue_ids visited
        "locator_zones_ever": [str, ...],   # locator zone ids ever visited
    # space combat (daily reset via space_engagement_day_key)
    "space_engagement_day_key": str,
    "space_engagement_events_today": int,
    "space_engagement_completions_today": int,
    "space_under_fire_events_today": int,
    "space_heat_stress_events_today": int,
    },
}
"""

from __future__ import annotations

from typing import Any

from evennia.utils import logger

from world.challenges.challenge_evaluator import evaluate_window, on_event
from world.challenges.challenge_loader import (
    all_challenge_templates,
    challenges_for_cadence,
    get_challenge_template,
)
from world.time import (
    VALID_CADENCES,
    to_iso,
    utc_now,
    window_key_for_cadence,
)
from world.point_store.point_store_loader import (
    all_point_offers,
    get_point_offer,
    serialize_offer_for_web,
)

CHALLENGE_ATTR_KEY = "_challenges"
CHALLENGE_ATTR_CATEGORY = "challenges"
SCHEMA_VERSION = 1

HISTORY_CAP = 200
ROOMS_EVER_CAP = 2000
ZONES_TODAY_CAP = 100
ROOMS_TODAY_CAP = 500
VENDOR_IDS_CAP = 200
PIPELINES_CAP = 20

# Sanity cap for staff-editable JSON (single grant).
MAX_SINGLE_CHALLENGE_CREDITS_GRANT = 1_000_000

# Default perk slots before point-store bonuses.
DEFAULT_PERK_SLOT_TOTAL = 2

# When reading license tier, if character has no explicit value use this floor.
LICENSE_READ_BASELINE: dict[str, int] = {}


def _blank_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "windows": {},
        "active": [],
        "history": [],
        "points_lifetime": 0,
        "points_season": 0,
        "season_id": "",
        "pointPurchases": {},
        "unlockTags": [],
        "perkSlotTotal": DEFAULT_PERK_SLOT_TOTAL,
        "ownedPerks": [],
        "equippedPerks": [],
        "licenseTiers": {},
        "unlockedRefiningRecipes": [],
        "telemetry": {
            "zones_today": [],
            "rooms_today": [],
            "balance_snapshot_day_key": "",
            "balance_snapshot": 0,
            "hauler_events_day_key": "",
            "hauler_events_today": 0,
            "property_ops_day_key": "",
            "property_ops_today": 0,
            "vendor_sales_day_key": "",
            "vendor_sales_today": 0,
            "vendor_ids_today": [],
            "treasury_touches_day_key": "",
            "treasury_touches_today": 0,
            "mine_deposits_day_key": "",
            "mine_deposits_today": 0,
            "pipelines_today": [],
            "hauler_throughput_by_window": {},
            "deed_actions_by_window": {},
            "lifetime_credits_moved": 0,
            "rooms_ever": [],
            "venues_ever": [],
            "locator_zones_ever": [],
            "space_engagement_day_key": "",
            "space_engagement_events_today": 0,
            "space_engagement_completions_today": 0,
            "space_under_fire_events_today": 0,
            "space_heat_stress_events_today": 0,
        },
    }


class ChallengeHandler:
    """Per-character cadence challenge state manager."""

    def __init__(self, obj):
        self.obj = obj
        raw = obj.attributes.get(
            CHALLENGE_ATTR_KEY,
            category=CHALLENGE_ATTR_CATEGORY,
            default=None,
        )
        self._state: dict[str, Any] = _blank_state() if not isinstance(raw, dict) else raw
        self._normalize()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _normalize(self) -> None:
        state = self._state
        state.setdefault("schema_version", SCHEMA_VERSION)
        state.setdefault("windows", {})
        state.setdefault("active", [])
        state.setdefault("history", [])
        tel = state.setdefault("telemetry", {})
        blank_tel = _blank_state()["telemetry"]
        for k, v in blank_tel.items():
            if k not in tel:
                tel[k] = v
        state.setdefault("points_lifetime", 0)
        state.setdefault("points_season", 0)
        state.setdefault("season_id", "")
        state.setdefault("pointPurchases", {})
        state.setdefault("unlockTags", [])
        state.setdefault("perkSlotTotal", DEFAULT_PERK_SLOT_TOTAL)
        state.setdefault("ownedPerks", [])
        state.setdefault("equippedPerks", [])
        state.setdefault("licenseTiers", {})
        state.setdefault("unlockedRefiningRecipes", [])

    def _save(self) -> None:
        self.obj.attributes.add(
            CHALLENGE_ATTR_KEY, self._state, category=CHALLENGE_ATTR_CATEGORY
        )

    # ------------------------------------------------------------------
    # Public API used by Character and web layer
    # ------------------------------------------------------------------

    def on_event(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        """Dispatch a game event; evaluates incremental telemetry and completes challenges."""
        changed = on_event(self, event_name, payload or {})
        if changed:
            self._save()

    def evaluate_window(self, cadence: str | None = None) -> list[str]:
        """
        Check all active challenges for cadences. If cadence is None, checks all.
        Returns list of newly completed challengeIds.
        """
        cadences = [cadence] if cadence else list(VALID_CADENCES)
        newly_completed: list[str] = []
        for cad in cadences:
            completed = evaluate_window(self, cad)
            newly_completed.extend(completed)
        if newly_completed:
            self._save()
        return newly_completed

    def sync_window_roll(self, cadence: str) -> bool:
        """
        If the current window key differs from the last stored one, roll the window:
        archive in-progress challenges that are now past their window, activate
        new ones for this window. Returns True if a roll happened.
        """
        current_key = window_key_for_cadence(cadence)
        last_key = (self._state.get("windows") or {}).get(cadence, "")
        if current_key == last_key:
            return False
        self._roll_window(cadence, current_key)
        self._save()
        return True

    def sync_all_windows(self) -> list[str]:
        """Roll all cadences. Returns list of cadences that were rolled."""
        rolled = []
        for cadence in VALID_CADENCES:
            if self.sync_window_roll(cadence):
                rolled.append(cadence)
        return rolled

    # ------------------------------------------------------------------
    # Telemetry accessors / mutators (called by evaluator / signals)
    # ------------------------------------------------------------------

    @property
    def telemetry(self) -> dict[str, Any]:
        return self._state["telemetry"]

    def _tel_reset_if_stale(self, day_key_field: str, *counter_fields: str) -> None:
        tel = self.telemetry
        today = window_key_for_cadence("daily")
        if tel.get(day_key_field) != today:
            tel[day_key_field] = today
            for f in counter_fields:
                if isinstance(tel.get(f), int):
                    tel[f] = 0
                elif isinstance(tel.get(f), list):
                    tel[f] = []

    def record_zone_visit(self, zone_id: str) -> None:
        self._tel_reset_if_stale("balance_snapshot_day_key")  # ensure day key check
        today = window_key_for_cadence("daily")
        tel = self.telemetry
        # Use separate stale guard for zones
        if tel.get("zones_today_day_key", "") != today:
            tel["zones_today_day_key"] = today
            tel["zones_today"] = []
        zones: list[str] = tel.setdefault("zones_today", [])
        if zone_id and zone_id not in zones:
            zones.append(zone_id)
            if len(zones) > ZONES_TODAY_CAP:
                tel["zones_today"] = zones[-ZONES_TODAY_CAP:]
        # all-time
        ever: list[str] = tel.setdefault("locator_zones_ever", [])
        if zone_id and zone_id not in ever:
            ever.append(zone_id)

    def record_room_visit(self, room_id: int, venue_id: str | None = None) -> None:
        today = window_key_for_cadence("daily")
        tel = self.telemetry
        if tel.get("rooms_today_day_key", "") != today:
            tel["rooms_today_day_key"] = today
            tel["rooms_today"] = []
        rooms: list[int] = tel.setdefault("rooms_today", [])
        if room_id not in rooms:
            rooms.append(room_id)
            if len(rooms) > ROOMS_TODAY_CAP:
                tel["rooms_today"] = rooms[-ROOMS_TODAY_CAP:]
        # all-time
        ever: list[int] = tel.setdefault("rooms_ever", [])
        if room_id not in ever:
            ever.append(room_id)
            if len(ever) > ROOMS_EVER_CAP:
                tel["rooms_ever"] = ever[-ROOMS_EVER_CAP:]
        if venue_id:
            venue_ever: list[str] = tel.setdefault("venues_ever", [])
            if venue_id not in venue_ever:
                venue_ever.append(venue_id)

    def record_vendor_sale(self, vendor_id: str, price: int, tax_amount: int) -> None:
        self._tel_reset_if_stale("vendor_sales_day_key", "vendor_sales_today")
        tel = self.telemetry
        tel["vendor_sales_today"] = int(tel.get("vendor_sales_today") or 0) + 1
        vendor_ids: list[str] = tel.setdefault("vendor_ids_today", [])
        if tel.get("vendor_ids_day_key", "") != window_key_for_cadence("daily"):
            tel["vendor_ids_day_key"] = window_key_for_cadence("daily")
            tel["vendor_ids_today"] = [vendor_id] if vendor_id else []
        elif vendor_id and vendor_id not in vendor_ids:
            vendor_ids.append(vendor_id)
            if len(vendor_ids) > VENDOR_IDS_CAP:
                tel["vendor_ids_today"] = vendor_ids[-VENDOR_IDS_CAP:]
        tel["lifetime_credits_moved"] = (
            int(tel.get("lifetime_credits_moved") or 0) + abs(price)
        )

    def record_treasury_touch(self) -> None:
        self._tel_reset_if_stale("treasury_touches_day_key", "treasury_touches_today")
        self.telemetry["treasury_touches_today"] = (
            int(self.telemetry.get("treasury_touches_today") or 0) + 1
        )

    def record_property_op(self) -> None:
        self._tel_reset_if_stale("property_ops_day_key", "property_ops_today")
        self.telemetry["property_ops_today"] = (
            int(self.telemetry.get("property_ops_today") or 0) + 1
        )

    def record_hauler_event(self, mine_zone: str | None = None) -> None:
        today = window_key_for_cadence("daily")
        tel = self.telemetry
        self._tel_reset_if_stale("hauler_events_day_key", "hauler_events_today")
        tel["hauler_events_today"] = int(tel.get("hauler_events_today") or 0) + 1
        week_key = window_key_for_cadence("weekly")
        by_window: dict[str, int] = tel.setdefault("hauler_throughput_by_window", {})
        by_window[week_key] = int(by_window.get(week_key) or 0) + 1
        if mine_zone:
            self.record_zone_visit(mine_zone)

    def record_mine_deposit(self, pipeline: str) -> None:
        self._tel_reset_if_stale("mine_deposits_day_key", "mine_deposits_today")
        self.telemetry["mine_deposits_today"] = (
            int(self.telemetry.get("mine_deposits_today") or 0) + 1
        )
        today = window_key_for_cadence("daily")
        tel = self.telemetry
        if tel.get("pipelines_day_key", "") != today:
            tel["pipelines_day_key"] = today
            tel["pipelines_today"] = []
        pipelines: list[str] = tel.setdefault("pipelines_today", [])
        if pipeline and pipeline not in pipelines:
            pipelines.append(pipeline)

    def record_deed_action(self) -> None:
        tel = self.telemetry
        week_key = window_key_for_cadence("weekly")
        by_window: dict[str, int] = tel.setdefault("deed_actions_by_window", {})
        by_window[week_key] = int(by_window.get(week_key) or 0) + 1

    def take_balance_snapshot(self, balance: int) -> None:
        today = window_key_for_cadence("daily")
        tel = self.telemetry
        if tel.get("balance_snapshot_day_key") != today:
            tel["balance_snapshot_day_key"] = today
            tel["balance_snapshot"] = int(balance)

    def add_lifetime_credits(self, amount: int) -> None:
        tel = self.telemetry
        tel["lifetime_credits_moved"] = (
            int(tel.get("lifetime_credits_moved") or 0) + max(0, int(amount))
        )

    # ------------------------------------------------------------------
    # Challenge activation / completion (used by evaluator)
    # ------------------------------------------------------------------

    def get_active(self, challenge_id: str, window_key: str) -> dict[str, Any] | None:
        for entry in list(self._state.get("active") or []):
            if entry.get("challengeId") == challenge_id and entry.get("windowKey") == window_key:
                return entry
        return None

    def get_or_create_active(
        self, challenge_id: str, cadence: str, window_key: str
    ) -> dict[str, Any]:
        entry = self.get_active(challenge_id, window_key)
        if entry is None:
            entry = {
                "challengeId": challenge_id,
                "cadence": cadence,
                "windowKey": window_key,
                "progress": {},
                "status": "in_progress",
                "startedAt": to_iso(utc_now()),
                "completedAt": None,
            }
            self._state["active"].append(entry)
        return entry

    def _apply_rewards_for_entry(self, entry: dict, *, phase: str) -> dict[str, int]:
        """
        phase: 'complete' | 'claim'
        Idempotent: if entry['rewardsGranted'], no-op.
        """
        if entry.get("rewardsGranted"):
            return {"points_added": 0, "credits_added": 0}

        cid = str(entry.get("challengeId") or "")
        tmpl = get_challenge_template(cid) or {}
        rewards = dict(tmpl.get("rewards") or {})
        grant_on = str(rewards.get("grantOn") or "claim").lower()
        if grant_on != phase:
            return {"points_added": 0, "credits_added": 0}

        pts = max(0, int(rewards.get("challengePoints") or 0))
        cr = max(0, min(int(rewards.get("credits") or 0), MAX_SINGLE_CHALLENGE_CREDITS_GRANT))

        if pts:
            self._state["points_lifetime"] = int(self._state.get("points_lifetime") or 0) + pts
            self._state["points_season"] = int(self._state.get("points_season") or 0) + pts

        if cr:
            from typeclasses.economy import get_economy

            econ = get_economy(create_missing=True)
            acct = econ.get_character_account(self.obj)
            econ.ensure_account(acct, opening_balance=int(getattr(self.obj.db, "credits", None) or 0))
            econ.deposit(acct, cr, memo=f"challenge reward {cid}")
            econ.sync_character_balance(self.obj)

        entry["rewardsGranted"] = True
        entry["rewardsGrantedAt"] = to_iso(utc_now())
        logger.log_info(f"[challenges] reward {self.obj.key} id={cid} +{pts}pts +{cr}cr phase={phase}")
        return {"points_added": pts, "credits_added": cr}

    def mark_complete(self, challenge_id: str, window_key: str) -> bool:
        entry = self.get_active(challenge_id, window_key)
        if entry is None or entry.get("status") != "in_progress":
            return False
        entry["status"] = "complete"
        entry["completedAt"] = to_iso(utc_now())
        self._push_history(challenge_id, entry.get("cadence", ""), window_key)
        self._maybe_unlock_missions(challenge_id)
        self._apply_rewards_for_entry(entry, phase="complete")
        return True

    def _maybe_unlock_missions(self, challenge_id: str) -> None:
        """If the challenge template lists missionUnlockIds, offer them as opportunities."""
        try:
            from world.challenges.challenge_loader import get_challenge_template
            from world.mission_loader import get_mission_template
            tmpl = get_challenge_template(challenge_id) or {}
            unlock_ids = list(tmpl.get("missionUnlockIds") or [])
            if not unlock_ids:
                return
            for mid in unlock_ids:
                mission_tmpl = get_mission_template(mid)
                if not mission_tmpl:
                    continue
                self.obj.missions._offer_template(
                    mission_tmpl,
                    source={
                        "kind": "alert",
                        "sourceKey": f"challenge:{challenge_id}:unlock:{mid}",
                    },
                )
        except Exception:
            from evennia.utils import logger
            logger.log_trace(f"[challenges] mission unlock failed for {challenge_id}")

    def mark_claimed(self, challenge_id: str, window_key: str) -> tuple[bool, str]:
        entry = self.get_active(challenge_id, window_key)
        if entry is None:
            return False, "No active entry for that challenge and window."
        if entry.get("status") != "complete":
            return False, "That challenge is not ready to claim (must be complete)."
        self._apply_rewards_for_entry(entry, phase="claim")
        entry["status"] = "claimed"
        self._save()
        return True, "Claimed."

    def list_complete_claim_pairs_for_cadence(self, cadence: str) -> list[tuple[str, str]]:
        """Snapshot (challengeId, windowKey) for entries ready to claim in this cadence."""
        out: list[tuple[str, str]] = []
        for e in list(self._state.get("active") or []):
            if e.get("cadence") != cadence or e.get("status") != "complete":
                continue
            cid = str(e.get("challengeId") or "").strip()
            wk = str(e.get("windowKey") or "").strip()
            if cid and wk:
                out.append((cid, wk))
        return out

    def claim_all_complete_for_cadence(self, cadence: str) -> tuple[int, str]:
        """
        Claim every challenge in ``cadence`` that is currently ``complete``.
        Reuses mark_claimed per entry so economy grants and _save() match single-claim semantics.
        """
        if cadence not in VALID_CADENCES:
            return 0, f"Unknown cadence {cadence!r}."
        pairs = self.list_complete_claim_pairs_for_cadence(cadence)
        if not pairs:
            return 0, "No completed challenges to claim for that cadence."
        n = 0
        last_msg = ""
        for cid, wk in pairs:
            ok, msg = self.mark_claimed(cid, wk)
            last_msg = msg or last_msg
            if ok:
                n += 1
        if n:
            return n, f"Claimed {n} challenge(s)."
        return 0, last_msg or "Nothing could be claimed."

    def _push_history(self, challenge_id: str, cadence: str, window_key: str) -> None:
        hist = list(self._state.get("history") or [])
        hist.append({
            "challengeId": challenge_id,
            "cadence": cadence,
            "windowKey": window_key,
            "completedAt": to_iso(utc_now()),
            "claimed": False,
        })
        self._state["history"] = hist[-HISTORY_CAP:]

    def already_completed(self, challenge_id: str, window_key: str) -> bool:
        for entry in list(self._state.get("active") or []):
            if (
                entry.get("challengeId") == challenge_id
                and entry.get("windowKey") == window_key
                and entry.get("status") in ("complete", "claimed")
            ):
                return True
        for row in list(self._state.get("history") or []):
            if (
                row.get("challengeId") == challenge_id
                and row.get("windowKey") == window_key
            ):
                return True
        return False

    def _roll_window(self, cadence: str, new_key: str) -> None:
        old_key = (self._state.get("windows") or {}).get(cadence, "")
        active = self._state.get("active") or []
        kept = []
        for entry in active:
            if entry.get("cadence") == cadence and entry.get("windowKey") == old_key:
                if entry.get("status") == "in_progress":
                    entry["status"] = "expired"
            kept.append(entry)
        # Trim old expired/claimed entries (keep last 40 per cadence for web display)
        by_cadence: dict[str, list] = {}
        for e in kept:
            by_cadence.setdefault(e.get("cadence", ""), []).append(e)
        trimmed = []
        for cad, entries in by_cadence.items():
            if cad == cadence:
                non_expired = [e for e in entries if e.get("status") not in ("expired", "claimed")]
                trimmed.extend(non_expired[-40:])
            else:
                trimmed.extend(entries)
        self._state["active"] = trimmed
        self._state.setdefault("windows", {})[cadence] = new_key

    # ------------------------------------------------------------------
    # Challenge point store
    # ------------------------------------------------------------------

    def purchase_count(self, offer_id: str) -> int:
        oid = str(offer_id or "").strip()
        if not oid:
            return 0
        row = (self._state.get("pointPurchases") or {}).get(oid) or {}
        return max(0, int(row.get("count") or 0))

    def has_unlock_tag(self, tag: str) -> bool:
        return str(tag).strip() in set(self._state.get("unlockTags") or [])

    def equipped_perk_ids(self) -> list[str]:
        return [str(x).strip() for x in (self._state.get("equippedPerks") or []) if str(x).strip()]

    def perk_slot_total(self) -> int:
        return max(0, int(self._state.get("perkSlotTotal") or DEFAULT_PERK_SLOT_TOTAL))

    def license_tier(self, key: str) -> int:
        k = str(key or "").strip()
        if not k:
            return 0
        stored = (self._state.get("licenseTiers") or {}).get(k)
        if stored is not None:
            return max(0, int(stored))
        return max(0, int(LICENSE_READ_BASELINE.get(k, 0)))

    def has_refining_recipe_unlock(self, recipe_key: str) -> bool:
        rk = str(recipe_key or "").strip()
        if not rk:
            return False
        return rk in set(self._state.get("unlockedRefiningRecipes") or [])

    def _increment_purchase_record(self, offer_id: str) -> None:
        pp = dict(self._state.get("pointPurchases") or {})
        prev = pp.get(offer_id) or {}
        pp[offer_id] = {
            "count": int(prev.get("count") or 0) + 1,
            "lastAt": to_iso(utc_now()),
        }
        self._state["pointPurchases"] = pp

    def _decrement_purchase_record(self, offer_id: str) -> None:
        pp = dict(self._state.get("pointPurchases") or {})
        prev = pp.get(offer_id) or {}
        n = int(prev.get("count") or 0) - 1
        if n <= 0:
            pp.pop(offer_id, None)
        else:
            pp[offer_id] = {**prev, "count": n}
        self._state["pointPurchases"] = pp

    def _bump_perk_slots(self, delta: int) -> None:
        self._state["perkSlotTotal"] = self.perk_slot_total() + int(delta)

    def _grant_and_try_equip_perk(self, perk_id: str) -> None:
        owned = list(self._state.get("ownedPerks") or [])
        if perk_id not in owned:
            owned.append(perk_id)
            self._state["ownedPerks"] = owned[-200:]
        eq = [str(x) for x in (self._state.get("equippedPerks") or []) if str(x).strip()]
        if perk_id not in eq and len(eq) < self.perk_slot_total():
            eq.append(perk_id)
        self._state["equippedPerks"] = eq[-50:]

    def _add_unlock_tags(self, tags: list[str]) -> None:
        cur = list(self._state.get("unlockTags") or [])
        s = set(cur)
        for t in tags:
            if t and t not in s:
                cur.append(t)
                s.add(t)
        self._state["unlockTags"] = cur[-500:]

    def _set_license_tier_floor(self, license_key: str, tier: int) -> None:
        lt = dict(self._state.get("licenseTiers") or {})
        cur = lt.get(license_key)
        if cur is None:
            cur = LICENSE_READ_BASELINE.get(license_key, 0)
        else:
            cur = int(cur)
        lt[license_key] = max(cur, int(tier))
        self._state["licenseTiers"] = lt

    def _unlock_refining_recipes(self, keys: list[str]) -> None:
        cur = list(self._state.get("unlockedRefiningRecipes") or [])
        s = set(cur)
        for k in keys:
            if k and k not in s:
                cur.append(k)
                s.add(k)
        self._state["unlockedRefiningRecipes"] = cur[-500:]

    def purchase_offer(self, offer_id: str) -> tuple[bool, str]:
        """
        Spend challenge points for a catalog offer. Credits are never used.
        On effect failure, points and purchase count are rolled back.
        """
        from world.point_store.effects import apply_effect

        oid = str(offer_id or "").strip()
        row = get_point_offer(oid)
        if not row or not row.get("enabled", True):
            return False, "Unknown or disabled offer."

        for pr in row.get("prerequisiteOfferIds") or []:
            if self.purchase_count(pr) < 1:
                return False, f"Requires prerequisite offer {pr!r}."

        max_p = row.get("maxPurchasesPerCharacter")
        if max_p is not None and self.purchase_count(oid) >= int(max_p):
            return False, "Maximum purchases for this offer reached."

        cl = int(row["costLifetime"] or 0)
        cs = int(row["costSeason"] or 0)
        season_need = row.get("seasonId")
        char_season = str(self._state.get("season_id") or "")
        if cs > 0:
            if not char_season.strip():
                return False, "Season is not active; seasonal offers are unavailable."
            if season_need and str(season_need).strip() != char_season.strip():
                return False, "This offer is not available in the current season."

        pl = int(self._state.get("points_lifetime") or 0)
        ps = int(self._state.get("points_season") or 0)
        if pl < cl or ps < cs:
            return False, "Not enough challenge points."

        self._state["points_lifetime"] = pl - cl
        self._state["points_season"] = ps - cs
        self._increment_purchase_record(oid)
        setattr(self, "_effect_offer_id", oid)
        try:
            apply_effect(self, dict(row["effect"]))
        except Exception as exc:
            self._state["points_lifetime"] = pl
            self._state["points_season"] = ps
            self._decrement_purchase_record(oid)
            logger.log_err(f"[point_store] purchase_offer effect failed {self.obj.key} {oid}: {exc}")
            return False, f"Purchase failed: {exc}"
        finally:
            if hasattr(self, "_effect_offer_id"):
                delattr(self, "_effect_offer_id")

        self._save()
        logger.log_info(f"[point_store] purchase {self.obj.key} offer={oid} -{cl}LT -{cs}SS")
        return True, "Purchased."

    # ------------------------------------------------------------------
    # Web serialization
    # ------------------------------------------------------------------

    def serialize_for_web(self) -> dict[str, Any]:
        active_payload = []
        for entry in list(self._state.get("active") or []):
            tmpl = get_challenge_template(entry.get("challengeId") or "") or {}
            active_payload.append({
                "challengeId": entry.get("challengeId"),
                "cadence": entry.get("cadence"),
                "windowKey": entry.get("windowKey"),
                "title": tmpl.get("title") or entry.get("challengeId"),
                "summary": tmpl.get("summary") or "",
                "status": entry.get("status"),
                "startedAt": entry.get("startedAt"),
                "completedAt": entry.get("completedAt"),
                "progress": dict(entry.get("progress") or {}),
                "rewardsGranted": bool(entry.get("rewardsGranted")),
            })
        history_rows = list(reversed((self._state.get("history") or [])[-20:]))
        recent_history = []
        for row in history_rows:
            out = dict(row)
            cid = out.get("challengeId") or ""
            tmpl = get_challenge_template(cid) or {}
            out["title"] = str(tmpl.get("title") or "")
            recent_history.append(out)
        offers_pub = []
        for off in all_point_offers():
            if not off.get("enabled", True):
                continue
            ser = serialize_offer_for_web(off)
            cid = ser["id"]
            ser["purchasedCount"] = self.purchase_count(cid)
            plb = int(self._state.get("points_lifetime") or 0)
            psb = int(self._state.get("points_season") or 0)
            ser["canAfford"] = plb >= int(off.get("costLifetime") or 0) and psb >= int(
                off.get("costSeason") or 0
            )
            prereq_ok = True
            for pr in off.get("prerequisiteOfferIds") or []:
                if self.purchase_count(pr) < 1:
                    prereq_ok = False
                    break
            ser["prerequisitesMet"] = prereq_ok
            max_p = off.get("maxPurchasesPerCharacter")
            if max_p is not None and self.purchase_count(cid) >= int(max_p):
                ser["soldOut"] = True
            else:
                ser["soldOut"] = False
            cseason = int(off.get("costSeason") or 0)
            char_season = str(self._state.get("season_id") or "").strip()
            need_season = str(off.get("seasonId") or "").strip()
            season_ok = True
            if cseason > 0:
                season_ok = bool(char_season) and (not need_season or need_season == char_season)
            ser["seasonOk"] = season_ok
            ser["canPurchase"] = (
                bool(off.get("enabled", True))
                and ser["prerequisitesMet"]
                and not ser["soldOut"]
                and ser["canAfford"]
                and season_ok
            )
            offers_pub.append(ser)

        purchase_summary = {
            k: int((v or {}).get("count") or 0)
            for k, v in (self._state.get("pointPurchases") or {}).items()
        }

        return {
            "active": active_payload,
            "history": recent_history,
            "windows": dict(self._state.get("windows") or {}),
            "pointsLifetime": int(self._state.get("points_lifetime") or 0),
            "pointsSeason": int(self._state.get("points_season") or 0),
            "seasonId": str(self._state.get("season_id") or ""),
            "pointOffers": offers_pub,
            "pointPurchases": purchase_summary,
            "perkSlotTotal": self.perk_slot_total(),
            "equippedPerks": self.equipped_perk_ids(),
        }
