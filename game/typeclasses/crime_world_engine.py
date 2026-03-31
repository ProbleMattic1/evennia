"""
Crime world feed: periodic non-graphic criminal *pressure* in the setting.
Emits mission seeds (kind=crime) for JSON mission templates to pick up.
"""

from __future__ import annotations

import random

from evennia.utils import logger

from world.crime_registry import get_crime_snapshot
from world.time import parse_iso, to_iso, utc_now

from typeclasses.mission_seeds import enqueue_mission_seed
from typeclasses.scripts import Script
from typeclasses.system_alerts import enqueue_system_alert

ENGINE_INTERVAL_SECONDS = 900
_PRUNE_EVERY = 144


class CrimeWorldEngine(Script):
    def at_script_creation(self):
        self.key = "crime_world_engine"
        self.desc = "Crime ambient feed (tick + hourly strong beat) → mission seeds."
        self.persistent = True
        self.interval = ENGINE_INTERVAL_SECONDS
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self):
        now = utc_now()
        self.db.tick_index = int(self.db.tick_index or 0) + 1
        tick_idx = self.db.tick_index

        snap = get_crime_snapshot()
        by_cadence = snap["by_cadence"]

        if tick_idx % _PRUNE_EVERY == 0:
            self._prune_cooldowns(snap.get("valid_ids") or frozenset())

        slot_boundary = int(now.timestamp()) // int(ENGINE_INTERVAL_SECONDS)
        self._fire_one_pool(by_cadence.get("tick", ()), "tick", now, slot_boundary, tick_idx)

        hour_key = f"{now.date().isoformat()}T{now.hour:02d}"
        if self.db.last_strong_beat_hour != hour_key:
            self.db.last_strong_beat_hour = hour_key
            self._fire_one_pool(by_cadence.get("strong", ()), "strong", now, hour_key, tick_idx)

    def _prune_cooldowns(self, valid_ids: frozenset):
        if not valid_ids:
            return
        cd = dict(self.db.template_cooldowns or {})
        self.db.template_cooldowns = {k: v for k, v in cd.items() if k in valid_ids}

    def _fire_one_pool(self, templates, cadence, now, dedupe_slot, tick_idx):
        cooldowns = dict(self.db.template_cooldowns or {})
        eligible = []
        for t in templates:
            if int(t.get("min_tick") or 0) > tick_idx:
                continue
            cid = t["id"]
            last_fired = cooldowns.get(cid)
            if last_fired:
                prev = parse_iso(last_fired)
                cool = int(t.get("cooldown_seconds") or 0)
                if prev and cool > 0 and (now - prev).total_seconds() < cool:
                    continue
            eligible.append(t)
        if not eligible:
            return

        weights = [max(1, int(t["weight"])) for t in eligible]
        chosen = random.choices(eligible, weights=weights, k=1)[0]
        dedupe_key = f"crime:{chosen['id']}:{dedupe_slot}"

        if chosen.get("broadcast"):
            enqueue_system_alert(
                severity=chosen["severity"],
                category="crime",
                title=chosen["title"],
                detail=chosen["summary"],
                source=chosen.get("source") or "crime_world_engine",
                dedupe_key=dedupe_key,
            )

        enqueue_mission_seed(
            kind="crime",
            seed_id=chosen["id"],
            source_key=dedupe_key,
            title=chosen["title"],
            summary=chosen["summary"],
            payload={
                "severity": chosen["severity"],
                "category": chosen["category"],
                "cadence": cadence,
            },
            ttl_seconds=max(3600, int(chosen.get("cooldown_seconds") or 3600)),
        )
        cooldowns[chosen["id"]] = to_iso(now)
        self.db.template_cooldowns = cooldowns
        stats = dict(self.db.stats or {})
        stats["fired"] = int(stats.get("fired") or 0) + 1
        self.db.stats = stats
        logger.log_info(f"[crime_world] cadence={cadence} id={chosen['id']}")
