"""
Trait vs buff contrib (project policy)
======================================

**Decision:** Use ``evennia.contrib.rpg.traits`` (TraitHandler on Character) as the
single source of character stats, vitals, and long-lived modifiers.

**Do not** enable ``evennia.contrib.rpg.buffs`` until a specific feature needs timed
combat/effect stacks. Mixing both without a written precedence rule duplicates
modifier pipelines and complicates the web dashboard + combat math.

If buffs are adopted later: traits hold base + equipment; buffs apply timed deltas
with explicit ordering (buffs applied after trait effective values, or document the
inverse) and tests for stacking.
"""

TRAIT_BUFFS_POLICY_SUMMARY = "Traits only; buffs contrib deferred until a scoped feature needs timed stacks."
