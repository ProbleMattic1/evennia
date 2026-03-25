"""
D&D-style 27-point buy (scores 8–15) for new player characters.

OOC only. Superuser/Developer characters skip point-buy via Account.at_post_create_character.
"""

from evennia.commands.default.account import CmdCharCreate as DefaultCmdCharCreate
from evennia.utils import utils
from evennia.utils.evmenu import EvMenu

from commands.command import Command

from typeclasses.characters import ABILITY_KEYS, ABILITY_NAMES, character_key_skips_pointbuy

POINT_BUY_POOL = 27

# Cumulative cost from score 8 for each allowed score (PHB-style)
_SCORE_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}


def _cost_for_score(score):
    return _SCORE_COST[int(score)]


def _total_spent(work):
    return sum(_cost_for_score(work[k]) for k in ABILITY_KEYS)


def _remaining(work):
    return POINT_BUY_POOL - _total_spent(work)


def _marginal_up(score):
    """Cost to raise score by 1, or None if at max."""
    if score >= 15:
        return None
    return _cost_for_score(score + 1) - _cost_for_score(score)


def _marginal_down(score):
    """Points refunded for lowering score by 1, or None if at min."""
    if score <= 8:
        return None
    return _cost_for_score(score) - _cost_for_score(score - 1)


def _get_char(caller):
    return getattr(caller.ndb, "pointbuy_char", None)


def _get_work(char):
    work = getattr(char.db, "_pointbuy_work", None)
    if work is None:
        work = {k: 8 for k in ABILITY_KEYS}
        char.db._pointbuy_work = work
    return work


def _summary(char, work):
    lines = [f"|w{char.key}|n — Point buy ({POINT_BUY_POOL} pts)", ""]
    for k in ABILITY_KEYS:
        lines.append(f"  {ABILITY_NAMES[k]}: |c{work[k]}|n")
    lines.append("")
    rem = _remaining(work)
    lines.append(f"Points remaining: |y{rem}|n")
    lines.append("")
    lines.append("Adjust scores with the menu; |wfinish|n when valid (all 8–15, pool not exceeded).")
    return "\n".join(lines)


def node_main(caller, raw_string=None, **kwargs):
    char = _get_char(caller)
    if not char:
        return "|rNo character selected.|n", None
    if character_key_skips_pointbuy(char.key):
        return "|rThat character does not use point buy.|n", None
    if getattr(char.db, "rpg_pointbuy_done", None) is not False:
        return "|rThat character has already finished ability setup.|n", None

    work = _get_work(char)
    text = _summary(char, work)
    options = []

    for key in ABILITY_KEYS:
        up = _marginal_up(work[key])
        if up is not None and _remaining(work) >= up:
            options.append(
                {
                    "key": f"{key}+",
                    "desc": f"Raise {ABILITY_NAMES[key]} ({up} pts)",
                    "goto": (_do_raise, {"abil": key}),
                }
            )
        down = _marginal_down(work[key])
        if down is not None:
            options.append(
                {
                    "key": f"{key}-",
                    "desc": f"Lower {ABILITY_NAMES[key]} (+{down} pts)",
                    "goto": (_do_lower, {"abil": key}),
                }
            )

    options.append({"key": "finish", "desc": "Apply scores and finish", "goto": "node_finish"})
    options.append({"key": ("abort", "a"), "desc": "Exit without saving scores", "goto": "node_abort"})
    return text, tuple(options)


def _do_raise(caller, raw_string, **kwargs):
    char = _get_char(caller)
    if not char:
        return "node_main"
    work = _get_work(char)
    key = kwargs.get("abil")
    if key not in ABILITY_KEYS:
        return "node_main"
    up = _marginal_up(work[key])
    if up is None or _remaining(work) < up:
        caller.msg("|rNot enough points or already at maximum.|n")
        return "node_main"
    work[key] += 1
    char.db._pointbuy_work = work
    return "node_main"


