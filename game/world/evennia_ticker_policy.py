"""
TICKER_HANDLER vs Script.interval (project policy)
==================================================

Use ``TICKER_HANDLER`` when many objects share the same periodic callback at the same
interval (dense subscriptions, occupancy-driven room ticks). Unsubscribe when the
object no longer needs ticks.

Use a persistent ``Script`` registered in ``settings.GLOBAL_SCRIPTS`` with
``interval`` + ``at_repeat`` for singleton world engines and other single-owner loops.

Do not move global engines onto per-room TICKER_HANDLER without a measured need;
the current room environment ticker in ``typeclasses.rooms`` is the intended pattern
for that case.
"""

EVENNIA_TICKER_POLICY_SUMMARY = (
    "Many objects / same interval → TICKER_HANDLER; singleton world loop → GLOBAL_SCRIPTS Script."
)
