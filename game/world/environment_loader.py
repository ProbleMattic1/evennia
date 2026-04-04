"""
Load and validate ``world_environment.json`` against known venue ids.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from world.venues import all_venue_ids

_DATA_PATH = Path(__file__).resolve().parent / "data" / "world_environment.json"


class EnvironmentConfigError(ValueError):
    pass


def _normalize_transition(states: tuple[str, ...], trans: dict) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for src in states:
        row = dict(trans.get(src) or {})
        weights: dict[str, float] = {}
        for k, v in row.items():
            if k not in states:
                raise EnvironmentConfigError(f"transition target {k!r} not in states")
            weights[k] = float(v)
        s = sum(weights.values())
        if s <= 0:
            raise EnvironmentConfigError(f"transition row for {src!r} sums to zero")
        out[src] = {k: weights[k] / s for k in weights}
    return out


@lru_cache(maxsize=1)
def load_world_environment_config() -> dict:
    raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if int(raw.get("schema_version") or 0) != 1:
        raise EnvironmentConfigError("world_environment.json: unsupported schema_version")

    states = tuple(str(s) for s in (raw.get("default_states") or ()))
    if len(states) < 2:
        raise EnvironmentConfigError("default_states must list at least two weather ids")

    trans = _normalize_transition(states, raw.get("default_transition") or {})

    venues_cfg = dict(raw.get("venues") or {})
    known = set(all_venue_ids())
    for vid in venues_cfg:
        if vid not in known:
            raise EnvironmentConfigError(f"unknown venue_id in world_environment.json: {vid!r}")
    for vid in known:
        if vid not in venues_cfg:
            raise EnvironmentConfigError(f"missing venues[{vid!r}] in world_environment.json")

    for vid, spec in venues_cfg.items():
        iw = str(spec.get("initial_weather") or "clear")
        if iw not in states:
            raise EnvironmentConfigError(f"venues[{vid!r}].initial_weather {iw!r} not in states")

    return {
        "states": states,
        "transition": trans,
        "venues": venues_cfg,
    }


def clear_world_environment_cache() -> None:
    load_world_environment_config.cache_clear()
