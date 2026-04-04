"""
Per-venue weather / environmental pressure (Markov steps on a fixed interval).
"""

from __future__ import annotations

import random
from typing import Any

from evennia.utils import logger

from typeclasses.scripts import Script
from world.challenges.challenge_signals import emit
from world.environment_loader import load_world_environment_config
from world.venues import all_venue_ids, venue_id_for_object

ENGINE_INTERVAL_SECONDS = 300


def _session_characters_in_venue(venue_id: str):
    import evennia

    for sess in evennia.SESSION_HANDLER.values():
        char = getattr(sess, "puppet", None)
        if char is None:
            continue
        if not char.is_typeclass("typeclasses.characters.Character", exact=False):
            continue
        if venue_id_for_object(char) == venue_id:
            yield char


class WorldEnvironmentEngine(Script):
    def at_script_creation(self):
        self.key = "world_environment_engine"
        self.desc = "Per-venue environment state (weather, pressure) for challenges and perception."
        self.persistent = True
        self.interval = ENGINE_INTERVAL_SECONDS
        self.start_delay = True
        self.repeats = 0

    def at_start(self):
        if self.db.by_venue is None:
            self.db.by_venue = {}

    def at_repeat(self):
        cfg = load_world_environment_config()
        states: tuple[str, ...] = cfg["states"]
        trans: dict[str, dict[str, float]] = cfg["transition"]
        vconf: dict[str, Any] = cfg["venues"]
        by_venue = dict(self.db.by_venue or {})

        season = _current_season_label()
        pressure_base = {"clear": 1.0, "dust": 1.08, "solar_flare_watch": 1.15, "fuel_ice_fog": 1.12}

        for vid in all_venue_ids():
            prev = dict(by_venue.get(vid) or {})
            cur_w = str(prev.get("weather") or vconf[vid]["initial_weather"])
            if cur_w not in states:
                cur_w = str(vconf[vid]["initial_weather"])

            row = trans.get(cur_w) or trans[states[0]]
            choices = list(row.keys())
            weights = [row[k] for k in choices]
            new_w = random.choices(choices, weights=weights, k=1)[0]

            anomaly = str(prev.get("anomaly") or "none")
            if random.random() < 0.02:
                anomaly = random.choice(("none", "gravity_ripple", "comm_static", "bio_spore"))

            snap = {
                "weather": new_w,
                "pressure": float(pressure_base.get(new_w, 1.0)),
                "anomaly": anomaly,
                "season_bias": season,
                "perception_mod": _perception_mod(new_w, anomaly),
                "stealth_mod": _stealth_mod(new_w, anomaly),
            }
            by_venue[vid] = snap

            payload_tick = {"venue_id": vid, **snap}
            for char in _session_characters_in_venue(vid):
                emit(char, "world_environment_tick", payload_tick)

            if new_w != cur_w:
                payload_shift = {"venue_id": vid, "from": cur_w, "to": new_w, "season": season}
                for char in _session_characters_in_venue(vid):
                    emit(char, "weather_shift", payload_shift)
                logger.log_info(f"[world_environment] venue={vid} weather {cur_w!r} -> {new_w!r}")

        self.db.by_venue = by_venue


def _current_season_label() -> str:
    from evennia import GLOBAL_SCRIPTS

    wc = GLOBAL_SCRIPTS.get("world_clock_script")
    if not wc:
        return "summer"
    snap = wc.db.last_snapshot or {}
    return str(snap.get("season") or "summer")


def _perception_mod(weather: str, anomaly: str) -> float:
    w = {"clear": 1.0, "dust": 0.92, "solar_flare_watch": 0.88, "fuel_ice_fog": 0.85}.get(
        weather, 1.0
    )
    if anomaly == "comm_static":
        w *= 0.95
    if anomaly == "bio_spore":
        w *= 0.9
    return float(w)


def _stealth_mod(weather: str, anomaly: str) -> float:
    w = {"clear": 1.0, "dust": 1.05, "solar_flare_watch": 0.98, "fuel_ice_fog": 1.12}.get(
        weather, 1.0
    )
    if anomaly == "fuel_ice_fog" or weather == "fuel_ice_fog":
        w *= 1.04
    return float(w)
