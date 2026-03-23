"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.contrib.rpg.traits import TraitHandler
from evennia.objects.objects import DefaultCharacter
from evennia.utils import lazy_property

from .objects import ObjectParent


ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

DEFAULT_ABILITY_BASES = {
    "str": 13,
    "dex": 15,
    "con": 14,
    "int": 17,
    "wis": 15,
    "cha": 17,
}

MARCUS_CHARACTER_KEY = "Marcus Killstar"

MARCUS_ABILITY_BASES = {
    "str": 24,
    "dex": 24,
    "con": 24,
    "int": 24,
    "wis": 24,
    "cha": 24,
}


def ability_bases_for_character_key(character_key, *, rpg_pointbuy_done):
    """
    Base scores when creating missing ability traits.

    Marcus: fixed god-tier. rpg_pointbuy_done False: 8s until point-buy finishes.
    None (legacy) or True: DEFAULT_ABILITY_BASES for any still-missing trait.
    """
    if character_key == MARCUS_CHARACTER_KEY:
        return MARCUS_ABILITY_BASES
    if rpg_pointbuy_done is False:
        return {k: 8 for k in ABILITY_KEYS}
    return DEFAULT_ABILITY_BASES


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    @lazy_property
    def stats(self):
        return TraitHandler(self, db_attribute_key="rpg_stats", db_attribute_category="traits")

    @lazy_property
    def skills(self):
        return TraitHandler(self, db_attribute_key="rpg_skills", db_attribute_category="traits")

    @lazy_property
    def vitals(self):
        return TraitHandler(self, db_attribute_key="rpg_vitals", db_attribute_category="traits")

    def at_object_creation(self):
        super().at_object_creation()
        if self.db.credits is None:
            self.db.credits = 1000
        if self.key == MARCUS_CHARACTER_KEY:
            self.db.rpg_pointbuy_done = True
        else:
            self.db.rpg_pointbuy_done = False
        self.ensure_default_rpg_traits()

    def ensure_default_rpg_traits(self):
        """Idempotent: safe to call for old characters that lack traits."""
        done = getattr(self.db, "rpg_pointbuy_done", None)
        bases = ability_bases_for_character_key(self.key, rpg_pointbuy_done=done)
        for key in ABILITY_KEYS:
            if self.stats.get(key):
                continue
            self.stats.add(
                key,
                ABILITY_NAMES[key],
                trait_type="static",
                base=bases[key],
                mod=0,
                mult=1.0,
            )
        if not self.vitals.get("hp"):
            self.vitals.add("hp", "Hit Points", trait_type="gauge", base=10, mod=0, min=0)
        if not self.skills.get("athletics"):
            self.skills.add(
                "athletics",
                "Athletics",
                trait_type="counter",
                base=0,
                mod=0,
                mult=1.0,
                min=0,
                max=None,
            )

    def at_pre_puppet(self, account, session=None, **kwargs):
        if not account.check_permstring("Developer"):
            if (
                self.key != MARCUS_CHARACTER_KEY
                and getattr(self.db, "rpg_pointbuy_done", None) is False
            ):
                raise RuntimeError(
                    "Finish ability point-buy first (OOC): |wpointbuy|n, then |wic|n."
                )
        super().at_pre_puppet(account, session=session, **kwargs)

    def ability_modifier(self, ability_key):
        ability_key = ability_key.lower()
        trait = self.stats.get(ability_key)
        if not trait:
            return 0
        score = int(trait.value)
        return (score - 10) // 2

    def armor_class(self, armor_bonus=0, shield_bonus=0):
        return 10 + self.ability_modifier("dex") + armor_bonus + shield_bonus

    def get_rpg_dashboard_snapshot(self):
        self.ensure_default_rpg_traits()

        def static_payload(trait):
            return {
                "name": trait.name,
                "score": int(trait.value),
                "base": int(trait.base),
                "mod": int(trait.mod),
                "abilityMod": (int(trait.value) - 10) // 2,
            }

        def gauge_payload(trait):
            return {
                "name": trait.name,
                "current": int(trait.value),
                "max": int(trait.max) if trait.max is not None else None,
            }

        abilities = {k: static_payload(self.stats[k]) for k in ABILITY_KEYS if self.stats.get(k)}
        vitals = {}
        if self.vitals.get("hp"):
            vitals["hp"] = gauge_payload(self.vitals.hp)

        return {
            "abilities": abilities,
            "vitals": vitals,
            "armorClass": self.armor_class(),
        }

    def at_post_puppet(self, **kwargs):
        super().at_post_puppet(**kwargs)
        self.ensure_default_rpg_traits()
        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=False)
        if econ:
            econ.sync_character_balance(self)
