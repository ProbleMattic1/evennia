"""
Faction definitions for reputation-based pricing (``world/data/factions.json``).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent / "data" / "factions.json"


class FactionsConfigError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_factions_config() -> dict:
    raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if int(raw.get("schema_version") or 0) != 1:
        raise FactionsConfigError("factions.json: unsupported schema_version")
    factions = dict(raw.get("factions") or {})
    if not factions:
        raise FactionsConfigError("factions.json: empty factions")
    for fid, spec in factions.items():
        for k in (
            "label",
            "min_standing",
            "max_standing",
            "buy_mult_at_min_standing",
            "buy_mult_at_max_standing",
        ):
            if k not in spec:
                raise FactionsConfigError(f"factions[{fid!r}] missing {k!r}")
        mn = int(spec["min_standing"])
        mx = int(spec["max_standing"])
        if mx <= mn:
            raise FactionsConfigError(f"factions[{fid!r}]: max_standing must exceed min_standing")
    return {"factions": factions}


def clear_factions_cache() -> None:
    load_factions_config.cache_clear()


def get_faction_spec(faction_id: str) -> dict:
    cfg = load_factions_config()
    spec = (cfg["factions"] or {}).get(str(faction_id))
    if not spec:
        raise ValueError(f"Unknown faction id for standing system: {faction_id!r}")
    return spec


def buy_price_multiplier_for_standing(faction_id: str, standing: int) -> float:
    spec = get_faction_spec(faction_id)
    mn = int(spec["min_standing"])
    mx = int(spec["max_standing"])
    lo = float(spec["buy_mult_at_min_standing"])
    hi = float(spec["buy_mult_at_max_standing"])
    st = max(mn, min(mx, int(standing)))
    if mx == mn:
        t = 0.5
    else:
        t = (st - mn) / (mx - mn)
    return float(lo + (hi - lo) * t)
