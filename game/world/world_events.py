"""
Lightweight fan-out for world simulation ticks (avoid circular typeclass imports).
"""

from __future__ import annotations

import importlib
from typing import Any


def emit_world_clock_tick(snapshot: dict[str, Any]) -> None:
    """Notify engines that listen for IC clock updates."""
    for mod_path in (
        "typeclasses.ambient_world_engine",
        "typeclasses.crime_world_engine",
        "typeclasses.battlespace_world_engine",
    ):
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, "on_world_clock_tick", None)
        if callable(fn):
            fn(snapshot)
