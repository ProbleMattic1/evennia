"""
Helpers for singleton scripts registered in ``settings.GLOBAL_SCRIPTS``.

Evennia recreates a script if the pickle-hash of its GLOBAL_SCRIPTS entry changes.
Keep entries to ``typeclass`` + ``persistent`` only unless you intend a migration.
"""

from __future__ import annotations


def require_global_script(key: str):
    """
    Return the global script for ``key`` or raise.

    Call after the server has run ``GLOBAL_SCRIPTS.start()`` (normal game bootstrap).
    """
    from evennia import GLOBAL_SCRIPTS

    scr = GLOBAL_SCRIPTS.get(key)
    if scr is None:
        raise RuntimeError(
            f"Missing global script {key!r}. "
            "It must be listed in server.conf.settings.GLOBAL_SCRIPTS and the server "
            "must have finished startup."
        )
    return scr
