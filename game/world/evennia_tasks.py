"""
Evennia TASK_HANDLER helpers and alignment notes.

TASK_HANDLER audit (singleton world scripts)
--------------------------------------------
- **Periodic world step** (economy rebalance, mining/flora/fauna ticks, hauler engine,
  discovery engines, world clock): keep ``Script.interval`` + ``at_repeat`` on
  ``GLOBAL_SCRIPTS`` entries. This matches Evennia’s documented pattern for global
  controllers.
- **SpaceEngagement**: bounded repeat (``repeats=MAX_TICKS``) on a per-engagement
  ``Script`` — appropriate; do not move to TASK_HANDLER.
- **One-shot / defer-after-start**: use ``TASK_HANDLER.add`` with ``persistent=False``
  for fire-and-forget work tied to the current process, or ``persistent=True`` only
  when the callback is a picklable top-level function or instance method and args
  are picklable (see Evennia taskhandler docs).

WorldClockScript schedules an immediate first snapshot via TASK_HANDLER so UI and
engines see ``last_snapshot`` without waiting a full interval after cold start.
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = [
    "schedule_once",
    "run_world_clock_immediate_tick",
    "schedule_world_clock_immediate_tick",
]


def schedule_once(
    delay_seconds: float,
    callback: Callable[..., Any],
    *args: Any,
    persistent: bool = False,
    **kwargs: Any,
) -> Any:
    """Thin wrapper around ``evennia.TASK_HANDLER.add``."""
    from evennia import TASK_HANDLER

    return TASK_HANDLER.add(delay_seconds, callback, *args, persistent=persistent, **kwargs)


def run_world_clock_immediate_tick(script_id: int) -> None:
    """
    TASK_HANDLER callback: one immediate world clock snapshot for script dbref id.

    Top-level so it is safe for non-persistent deferred calls.
    """
    from world import world_events
    from world.world_clock import compute_clock_snapshot

    from evennia.scripts.models import ScriptDB

    script = ScriptDB.objects.filter(id=script_id).first()
    if not script or not script.is_active:
        return
    snap = compute_clock_snapshot()
    script.db.last_snapshot = dict(snap)
    world_events.emit_world_clock_tick(snap)


def schedule_world_clock_immediate_tick(script, *, delay_seconds: float = 0.5) -> None:
    """Queue a single immediate-ish clock tick after the script starts."""
    schedule_once(delay_seconds, run_world_clock_immediate_tick, int(script.id), persistent=False)
