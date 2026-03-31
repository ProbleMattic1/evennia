from __future__ import annotations

from typing import Any

from world.time import to_iso, utc_now

CRIME_ATTR_KEY = "_crime_record"
CRIME_ATTR_CATEGORY = "crime"


def _blank_state() -> dict[str, Any]:
    return {
        "notoriety": 0,
        "infractions": [],
        "flags": [],
    }


class CrimeRecordHandler:
    """Per-character crime state (not a duplicate mission engine)."""

    def __init__(self, obj):
        self.obj = obj
        self._state = obj.attributes.get(
            CRIME_ATTR_KEY,
            category=CRIME_ATTR_CATEGORY,
            default=_blank_state(),
        )
        self._normalize()

    def _normalize(self) -> None:
        if not isinstance(self._state, dict):
            self._state = _blank_state()
        self._state.setdefault("notoriety", 0)
        self._state.setdefault("infractions", [])
        self._state.setdefault("flags", [])

    def _save(self) -> None:
        self.obj.attributes.add(CRIME_ATTR_KEY, self._state, category=CRIME_ATTR_CATEGORY)

    @property
    def notoriety(self) -> int:
        return int(self._state.get("notoriety") or 0)

    def add_infraction(self, *, category: str, magnitude: int = 1, note: str = "") -> None:
        mag = max(1, int(magnitude))
        inf = list(self._state.get("infractions") or [])
        inf.append(
            {
                "category": str(category or "general").strip().lower(),
                "magnitude": mag,
                "note": str(note or "")[:500],
                "at": to_iso(utc_now()),
            }
        )
        self._state["infractions"] = inf[-200:]
        self._state["notoriety"] = int(self._state.get("notoriety") or 0) + mag
        self._save()

    def add_flag(self, flag: str) -> None:
        f = str(flag or "").strip().lower()
        if not f:
            return
        flags = list(self._state.get("flags") or [])
        if f not in flags:
            flags.append(f)
        self._state["flags"] = flags[-100:]
        self._save()

    def has_flag(self, flag: str) -> bool:
        return str(flag or "").strip().lower() in set(self._state.get("flags") or [])

    def summary_lines(self) -> list[str]:
        lines = [
            f"Notoriety: {self.notoriety}",
        ]
        flags = list(self._state.get("flags") or [])
        if flags:
            lines.append("Flags: " + ", ".join(flags[-12:]))
        recent = list(self._state.get("infractions") or [])[-5:]
        if recent:
            lines.append("Recent (abstract):")
            for row in recent:
                lines.append(
                    f"  - {row.get('category')}: +{row.get('magnitude')} "
                    f"({row.get('at', '')[:19]})"
                )
        return lines
