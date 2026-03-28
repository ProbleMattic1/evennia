"""

Lockfuncs

Lock functions are functions available when defining lock strings,
which in turn limits access to various game systems.

All functions defined globally in this module are assumed to be
available for use in lockstrings to determine access. See the
Evennia documentation for more info on locks.

A lock function is always called with two arguments, accessing_obj and
accessed_obj, followed by any number of arguments. All possible
arguments should be handled with *args, **kwargs. The lock function
should handle all eventual tracebacks by logging the error and
returning False.

Lock functions in this module extend (and will overload same-named)
lock functions from evennia.locks.lockfuncs.

"""

from evennia.utils import logger


def title_owner(accessing_obj, accessed_obj, *args, **kwargs):
    """
    True if accessing_obj is the titled owner of the holding that contains accessed_obj
    (e.g. Workshop on PropertyHolding).
    """
    try:
        loc = accessed_obj.location
        if not loc:
            return False
        owner = getattr(loc.db, "title_owner", None)
        return owner is not None and owner == accessing_obj
    except Exception:
        logger.log_trace()
        return False


# def myfalse(accessing_obj, accessed_obj, *args, **kwargs):
#    """
#    called in lockstring with myfalse().
#    A simple logger that always returns false. Prints to stdout
#    for simplicity, should use utils.logger for real operation.
#    """
#    print "%s tried to access %s. Access denied." % (accessing_obj, accessed_obj)
#    return False
