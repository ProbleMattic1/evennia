"""
Tiered split-haul Resource Colonies (10% / 25% / 50% / 75% / 100% local reserve cap before bay payout).

Same mining_pro + flora/fauna layout as Hybrid Buffer; only ``local_plant_fill_fraction`` differs.
Bootstrap via ``bootstrap_npc_tiered_split_colonies`` + resource-colony bio helper.
"""

from __future__ import annotations

from typing import Any

_LETTERS = ("Alpha", "Bravo", "Charlie", "Delta", "Echo")

_PLANT_FLORA = (
    "Aurnom Flora Processing Plant",
    "Aurnom Ore Processing Plant",
)
_PLANT_FAUNA = (
    "Aurnom Fauna Processing Plant",
    "Aurnom Flora Processing Plant",
    "Aurnom Ore Processing Plant",
)


def _npc_units(pad_prefix: str, pct_display: str) -> list[dict[str, Any]]:
    return [
        {
            "unit_id": f"H{i + 1}",
            "npc_key": f"{pad_prefix} Mining Unit {name}",
            "npc_desc": (
                f"Split-haul resource colony contractor; local reserve to {pct_display} of capacity "
                "then Ore Receiving Bay payout on overflow."
            ),
            "deploy_profile": "mining_pro",
        }
        for i, name in enumerate(_LETTERS)
    ]


def _resource_bio_for_tier(
    pad_prefix: str,
    colony_label: str,
    flora_exit_key: str,
    flora_aliases: list[str],
    fauna_exit_key: str,
    fauna_aliases: list[str],
    flora_tag: str,
    fauna_tag: str,
) -> dict[str, Any]:
    return {
        "colony_label": colony_label,
        "flora_staging_room_key": f"{pad_prefix} Flora Annex",
        "flora_staging_room_desc": (
            f"Flora annex for {colony_label}: leased stands, bulk bins, "
            "and split dispatch to local reserve and core processing."
        ),
        "flora_hub_exit_key": flora_exit_key,
        "flora_hub_exit_aliases": flora_aliases,
        "fauna_staging_room_key": f"{pad_prefix} Fauna Annex",
        "fauna_staging_room_desc": (
            f"Fauna annex for {colony_label}: leased ranges, containment, "
            "and split dispatch to local reserve and core processing."
        ),
        "fauna_hub_exit_key": fauna_exit_key,
        "fauna_hub_exit_aliases": fauna_aliases,
        "flora_pad_prefix": f"{pad_prefix} Flora Pad",
        "fauna_pad_prefix": f"{pad_prefix} Fauna Pad",
        "flora_cell_desc_template": (
            f"{colony_label} flora stand {{cell}}: harvest and split haul routing "
            "to local reserve then processing plant."
        ),
        "fauna_cell_desc_template": (
            f"{colony_label} fauna range {{cell}}: harvest and split haul routing "
            "to local reserve then processing plant."
        ),
        "flora_site_suffix": "Stand",
        "fauna_site_suffix": "Range",
        "flora_deploy_tag": flora_tag,
        "fauna_deploy_tag": fauna_tag,
        "flora_plant_keys": _PLANT_FLORA,
        "fauna_plant_keys": _PLANT_FAUNA,
    }


def _tier_spec(
    tier_slug: str,
    pct_display: str,
    frac: float,
    hub_key: str,
    hub_aliases: list[str],
    site_tag: str,
    pad_prefix: str,
    colony_label: str,
    flora_exit: str,
    flora_aliases: list[str],
    fauna_exit: str,
    fauna_aliases: list[str],
    flora_tag: str,
    fauna_tag: str,
    cell_prefix: str,
) -> dict[str, Any]:
    return {
        "tier_log_slug": tier_slug,
        "local_plant_fill_fraction": frac,
        "log_prefix": f"[npc-tiered-split:{tier_slug}]",
        "staging_room_key": f"{pad_prefix} Grid",
        "staging_room_desc": (
            f"Service deck for {colony_label}: pad telemetry, ore hoppers, and haulers with "
            f"a {pct_display} local reserve cap before overflow sells to the Ore Receiving Bay."
        ),
        "hub_to_staging_exit_key": hub_key,
        "hub_to_staging_aliases": hub_aliases,
        "staging_to_hub_exit_key": "promenade",
        "staging_to_hub_aliases": ["back", "exit", "out", "plex", "hub"],
        "cell_exit_prefix": cell_prefix,
        "site_tag": site_tag,
        "site_tag_category": "world",
        "pad_colony_prefix": pad_prefix,
        "cell_room_desc_suffix": (
            "drill mast, hopper, and split haul routing to the processing plant."
        ),
        "site_room_desc": (
            f"{colony_label} lease; catalog-wide feedstock with split local/plant haul delivery "
            f"({pct_display} local cap)."
        ),
        "npc_units": _npc_units(pad_prefix, pct_display),
        "resource_bio": _resource_bio_for_tier(
            pad_prefix,
            colony_label,
            flora_exit,
            flora_aliases,
            fauna_exit,
            fauna_aliases,
            flora_tag,
            fauna_tag,
        ),
    }


