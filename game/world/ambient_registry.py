"""
In-memory ambient template registry. Rebuilt at cold start and via reload command.
Evennia: single main thread for game logic; lock documents intent if you ever read from threads.
"""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.RLock()

_registry: dict[str, Any] = {
    "version": 0,
    "by_cadence": {"tick": (), "strong": ()},
    "valid_ids": frozenset(),
    "errors": (),
}


def get_ambient_snapshot() -> dict[str, Any]:
    with _lock:
        return _registry


def replace_ambient_registry(
    *,
    by_cadence: dict[str, tuple[dict, ...]],
    valid_ids: frozenset[str],
    errors: tuple[str, ...] = (),
) -> int:
    global _registry
    with _lock:
        ver = int(_registry["version"]) + 1
        _registry = {
            "version": ver,
            "by_cadence": {
                "tick": tuple(by_cadence.get("tick", ())),
                "strong": tuple(by_cadence.get("strong", ())),
            },
            "valid_ids": valid_ids,
            "errors": tuple(errors),
        }
        return ver
