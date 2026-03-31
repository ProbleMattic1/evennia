"""
Shared mining deposit presets and rig tuning for bootstrap scripts.

Keeps NPC contractor grids aligned with Marcus Killstar mine scaling:
catalog-wide ore mix, Deep-tier tonnage fields, pro-rig drive modes.

Import only from typeclasses / stdlib here to avoid bootstrap import cycles.
"""

from __future__ import annotations

from typing import Any

from typeclasses.mining import RESOURCE_CATALOG

# Match legacy bootstrap_marcus_mines deposit base for long-term parity.
CATALOG_WIDE_DEPOSIT_BASE: dict[str, Any] = {
    "richness": 1.0,
    "base_output_tons": 20.0,
    "depletion_rate": 0.002,
    "richness_floor": 0.12,
}


def composition_all_ore_resources() -> dict[str, float]:
    keys = list(RESOURCE_CATALOG.keys())
    if not keys:
        return {}
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def catalog_wide_ore_deposit() -> dict[str, Any]:
    """Deposit dict for MiningSite.db.deposit — every RESOURCE_CATALOG key, equal share."""
    d = dict(CATALOG_WIDE_DEPOSIT_BASE)
    d["composition"] = composition_all_ore_resources()
    return d


def tune_mining_rig_max_output(rig) -> None:
    rig.db.mode = "overdrive"
    rig.db.power_level = "high"
    rig.db.target_family = "mixed"
    rig.db.purity_cutoff = "low"
    rig.db.maintenance_level = "premium"


def retune_mining_rigs_on_site(site) -> None:
    for r in site.db.rigs or []:
        if r:
            tune_mining_rig_max_output(r)
