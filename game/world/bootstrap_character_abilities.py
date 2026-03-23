"""
Apply default D&D-style ability bases to all Character objects once per baseline version.

Runs from at_server_cold_start on deploy. Idempotent: skips characters that already have
db.rpg_baseline_scores_v1 equal to BASELINE_VERSION.

Set env FORCE_RPG_BASELINE=1 to re-apply bases from DEFAULT_ABILITY_BASES.
"""

import os

from evennia.objects.models import ObjectDB

from typeclasses.characters import ABILITY_KEYS, DEFAULT_ABILITY_BASES, Character

BASELINE_VERSION = 1

_FLAG = "rpg_baseline_scores_v1"


def _force_reapply():
    return os.environ.get("FORCE_RPG_BASELINE", "").strip().lower() in ("1", "true", "yes")


def bootstrap_character_abilities():
    force = _force_reapply()
    qs = ObjectDB.objects.filter(db_typeclass_path__icontains="characters.Character")

    updated = 0
    skipped = 0

    # ObjectDB rows are already the live typeclass instance (e.g. Character), not a
    # separate model with a .typeclass attribute.
    for char in qs.iterator():
        if not char.is_typeclass(Character, exact=False):
            continue

        if not force and getattr(char.db, _FLAG, None) == BASELINE_VERSION:
            skipped += 1
            continue

        char.ensure_default_rpg_traits()

        for key in ABILITY_KEYS:
            trait = char.stats.get(key)
            if trait:
                trait.base = DEFAULT_ABILITY_BASES[key]
                trait.mod = 0
                trait.mult = 1.0

        setattr(char.db, _FLAG, BASELINE_VERSION)
        updated += 1

    print(f"[rpg-baseline] ability bases applied={updated} skipped={skipped} force={force}")
