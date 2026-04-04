"""
Per-character faction reputation (numeric standing → buy price multiplier).
"""

from __future__ import annotations

from typing import Any

from evennia.utils import logger

_ATTR_KEY = "_faction_standing_v1"
_ATTR_CAT = "factions"


class FactionStandingHandler:
    def __init__(self, obj):
        self.obj = obj

    def _state(self) -> dict[str, Any]:
        data = self.obj.attributes.get(_ATTR_KEY, category=_ATTR_CAT, default=None)
        if not isinstance(data, dict):
            data = {"schema_version": 1, "standings": {}}
            self.obj.attributes.add(_ATTR_KEY, data, category=_ATTR_CAT)
        if data.get("schema_version") != 1:
            data = {"schema_version": 1, "standings": dict(data.get("standings") or {})}
            self.obj.attributes.add(_ATTR_KEY, data, category=_ATTR_CAT)
        return data

    def _save(self, state: dict[str, Any]) -> None:
        self.obj.attributes.add(_ATTR_KEY, state, category=_ATTR_CAT)

    def get_standing(self, faction_id: str) -> int:
        return int((self._state().get("standings") or {}).get(str(faction_id), 0))

    def set_standing(self, faction_id: str, value: int) -> int:
        st = self._state()
        standings = dict(st.get("standings") or {})
        from world.factions_loader import get_faction_spec

        spec = get_faction_spec(faction_id)
        mn = int(spec["min_standing"])
        mx = int(spec["max_standing"])
        v = max(mn, min(mx, int(value)))
        standings[str(faction_id)] = v
        st["standings"] = standings
        self._save(st)
        return v

    def adjust_standing(self, faction_id: str, delta: int, *, reason: str = "") -> int:
        cur = self.get_standing(faction_id)
        new_val = self.set_standing(faction_id, cur + int(delta))
        if reason:
            logger.log_info(
                f"[faction_standing] char={getattr(self.obj, 'key', '?')} "
                f"faction={faction_id!r} {cur} -> {new_val} ({reason})"
            )
        return new_val

    def buy_price_multiplier(self, faction_id: str) -> float:
        from world.factions_loader import buy_price_multiplier_for_standing

        return buy_price_multiplier_for_standing(faction_id, self.get_standing(faction_id))

    def all_standings(self) -> dict[str, int]:
        return {str(k): int(v) for k, v in (self._state().get("standings") or {}).items()}


