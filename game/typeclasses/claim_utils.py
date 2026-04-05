"""
Claim creation, site generation, and random selection for package purchases.

Sites are generated dynamically — either on package purchase or by the
SiteDiscoveryEngine periodic script.  No sites are pre-seeded at startup.
"""
import random

from evennia import create_object, search_tag

JACKPOT_CHANCE = 0.005

JACKPOT_DEPOSIT = {
    "richness": 1.0,
    "base_output_tons": 25.0,
    "composition": {
        "rare_earth_concentrate": 0.30,
        "opal_seam": 0.25,
        "cobalt_ore": 0.25,
        "iron_ore": 0.20,
    },
    "depletion_rate": 0.001,
    "richness_floor": 0.20,
}

# Composition templates used by the site generator.
COMPOSITION_TEMPLATES = [
    {"iron_ore": 0.45, "copper_ore": 0.30, "nickel_ore": 0.15, "aluminum_ore": 0.10},
    {"iron_ore": 0.50, "sulfur_ore": 0.25, "silicate_dust": 0.15, "nickel_ore": 0.10},
    {"cobalt_ore": 0.35, "rare_earth_concentrate": 0.25, "opal_seam": 0.25, "quartz_matrix": 0.15},
    {"titanium_ore": 0.30, "cobalt_ore": 0.25, "tungsten_ore": 0.25, "iron_ore": 0.20},
    {"quartz_matrix": 0.30, "opal_seam": 0.30, "corundum_matrix": 0.25, "iron_ore": 0.15},
    {"copper_ore": 0.35, "lead_zinc_ore": 0.25, "nickel_ore": 0.25, "aluminum_ore": 0.15},
    {"rare_earth_concentrate": 0.30, "platinum_group_ore": 0.20, "cobalt_ore": 0.30, "tungsten_ore": 0.20},
    {"emerald_beryl_ore": 0.25, "diamond_kimberlite": 0.20, "corundum_matrix": 0.30, "quartz_matrix": 0.25},
]

SITE_NAME_PREFIXES = [
    "Industrial", "Vektor", "Keldrath", "Obsidian", "Dustwind", "Ironveil",
    "Cinderhollow", "Stonereach", "Grimcrest", "Frostbreak", "Dawnpeak",
    "Redscale", "Embervault", "Crystalfen", "Shadowmere", "Stormrift",
]

SITE_NAME_SUFFIXES = [
    "Basin", "Ridge", "Vein", "Hollow", "Shelf", "Canyon", "Plateau",
    "Drift", "Gorge", "Fissure", "Bluff", "Terrace", "Flat", "Ledge",
]


# ---------------------------------------------------------------------------
# Site generator
# ---------------------------------------------------------------------------

def _pick_site_name():
    """Generate a unique-ish procedural site name."""
    return f"{random.choice(SITE_NAME_PREFIXES)} {random.choice(SITE_NAME_SUFFIXES)}"


def _all_resource_site_room_keys():
    """Room keys used by any mining / flora / fauna claim site (avoid collisions)."""
    keys = set()
    for s in search_tag("mining_site", category="mining"):
        if s.location:
            keys.add(s.location.key)
    for s in search_tag("flora_site", category="flora"):
        if s.location:
            keys.add(s.location.key)
    for s in search_tag("fauna_site", category="fauna"):
        if s.location:
            keys.add(s.location.key)
    return keys


FLORA_SITE_NAME_PREFIXES = [
    "Verdant", "Canopy", "Spore", "Lichen", "Mycelial", "Hydropon",
    "Xenobloom", "Deeproot", "Glassfern", "Redmoss", "Starvine", "Biolume",
]

FLORA_SITE_NAME_SUFFIXES = [
    "Stand", "Grove", "Arbor", "Belt", "Terrace", "Vats", "Grid",
    "Annex", "Dome", "Ward", "Plot", "Range", "Nursery",
]

FAUNA_SITE_NAME_PREFIXES = [
    "Pelagic", "Chitin", "Synapse", "Benthic", "Roost", "Hive",
    "Strain", "Brood", "Feral", "Cryoherd", "Skimmer", "Weir",
]

FAUNA_SITE_NAME_SUFFIXES = [
    "Range", "Pen", "Weir", "Tank", "Yard", "Deck", "Pit",
    "Corral", "Lab", "Run", "Pool", "Nest", "Hatch",
]


