"""
Hybrid Buffer Colony: five NPC units (mine + flora/fauna via resource-colony bio bootstrap).

Haulers fill local raw reserve at the core plant to 50% of its capacity, then sell overflow
to the Ore Receiving Bay (see Character db.haul_local_reserve_then_plant and typeclasses.haulers).
"""

NPC_HYBRID_BUFFER_UNITS = [
    {
        "unit_id": "H1",
        "npc_key": "Hybrid Buffer Mining Unit Alpha",
        "npc_desc": "Buffer colony contractor; local reserve to half capacity then plant intake.",
        "deploy_profile": "mining_pro",
    },
    {
        "unit_id": "H2",
        "npc_key": "Hybrid Buffer Mining Unit Bravo",
        "npc_desc": "Buffer colony contractor; local reserve to half capacity then plant intake.",
        "deploy_profile": "mining_pro",
    },
    {
        "unit_id": "H3",
        "npc_key": "Hybrid Buffer Mining Unit Charlie",
        "npc_desc": "Buffer colony contractor; local reserve to half capacity then plant intake.",
        "deploy_profile": "mining_pro",
    },
    {
        "unit_id": "H4",
        "npc_key": "Hybrid Buffer Mining Unit Delta",
        "npc_desc": "Buffer colony contractor; local reserve to half capacity then plant intake.",
        "deploy_profile": "mining_pro",
    },
    {
        "unit_id": "H5",
        "npc_key": "Hybrid Buffer Mining Unit Echo",
        "npc_desc": "Buffer colony contractor; local reserve to half capacity then plant intake.",
        "deploy_profile": "mining_pro",
    },
]

HYBRID_BUFFER_RESOURCE_BIO = {
    "colony_label": "Hybrid Buffer Colony",
    "flora_staging_room_key": "Hybrid Buffer Colony Flora Annex",
    "flora_staging_room_desc": (
        "Flora annex for the Hybrid Buffer Colony: leased stands, bulk bins, "
        "and split dispatch to local reserve and core processing."
    ),
    "flora_hub_exit_key": "hybrid buffer colony flora",
    "flora_hub_exit_aliases": [
        "buffer colony flora",
        "hybrid buffer flora",
        "hybrid colony flora",
    ],
    "fauna_staging_room_key": "Hybrid Buffer Colony Fauna Annex",
    "fauna_staging_room_desc": (
        "Fauna annex for the Hybrid Buffer Colony: leased ranges, containment, "
        "and split dispatch to local reserve and core processing."
    ),
    "fauna_hub_exit_key": "hybrid buffer colony fauna",
    "fauna_hub_exit_aliases": [
        "buffer colony fauna",
        "hybrid buffer fauna",
        "hybrid colony fauna",
    ],
    "flora_pad_prefix": "Hybrid Buffer Colony Flora Pad",
    "fauna_pad_prefix": "Hybrid Buffer Colony Fauna Pad",
    "flora_cell_desc_template": (
        "Hybrid Buffer Colony flora stand {cell}: harvest and split haul routing "
        "to local reserve then processing plant."
    ),
    "fauna_cell_desc_template": (
        "Hybrid Buffer Colony fauna range {cell}: harvest and split haul routing "
        "to local reserve then processing plant."
    ),
    "flora_site_suffix": "Stand",
    "fauna_site_suffix": "Range",
    "flora_deploy_tag": "npc_hybrid_buffer_colony_flora",
    "fauna_deploy_tag": "npc_hybrid_buffer_colony_fauna",
    "flora_plant_keys": (
        "Aurnom Flora Processing Plant",
        "Aurnom Ore Processing Plant",
    ),
    "fauna_plant_keys": (
        "Aurnom Fauna Processing Plant",
        "Aurnom Flora Processing Plant",
        "Aurnom Ore Processing Plant",
    ),
}

# Split-buffer mining bootstrap (shared runner: bootstrap_npc_split_buffer_colony).
HYBRID_SPLIT_BUFFER_BOOTSTRAP = {
    "tier_log_slug": "hybrid-buffer",
    "local_plant_fill_fraction": None,
    "log_prefix": "[npc-hybrid-buffer]",
    "staging_room_key": "Hybrid Buffer Colony Grid",
    "staging_room_desc": (
        "Service deck for the Hybrid Buffer Colony: pad telemetry, ore hoppers, and haulers that "
        "stage raw locally at the plant to half reserve capacity before selling overflow to the bay."
    ),
    "hub_to_staging_exit_key": "hybrid buffer colony",
    "hub_to_staging_aliases": [
        "buffer colony",
        "hybrid buffer",
        "hybrid colony grid",
    ],
    "staging_to_hub_exit_key": "promenade",
    "staging_to_hub_aliases": ["back", "exit", "out", "plex", "hub"],
    "cell_exit_prefix": "buffer pad ",
    "site_tag": "npc_hybrid_buffer_supply",
    "site_tag_category": "world",
    "pad_colony_prefix": "Hybrid Buffer Colony",
    "cell_room_desc_suffix": (
        "drill mast, hopper, and split haul routing to the processing plant."
    ),
    "site_room_desc": (
        "Hybrid Buffer Colony lease; catalog-wide feedstock with split local/plant haul delivery."
    ),
    "npc_units": NPC_HYBRID_BUFFER_UNITS,
    "resource_bio": HYBRID_BUFFER_RESOURCE_BIO,
}
