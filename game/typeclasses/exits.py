"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

    Optional db attributes for web nav (set in bootstrap or in-game):
      - db.nav_section: str — canonical key from world.nav_exit.SECTION_LABELS keys
      - db.nav_order: int — sort within section (default 0)

    Or tag the exit: tags.add("killstar", category="nav_section") for a tag-driven section.

    """

    pass