def _pick_flora_site_name():
    return f"{random.choice(FLORA_SITE_NAME_PREFIXES)} {random.choice(FLORA_SITE_NAME_SUFFIXES)}"


def _pick_fauna_site_name():
    return f"{random.choice(FAUNA_SITE_NAME_PREFIXES)} {random.choice(FAUNA_SITE_NAME_SUFFIXES)}"


FLORA_COMPOSITION_TEMPLATES = [
    {"wild_harvest_biomass": 0.35, "structural_cane": 0.25, "algal_mat": 0.20, "deep_root_tuber": 0.20},
    {"lichen_aggregate": 0.30, "cellulose_pulp_bale": 0.25, "pollen_aggregate": 0.25, "vascular_sheath_fibre": 0.20},
    {"medicinal_sap": 0.25, "volatile_terpene_resin": 0.25, "spore_culture_mass": 0.25, "xenohybrid_foliage": 0.25},
    {"algal_mat": 0.40, "wild_harvest_biomass": 0.30, "structural_cane": 0.30},
    {"deep_root_tuber": 0.35, "lichen_aggregate": 0.35, "cellulose_pulp_bale": 0.30},
    {"pollen_aggregate": 0.30, "medicinal_sap": 0.35, "volatile_terpene_resin": 0.35},
    {"spore_culture_mass": 0.40, "xenohybrid_foliage": 0.35, "crystalline_nectar_concentrate": 0.25},
    {"bioluminescent_moss": 0.45, "heritage_seed_pod_lot": 0.30, "crystalline_nectar_concentrate": 0.25},
]

FAUNA_COMPOSITION_TEMPLATES = [
    {"pelagic_protein_slurry": 0.35, "chitin_microflake_lot": 0.25, "hemolymph_serum_batch": 0.20, "deep_benthic_silicate_gel": 0.20},
    {"keratin_fiber_bale": 0.30, "collagen_fibril_mass": 0.25, "arthropod_powder_aggregate": 0.25, "elastic_tendon_sheath_lot": 0.20},
    {"exotic_enzyme_gland_paste": 0.25, "neural_lipid_extract": 0.25, "symbiotic_microfauna_culture": 0.25, "xenofauna_myo_bundle": 0.25},
    {"hemolymph_serum_batch": 0.40, "pelagic_protein_slurry": 0.35, "chitin_microflake_lot": 0.25},
    {"deep_benthic_silicate_gel": 0.35, "keratin_fiber_bale": 0.35, "collagen_fibril_mass": 0.30},
    {"arthropod_powder_aggregate": 0.30, "exotic_enzyme_gland_paste": 0.35, "neural_lipid_extract": 0.35},
    {"symbiotic_microfauna_culture": 0.40, "xenofauna_myo_bundle": 0.35, "crystalline_venom_precipitate": 0.25},
    {"bioluminescent_scale_flake": 0.45, "heritage_genotype_embryo_lot": 0.30, "crystalline_venom_precipitate": 0.25},
]

JACKPOT_FLORA_DEPOSIT = {
    "richness": 1.0,
    "base_output_tons": 22.0,
    "composition": {
        "bioluminescent_moss": 0.28,
        "heritage_seed_pod_lot": 0.27,
        "crystalline_nectar_concentrate": 0.25,
        "xenohybrid_foliage": 0.20,
    },
    "depletion_rate": 0.001,
    "richness_floor": 0.18,
}

JACKPOT_FAUNA_DEPOSIT = {
    "richness": 1.0,
    "base_output_tons": 22.0,
    "composition": {
        "bioluminescent_scale_flake": 0.28,
        "heritage_genotype_embryo_lot": 0.27,
        "crystalline_venom_precipitate": 0.25,
        "xenofauna_myo_bundle": 0.20,
    },
    "depletion_rate": 0.001,
    "richness_floor": 0.18,
}