def _do_lower(caller, raw_string, **kwargs):
    char = _get_char(caller)
    if not char:
        return "node_main"
    work = _get_work(char)
    key = kwargs.get("abil")
    if key not in ABILITY_KEYS:
        return "node_main"
    if _marginal_down(work[key]) is None:
        caller.msg("|rAlready at minimum (8).|n")
        return "node_main"
    work[key] -= 1
    char.db._pointbuy_work = work
    return "node_main"


def node_finish(caller, raw_string=None, **kwargs):
    char = _get_char(caller)
    if not char:
        return "|rNo character.|n", None
    work = _get_work(char)
    for k in ABILITY_KEYS:
        s = work[k]
        if s < 8 or s > 15:
            caller.msg("|rEach score must be between 8 and 15.|n")
            return "node_main"
    spent = _total_spent(work)
    if spent > POINT_BUY_POOL:
        caller.msg("|rSpent too many points.|n")
        return "node_main"

    char.ensure_default_rpg_traits()
    for k in ABILITY_KEYS:
        trait = char.stats.get(k)
        if trait:
            trait.base = work[k]
            trait.mod = 0
            trait.mult = 1.0

    char.db.rpg_pointbuy_done = True
    if getattr(char.db, "_pointbuy_work", None) is not None:
        del char.db._pointbuy_work

    caller.ndb.pointbuy_char = None
    caller.msg(
        f"|gAbility scores saved for {char.key}.|n You can |wic {char.key}|n to enter the game."
    )
    return None, None


def node_abort(caller, raw_string=None, **kwargs):
    caller.ndb.pointbuy_char = None
    caller.msg("Point-buy cancelled (scores not applied).")
    return None, None


class CmdPointBuy(Command):
    """
    Assign ability scores for a new character (27-point buy), OOC only.

    Usage:
      pointbuy <character name>
    """

    key = "pointbuy"
    locks = "cmd:pperm(Player)"
    help_category = "General"
    account_caller = True

    def func(self):
        account = self.account
        if self.session.puppet:
            self.msg("Use |wooc|n first. Point-buy is only available while out of character.")
            return
        if not self.args:
            wip = [
                c
                for c in utils.make_iter(account.characters)
                if getattr(c.db, "rpg_pointbuy_done", None) is False
            ]
            if len(wip) == 1:
                char = wip[0]
            elif not wip:
                self.msg("Usage: |wpointbuy <character name>|n (no characters need point-buy).")
                return
            else:
                names = ", ".join(c.key for c in wip)
                self.msg(f"Which character? {names}\nUsage: |wpointbuy <character name>|n")
                return
        else:
            found = account.search(
                self.args.strip(),
                candidates=utils.make_iter(account.characters),
                search_object=True,
                quiet=True,
            )
            if not found:
                self.msg("You have no character by that name.")
                return
            char = utils.make_iter(found)[0]

        if character_key_skips_pointbuy(char.key):
            self.msg("That character does not use point-buy.")
            return
        if getattr(char.db, "rpg_pointbuy_done", None) is not False:
            self.msg("That character does not need point-buy (already finished or exempt).")
            return

        account.ndb.pointbuy_char = char
        EvMenu(account, "commands.chargen_pointbuy", startnode="node_main", auto_quit=True)


class CmdCharCreate(DefaultCmdCharCreate):
    """Same as default, with a pointer to the point-buy step."""

    def func(self):
        account = self.account
        if not self.args:
            self.msg("Usage: charcreate <charname> [= description]")
            return
        key = self.lhs
        description = self.rhs or "This is a character."

        new_character, errors = self.account.create_character(
            key=key, description=description, ip=self.session.address
        )

        if errors:
            self.msg(errors)
        if not new_character:
            return

        self.msg(
            f"Created new character |c{new_character.key}|n.\n"
            f"Next: |wpointbuy {new_character.key}|n to assign ability scores (required before |wic|n).\n"
            f"Then: |wic {new_character.key}|n to enter the game."
        )
