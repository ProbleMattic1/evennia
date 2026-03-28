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
    "Ashfall", "Vektor", "Keldrath", "Obsidian", "Dustwind", "Ironveil",
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


def generate_mining_site(is_jackpot=False):
    """
    Create a brand-new MiningSite in a new room with randomised deposit data.
    Returns the site object.  The site starts unclaimed.
    """
    from world.bootstrap_hub import get_hub_room
    from world.bootstrap_mining import _get_or_create_exit, _get_or_create_room

    name = _pick_site_name()
    existing = search_tag("mining_site", category="mining")
    existing_room_keys = {s.location.key for s in existing if s.location}
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

    hub = get_hub_room()
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


# ---------------------------------------------------------------------------
# Package-purchase entry point
# ---------------------------------------------------------------------------

def grant_random_claim_on_purchase(buyer):
    """
    Generate a fresh mining site and grant a claim to buyer.
    Returns (claim, is_jackpot).
    """
    is_jackpot = random.random() < JACKPOT_CHANCE
    site = generate_mining_site(is_jackpot=is_jackpot)
    claim = create_claim_for_site(site, buyer, is_jackpot=is_jackpot)
    return claim, is_jackpot
