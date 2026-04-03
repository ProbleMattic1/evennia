"""Aggregate equipped point-store perks (opaque; server-only)."""

from __future__ import annotations

from typing import Any

from world.point_store.perk_defs_loader import get_perk_def


def mining_output_multiplier(character) -> float:
    """
    Product of miningOutputMult from equipped perks that exist in perk_defs.
    Default 1.0.
    """
    try:
        ch = character.challenges
    except Exception:
        return 1.0
    equipped = list(ch.equipped_perk_ids())
    m = 1.0
    for pid in equipped:
        d = get_perk_def(pid)
        if not d:
            continue
        try:
            m *= float(d.get("miningOutputMult") or 1.0)
        except (TypeError, ValueError):
            raise ValueError(f"perk_defs miningOutputMult invalid for perk {pid!r}")
    return m


def aggregate_modifiers(character) -> dict[str, Any]:
    """Diagnostic bundle for logging/tests; not for web clients."""
    return {
        "miningOutputMult": mining_output_multiplier(character),
        "equippedPerks": list(character.challenges.equipped_perk_ids()),
    }
