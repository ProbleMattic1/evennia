"""
Base script typeclass for game-specific persistent systems.

Scripts have no in-world location; use for economies, tick loops, and registries.
See Evennia docs: Components/Scripts.
"""

from evennia.scripts.scripts import DefaultScript


class Script(DefaultScript):
    """Local script base for game-specific scripts."""

    pass