def generate_mining_site(is_jackpot=False, venue_id="nanomega_core"):
    """
    Create a brand-new MiningSite in a new room with randomised deposit data.
    Returns the site object.  The site starts unclaimed.
    """
    from world.bootstrap_mining import _get_or_create_exit, _get_or_create_room
    from world.venue_resolve import hub_room_for_venue
    from world.venues import apply_venue_metadata

    name = _pick_site_name()
    existing_room_keys = _all_resource_site_room_keys()
    attempts = 0
    while name in existing_room_keys and attempts < 20:
        name = _pick_site_name()
        attempts += 1

    room = _get_or_create_room(
        name,
        desc=(
            f"A remote extraction zone known as {name}. Survey drones have "
            "flagged mineral-bearing strata beneath the surface. "
            "The site is unclaimed and ready for development."
        ),
    )
    apply_venue_metadata(room, venue_id)

    hub = hub_room_for_venue(venue_id)
    if hub:
        alias = name.lower().split()[0]
        _get_or_create_exit(name.lower(), [alias], hub, room)
        _get_or_create_exit(
            "promenade", ["back", "exit", "out", "plex", "hub"], room, hub,
        )

    if is_jackpot:
        deposit = dict(JACKPOT_DEPOSIT)
        hazard = round(random.uniform(0.02, 0.10), 2)
    else:
        deposit = {
            "richness": round(random.uniform(0.40, 0.95), 2),
            "base_output_tons": round(random.uniform(8.0, 20.0), 1),
            "composition": dict(random.choice(COMPOSITION_TEMPLATES)),
            "depletion_rate": round(random.uniform(0.001, 0.004), 3),
            "richness_floor": round(random.uniform(0.08, 0.18), 2),
        }
        hazard = round(random.uniform(0.05, 0.55), 2)

    site = create_object(
        "typeclasses.mining.MiningSite",
        key=f"{name} Deposit",
        location=room,
        home=room,
    )
    site.db.desc = (
        f"Survey stakes mark a claim boundary at {name}. "
        "Core samples indicate workable mineral concentrations."
    )
    site.db.deposit = deposit
    site.db.hazard_level = hazard
    try:
        from web.ui.world_graph import invalidate_world_graph_cache

        invalidate_world_graph_cache()
    except Exception:
        pass
    return site


# ---------------------------------------------------------------------------
# Unclaimed-site helpers (used by discovery script)
# ---------------------------------------------------------------------------

def get_unclaimed_sites():
    sites = search_tag("mining_site", category="mining")
    return [s for s in sites if not getattr(s.db, "is_claimed", False)]


def get_unclaimed_flora_sites():
    sites = search_tag("flora_site", category="flora")
    return [s for s in sites if not getattr(s.db, "is_claimed", False)]


def get_unclaimed_fauna_sites():
    sites = search_tag("fauna_site", category="fauna")
    return [s for s in sites if not getattr(s.db, "is_claimed", False)]


def generate_flora_site(is_jackpot=False, venue_id="nanomega_core"):
    """
    Create a new FloraSite in a new room. Unclaimed; allowed_purposes flora.
    """
    from world.bootstrap_mining import _get_or_create_exit, _get_or_create_room
    from world.venue_resolve import hub_room_for_venue
    from world.venues import apply_venue_metadata

    name = _pick_flora_site_name()
    existing_room_keys = _all_resource_site_room_keys()
    attempts = 0
    while name in existing_room_keys and attempts < 20:
        name = _pick_flora_site_name()
        attempts += 1

    room = _get_or_create_room(
        name,
        desc=(
            f"A botanical harvest zone, {name}. Survey tags an unleased stand "
            "with viable cultivation indices; the plot is unclaimed."
        ),
    )
    apply_venue_metadata(room, venue_id)
    hub = hub_room_for_venue(venue_id)
    if hub:
        alias = name.lower().split()[0]
        _get_or_create_exit(name.lower(), [alias], hub, room)
        _get_or_create_exit(
            "promenade", ["back", "exit", "out", "plex", "hub"], room, hub,
        )

    if is_jackpot:
        deposit = dict(JACKPOT_FLORA_DEPOSIT)
        hazard = round(random.uniform(0.02, 0.10), 2)
    else:
        deposit = {
            "richness": round(random.uniform(0.40, 0.95), 2),
            "base_output_tons": round(random.uniform(8.0, 20.0), 1),
            "composition": dict(random.choice(FLORA_COMPOSITION_TEMPLATES)),
            "depletion_rate": round(random.uniform(0.001, 0.004), 3),
            "richness_floor": round(random.uniform(0.08, 0.18), 2),
        }
        hazard = round(random.uniform(0.05, 0.45), 2)

    site = create_object(
        "typeclasses.flora.FloraSite",
        key=f"{name} Flora Stand",
        location=room,
        home=room,
    )
    site.db.desc = (
        f"Lease stakes outline a harvest boundary at {name}. "
        "Botanical assays show stable yield potential."
    )
    site.db.deposit = deposit
    site.db.hazard_level = hazard
    site.db.allowed_purposes = ["flora"]
    try:
        from web.ui.world_graph import invalidate_world_graph_cache

        invalidate_world_graph_cache()
    except Exception:
        pass
    return site