TIERED_SPLIT_COLONY_SPECS: list[dict[str, Any]] = [
    _tier_spec(
        tier_slug="10",
        pct_display="10%",
        frac=0.1,
        hub_key="split tier 10 resource colony",
        hub_aliases=[
            "split 10 colony",
            "tier 10 split grid",
            "split ten colony",
        ],
        site_tag="npc_split_tier_10_resource_supply",
        pad_prefix="Split Tier 10 Resource Colony",
        colony_label="Split Tier 10 Resource Colony",
        flora_exit="split tier 10 colony flora",
        flora_aliases=[
            "split 10 flora",
            "tier 10 colony flora",
        ],
        fauna_exit="split tier 10 colony fauna",
        fauna_aliases=[
            "split 10 fauna",
            "tier 10 colony fauna",
        ],
        flora_tag="npc_split_tier_10_resource_colony_flora",
        fauna_tag="npc_split_tier_10_resource_colony_fauna",
        cell_prefix="split10 pad ",
    ),
    _tier_spec(
        tier_slug="25",
        pct_display="25%",
        frac=0.25,
        hub_key="split tier 25 resource colony",
        hub_aliases=[
            "split 25 colony",
            "tier 25 split grid",
            "split quarter colony",
        ],
        site_tag="npc_split_tier_25_resource_supply",
        pad_prefix="Split Tier 25 Resource Colony",
        colony_label="Split Tier 25 Resource Colony",
        flora_exit="split tier 25 colony flora",
        flora_aliases=[
            "split 25 flora",
            "tier 25 colony flora",
        ],
        fauna_exit="split tier 25 colony fauna",
        fauna_aliases=[
            "split 25 fauna",
            "tier 25 colony fauna",
        ],
        flora_tag="npc_split_tier_25_resource_colony_flora",
        fauna_tag="npc_split_tier_25_resource_colony_fauna",
        cell_prefix="split25 pad ",
    ),
    _tier_spec(
        tier_slug="75",
        pct_display="75%",
        frac=0.75,
        hub_key="split tier 75 resource colony",
        hub_aliases=[
            "split 75 colony",
            "tier 75 split grid",
        ],
        site_tag="npc_split_tier_75_resource_supply",
        pad_prefix="Split Tier 75 Resource Colony",
        colony_label="Split Tier 75 Resource Colony",
        flora_exit="split tier 75 colony flora",
        flora_aliases=[
            "split 75 flora",
            "tier 75 colony flora",
        ],
        fauna_exit="split tier 75 colony fauna",
        fauna_aliases=[
            "split 75 fauna",
            "tier 75 colony fauna",
        ],
        flora_tag="npc_split_tier_75_resource_colony_flora",
        fauna_tag="npc_split_tier_75_resource_colony_fauna",
        cell_prefix="split75 pad ",
    ),
    _tier_spec(
        tier_slug="100",
        pct_display="100%",
        frac=1.0,
        hub_key="split tier 100 resource colony",
        hub_aliases=[
            "split 100 colony",
            "tier 100 split grid",
            "full local split colony",
        ],
        site_tag="npc_split_tier_100_resource_supply",
        pad_prefix="Split Tier 100 Resource Colony",
        colony_label="Split Tier 100 Resource Colony",
        flora_exit="split tier 100 colony flora",
        flora_aliases=[
            "split 100 flora",
            "tier 100 colony flora",
        ],
        fauna_exit="split tier 100 colony fauna",
        fauna_aliases=[
            "split 100 fauna",
            "tier 100 colony fauna",
        ],
        flora_tag="npc_split_tier_100_resource_colony_flora",
        fauna_tag="npc_split_tier_100_resource_colony_fauna",
        cell_prefix="split100 pad ",
    ),
]