def generate_fauna_site(is_jackpot=False, venue_id="nanomega_core"):
    """
    Create a new FaunaSite in a new room. Unclaimed; allowed_purposes fauna.
    """
    from world.bootstrap_mining import _get_or_create_exit, _get_or_create_room
    from world.venue_resolve import hub_room_for_venue
    from world.venues import apply_venue_metadata

    name = _pick_fauna_site_name()
    existing_room_keys = _all_resource_site_room_keys()
    attempts = 0
    while name in existing_room_keys and attempts < 20:
        name = _pick_fauna_site_name()
        attempts += 1

    room = _get_or_create_room(
        name,
        desc=(
            f"A fauna culture range known as {name}. Telemetry marks an unleased "
            "harvest band with viable biomass indices; the range is unclaimed."
        ),
    )
    apply_venue_metadata(room, venue_id)
    hub = hub_room_for_venue(venue_id)
    if hub:
        alias = name.lower().split()[0]
        _get_or_create_exit(name.lower(), [alias], hub, room)
        _get_or_create_exit(
            "promenade", ["back", "exit", "out", "plex", "hub"], room, hub,
        )

    if is_jackpot:
        deposit = dict(JACKPOT_FAUNA_DEPOSIT)
        hazard = round(random.uniform(0.02, 0.10), 2)
    else:
        deposit = {
            "richness": round(random.uniform(0.40, 0.95), 2),
            "base_output_tons": round(random.uniform(8.0, 20.0), 1),
            "composition": dict(random.choice(FAUNA_COMPOSITION_TEMPLATES)),
            "depletion_rate": round(random.uniform(0.001, 0.004), 3),
            "richness_floor": round(random.uniform(0.08, 0.18), 2),
        }
        hazard = round(random.uniform(0.05, 0.45), 2)

    site = create_object(
        "typeclasses.fauna.FaunaSite",
        key=f"{name} Fauna Range",
        location=room,
        home=room,
    )
    site.db.desc = (
        f"Range beacons delimit a harvest envelope at {name}. "
        "Culture assays indicate stable production potential."
    )
    site.db.deposit = deposit
    site.db.hazard_level = hazard
    site.db.allowed_purposes = ["fauna"]
    try:
        from web.ui.world_graph import invalidate_world_graph_cache

        invalidate_world_graph_cache()
    except Exception:
        pass
    return site


# ---------------------------------------------------------------------------
# Claim creation
# ---------------------------------------------------------------------------

def create_claim_for_site(site, owner, is_jackpot=False):
    from typeclasses.claims import MiningClaim

    room_key = site.location.key if site.location else site.key
    base = f"Claim: {room_key}"
    if is_jackpot:
        base = f"Elite Claim: {room_key} \u2605"
    claim = create_object(
        "typeclasses.claims.MiningClaim",
        key=base,
        location=owner,
        home=owner,
    )
    claim.key = f"{base} #{claim.id}"
    claim.db.site_ref = site
    claim.db.site_key = room_key
    claim.db.is_jackpot = is_jackpot
    if is_jackpot:
        claim.db.desc = f"An elite claim at {room_key} — exceptional deposit quality."
    else:
        claim.db.desc = f"Deed to deploy at {room_key}."
    claim.move_to(owner, quiet=True)
    ap = getattr(site.db, "allowed_purposes", None) or ["mining"]
    claim.db.allowed_purposes = list(ap)
    return claim


def create_flora_claim_for_site(site, owner, is_jackpot=False):
    from typeclasses.claims import FloraClaim

    room_key = site.location.key if site.location else site.key
    base = f"Flora Claim: {room_key}"
    if is_jackpot:
        base = f"Elite Flora Claim: {room_key} \u2605"
    claim = create_object(
        "typeclasses.claims.FloraClaim",
        key=base,
        location=owner,
        home=owner,
    )
    claim.key = f"{base} #{claim.id}"
    claim.db.site_ref = site
    claim.db.site_key = room_key
    claim.db.is_jackpot = is_jackpot
    if is_jackpot:
        claim.db.desc = f"An elite flora claim at {room_key} — exceptional stand quality."
    else:
        claim.db.desc = f"Flora deed to deploy at {room_key}."
    claim.move_to(owner, quiet=True)
    ap = getattr(site.db, "allowed_purposes", None) or ["flora"]
    claim.db.allowed_purposes = list(ap)
    return claim


def create_fauna_claim_for_site(site, owner, is_jackpot=False):
    from typeclasses.claims import FaunaClaim

    room_key = site.location.key if site.location else site.key
    base = f"Fauna Claim: {room_key}"
    if is_jackpot:
        base = f"Elite Fauna Claim: {room_key} \u2605"
    claim = create_object(
        "typeclasses.claims.FaunaClaim",
        key=base,
        location=owner,
        home=owner,
    )
    claim.key = f"{base} #{claim.id}"
    claim.db.site_ref = site
    claim.db.site_key = room_key
    claim.db.is_jackpot = is_jackpot
    if is_jackpot:
        claim.db.desc = f"An elite fauna claim at {room_key} — exceptional range quality."
    else:
        claim.db.desc = f"Fauna deed to deploy at {room_key}."
    claim.move_to(owner, quiet=True)
    ap = getattr(site.db, "allowed_purposes", None) or ["fauna"]
    claim.db.allowed_purposes = list(ap)
    return claim


def create_claim_for_resource_site(site, owner, is_jackpot=False):
    """Grant the correct deed type for a mining, flora, or fauna site."""
    if not site:
        return None
    if site.tags.has("mining_site", category="mining"):
        return create_claim_for_site(site, owner, is_jackpot=is_jackpot)
    if site.tags.has("flora_site", category="flora"):
        return create_flora_claim_for_site(site, owner, is_jackpot=is_jackpot)
    if site.tags.has("fauna_site", category="fauna"):
        return create_fauna_claim_for_site(site, owner, is_jackpot=is_jackpot)
    return None


# ---------------------------------------------------------------------------
# Package-purchase entry point
# ---------------------------------------------------------------------------

def grant_random_claim_on_purchase(buyer):
    """
    Generate a fresh mining site and grant a claim to buyer.
    Returns (claim, is_jackpot).
    """
    from world.venue_resolve import venue_id_for_object

    is_jackpot = random.random() < JACKPOT_CHANCE
    vid = venue_id_for_object(buyer) if buyer else None
    if not vid:
        vid = "nanomega_core"
    site = generate_mining_site(is_jackpot=is_jackpot, venue_id=vid)
    claim = create_claim_for_site(site, buyer, is_jackpot=is_jackpot)
    return claim, is_jackpot


def grant_random_flora_claim_on_purchase(buyer):
    """Generate a FloraSite and FloraClaim. Returns (claim, is_jackpot)."""
    from world.venue_resolve import venue_id_for_object

    is_jackpot = random.random() < JACKPOT_CHANCE
    vid = venue_id_for_object(buyer) if buyer else None
    if not vid:
        vid = "nanomega_core"
    site = generate_flora_site(is_jackpot=is_jackpot, venue_id=vid)
    claim = create_flora_claim_for_site(site, buyer, is_jackpot=is_jackpot)
    return claim, is_jackpot


def grant_random_fauna_claim_on_purchase(buyer):
    """Generate a FaunaSite and FaunaClaim. Returns (claim, is_jackpot)."""
    from world.venue_resolve import venue_id_for_object

    is_jackpot = random.random() < JACKPOT_CHANCE
    vid = venue_id_for_object(buyer) if buyer else None
    if not vid:
        vid = "nanomega_core"
    site = generate_fauna_site(is_jackpot=is_jackpot, venue_id=vid)
    claim = create_fauna_claim_for_site(site, buyer, is_jackpot=is_jackpot)
    return claim, is_jackpot
