"""
Mining system — Pass 3.

Components
----------
RESOURCE_CATALOG   15 commodity definitions with base prices per ton
MiningSite         adds license_level, tax_rate, hazard_level, hazard events
MiningRig          wear, mode, power, family, purity, maintenance (Pass 2)
MiningStorage      capacity_tons hard-cap (Pass 2)
MiningEngine       global persistent script — unchanged interface

Pass-1/2 db fields are preserved; all new fields use .get() with safe defaults.

Pass-3 additions
----------------
get_commodity_bid()     per-ton when a miner sells raw (bid; basis when the Plant buys ore).
get_commodity_ask()     per-ton when a buyer purchases raw from the Plant (bid × COMMODITY_ASK_OVER_BID).
get_commodity_price()  alias for get_commodity_bid() (backward compatibility).

MiningSite.db additions:
  license_level   int    0=unlicensed, 1=standard, 2=certified
  tax_rate        float  0.0–0.25; extraction tax per cycle deposited to treasury
  hazard_level    float  0.0–1.0; probability weight for random hazard events

Hazard events (triggered stochastically in process_cycle):
  raid            NPC steals a fraction of storage inventory
  geological      Reduces this cycle's output by 20–50 %

Production formula (unchanged from Pass 2 — see that docstring).
"""

import random

from evennia import search_tag
from evennia.objects.objects import DefaultObject
from evennia.utils import logger

from world.time import (
    MINING_DELIVERY_PERIOD,
    ceil_period,
    floor_period,
    next_period_after_completed,
    parse_iso,
    to_iso,
    utc_now,
)

from .objects import ObjectParent
from .scripts import Script


CYCLE_SECONDS = MINING_DELIVERY_PERIOD  # backward compat; global UTC grid (3h)
MAX_CATCHUP_CYCLES = 10  # cap back-fill after long downtime

# Spread process_cycle work across engine ticks (logical due times unchanged).
MINING_ENGINE_STAGGER_MOD = 4

WEAR_PER_CYCLE_BASE = 0.02  # ~50 cycles (25 days) to full wear at base settings

# Rig tuning tables
MODE_OUTPUT_MODIFIERS = {"balanced": 1.0,  "selective": 0.75, "overdrive": 1.4}
MODE_WEAR_MODIFIERS   = {"balanced": 1.0,  "selective": 0.8,  "overdrive": 2.0}

POWER_OUTPUT_MODIFIERS = {"low": 0.70, "normal": 1.0, "high": 1.30}
POWER_WEAR_MODIFIERS   = {"low": 0.60, "normal": 1.0, "high": 1.50}

MAINTENANCE_WEAR_MODIFIERS = {"low": 1.50, "standard": 1.0, "premium": 0.60}
BREAKDOWN_BASE             = {"low": 0.08, "standard": 0.03, "premium": 0.01}

WEAR_OUTPUT_PENALTY = 0.30  # 30 % output loss at full wear


def rig_normalized_mode_power(rig):
    """
    Return (mode, power_level) strings valid for output/wear modifier tables.
    Missing or invalid db fields default to balanced / normal.
    """
    db = getattr(rig, "db", None)
    mode = getattr(db, "mode", None) if db else None
    power = getattr(db, "power_level", None) if db else None
    if mode not in MODE_OUTPUT_MODIFIERS:
        mode = "balanced"
    if power not in POWER_OUTPUT_MODIFIERS:
        power = "normal"
    return mode, power


def rig_output_modifiers(rig):
    """Return (mode_mult, power_mult) for ton / CR estimates and process_cycle."""
    mode, power = rig_normalized_mode_power(rig)
    return MODE_OUTPUT_MODIFIERS[mode], POWER_OUTPUT_MODIFIERS[power]


# Hazard constants (Pass 3)
HAZARD_CHANCE_BASE = 0.06   # base 6 % per cycle at hazard_level 1.0
HAZARD_RAID_STEAL_FRAC = 0.20   # raid steals up to 20 % of storage
HAZARD_GEO_OUTPUT_MIN  = 0.50   # geological event reduces output to 50–80 %
HAZARD_GEO_OUTPUT_MAX  = 0.80

# License constants (Pass 3)
LICENSE_COST = {1: 2000, 2: 8000}   # cr cost to register each level
LICENSE_TAX_RATE_DEFAULT = 0.05     # 5 % extraction tax for licensed operations

# Rig field repair — ledger vendor:rig-repair; RIG_REPAIR_TAX_RATE to treasury:alpha-prime (shop-style split)
RIG_REPAIR_VENDOR_ID = "rig-repair"
RIG_REPAIR_TAX_RATE = 0.03
RIG_REPAIR_BASE_CR = 800
RIG_REPAIR_PER_RATING_CR = 400
RIG_REPAIR_WEAR_UNIT_CR = 25  # credits per wear percentage point
RIG_REPAIR_MIN_TOTAL_CR = 350

# Survey tiers — what each level reveals
SURVEY_LEVELS = {
    0: "unsurveyed",
    1: "basic scan",
    2: "standard assessment",
    3: "full geological survey",
}

# Purity thresholds (cr/t minimum to include in selective output)
PURITY_THRESHOLDS = {"low": 0, "medium": 100, "high": 300}

# Resource category to target_family membership
FAMILY_CATEGORIES = {
    "metals": {"standard_metal", "exotic_metal"},
    "gems":   {"gem_bearing"},
    "mixed":  {"standard_metal", "exotic_metal", "gem_bearing"},
}


def mining_owner_skips_wear_and_breakdown(owner):
    """
    True when this owner's mines use NPC-style rig rules: no wear accumulation,
    no breakdown random roll, and output ignores stored wear.

    - All characters with db.is_npc (industrial NPCs).
    - Seeded characters with db.mining_owner_uses_npc_production (e.g. Marcus Killstar).

    Hazards remain controlled per-site via db.hazard_level (use 0 to disable).
    """
    if not owner:
        return False
    db = getattr(owner, "db", None)
    if db is None:
        return False
    if getattr(db, "is_npc", False):
        return True
    return bool(getattr(db, "mining_owner_uses_npc_production", False))


# ---------------------------------------------------------------------------
# Resource catalog
# ---------------------------------------------------------------------------

RESOURCE_CATALOG = {
    # Standard metals (common)
    "iron_ore": {
        "name": "Iron Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 90,
        "desc": "Common iron ore suitable for basic smelting.",
    },
    "aluminum_ore": {
        "name": "Aluminum Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 110,
        "desc": "Lightweight bauxite-rich ore for industrial processing.",
    },
    "lead_zinc_ore": {
        "name": "Lead-Zinc Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 150,
        "desc": "Mixed sulfide ore carrying lead and zinc content.",
    },
    "copper_ore": {
        "name": "Copper Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 180,
        "desc": "Chalcopyrite-bearing ore for electrical and structural use.",
    },
    "nickel_ore": {
        "name": "Nickel Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 240,
        "desc": "Nickel-bearing pentlandite ore for alloys and coatings.",
    },
    "titanium_ore": {
        "name": "Titanium Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 520,
        "desc": "Ilmenite and rutile ore for aerospace-grade titanium.",
    },
    "sulfur_ore": {
        "name": "Sulfur Ore",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 80,
        "desc": "Raw sulfur-bearing ore for chemical processing.",
    },
    "silicate_dust": {
        "name": "Silicate Dust",
        "category": "standard_metal",
        "rarity": "common",
        "base_price_cr_per_ton": 60,
        "desc": "Fine silicate particulate for industrial use.",
    },
    # Exotic / strategic metals
    "cobalt_ore": {
        "name": "Cobalt Ore",
        "category": "exotic_metal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 650,
        "desc": "Strategic cobalt ore critical for battery and catalyst production.",
    },
    "tungsten_ore": {
        "name": "Tungsten Ore",
        "category": "exotic_metal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 780,
        "desc": "Wolframite-scheelite ore with extreme hardness applications.",
    },
    "rare_earth_concentrate": {
        "name": "Rare-Earth Concentrate",
        "category": "exotic_metal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 950,
        "desc": "Mixed rare-earth oxide concentrate for advanced electronics.",
    },
    "platinum_group_ore": {
        "name": "Platinum-Group Ore",
        "category": "exotic_metal",
        "rarity": "rare",
        "base_price_cr_per_ton": 3200,
        "desc": "Low-grade ore bearing platinum, palladium, and rhodium.",
    },
    # Gem-bearing materials
    "quartz_matrix": {
        "name": "Quartz Matrix",
        "category": "gem_bearing",
        "rarity": "common",
        "base_price_cr_per_ton": 260,
        "desc": "Silica-rich matrix with embedded quartz formations.",
    },
    "opal_seam": {
        "name": "Opal Seam",
        "category": "gem_bearing",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 1500,
        "desc": "Hydrated silica seam with play-of-color opal inclusions.",
    },
    "corundum_matrix": {
        "name": "Corundum Matrix",
        "category": "gem_bearing",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 1900,
        "desc": "Alumina-rich host rock bearing sapphire and ruby corundum.",
    },
    "emerald_beryl_ore": {
        "name": "Emerald Beryl Ore",
        "category": "gem_bearing",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 2300,
        "desc": "Beryllium-silicate matrix with chromium-rich emerald zones.",
    },
    "diamond_kimberlite": {
        "name": "Diamond Kimberlite",
        "category": "gem_bearing",
        "rarity": "rare",
        "base_price_cr_per_ton": 3400,
        "desc": "Kimberlite pipe material bearing raw diamond crystals.",
    },
}

# Rarity scores for resource_rarity_tier (weighted average)
RARITY_SCORES = {"common": 0, "uncommon": 1, "rare": 2}


# ---------------------------------------------------------------------------
# Timestamp helpers (delegate to world.time)
# ---------------------------------------------------------------------------

def _now():
    return utc_now()


def _parse_ts(ts_str):
    """Return a timezone-aware datetime from an isoformat string, or None."""
    return parse_iso(ts_str)


def _fmt_ts(dt):
    """Return isoformat string from a datetime, or None."""
    return to_iso(dt)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_mining_engine(create_missing=True):
    """Return the global MiningEngine script, creating it if needed."""
    from evennia import GLOBAL_SCRIPTS, create_script, search_script

    try:
        eng = GLOBAL_SCRIPTS.mining_engine
        if eng:
            return eng
    except Exception:
        pass

    found = search_script("mining_engine")
    if found:
        return found[0]

    if create_missing:
        return create_script("typeclasses.mining.MiningEngine")
    return None


COMMODITY_BID_DISCOUNT = 0.97   # Plant buys ore at 3% below catalog base price
COMMODITY_ASK_PREMIUM  = 1.03   # Plant sells ore at 3% above catalog base price
COMMODITY_ASK_OVER_BID = COMMODITY_ASK_PREMIUM  # backward-compat alias


def get_commodity_bid(resource_key, location=None):
    """Credits per ton when a miner sells raw ore to the Plant (bid = base price − 3%)."""
    from typeclasses.commodity_demand import get_commodity_demand_engine

    info = RESOURCE_CATALOG.get(resource_key, {})
    base = float(info.get("base_price_cr_per_ton", 0))
    if base <= 0:
        return 0
    eng = get_commodity_demand_engine(create_missing=False)
    mult = eng.get_market_multiplier(resource_key) if eng else 1.0
    return max(0, int(round(base * mult * COMMODITY_BID_DISCOUNT)))


def get_commodity_ask(resource_key, location=None):
    """Credits per ton when a buyer purchases raw from the Processing Plant (ask = base price + 3%)."""
    from typeclasses.commodity_demand import get_commodity_demand_engine

    info = RESOURCE_CATALOG.get(resource_key, {})
    base = float(info.get("base_price_cr_per_ton", 0))
    if base <= 0:
        return 0
    eng = get_commodity_demand_engine(create_missing=False)
    mult = eng.get_market_multiplier(resource_key) if eng else 1.0
    return max(0, int(round(base * mult * COMMODITY_ASK_PREMIUM)))


def get_commodity_price(resource_key, location=None):
    """Backward-compatible alias for get_commodity_bid."""
    return get_commodity_bid(resource_key, location=location)


# ---------------------------------------------------------------------------
# Helpers for survey display
# ---------------------------------------------------------------------------

def _richness_tier(richness):
    """Convert a float richness value to a descriptive tier string."""
    r = float(richness)
    if r < 0.40:
        return "poor"
    if r < 0.70:
        return "moderate"
    if r < 1.10:
        return "rich"
    return "very rich"


def _volume_tier(richness, base_tons):
    """
    Volume value classification: Lean -> Deep.
    Based on effective output volume (base_tons * richness) in t/cycle.
    """
    volume = float(richness or 0) * float(base_tons or 0)
    if volume >= 20:
        return "Deep", "sky"
    if volume >= 14:
        return "Rich", "emerald"
    if volume >= 8:
        return "Moderate", "amber"
    return "Lean", "zinc"


def _resource_rarity_tier(composition):
    """
    Resource rarity classification: Common -> Rare.
    Weighted average of resource rarities in composition.
    """
    if not composition:
        return "Common", "zinc"
    total_frac = 0
    weighted_score = 0
    for key, frac in composition.items():
        rarity = RESOURCE_CATALOG.get(key, {}).get("rarity", "common")
        score = RARITY_SCORES.get(rarity, 0)
        f = float(frac)
        weighted_score += f * score
        total_frac += f
    if total_frac <= 0:
        return "Common", "zinc"
    avg = weighted_score / total_frac
    if avg >= 1.5:
        return "Rare", "violet"
    if avg >= 0.6:
        return "Uncommon", "amber"
    return "Common", "zinc"


def estimated_site_value_per_cycle_cr(site):
    """
    Estimated credits from one production cycle at local bid prices.
    Matches claim detail and dashboard mine rows: applies rig / mode / power / wear
    when the site is active with an operational rig; otherwise base_tons * richness.
    """
    if not site or not getattr(site, "db", None):
        return 0
    deposit = site.db.deposit or {}
    richness = float(deposit.get("richness", 0) or 0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)
    raw_comp = deposit.get("composition") or {}
    loc = site.location

    installed = [r for r in (site.db.rigs or []) if r]
    operational = [r for r in installed if r.db.is_operational]
    active_rig = min(operational, key=lambda r: r.db.wear) if operational else None

    total = 0.0
    if site.is_active and active_rig:
        rig_rating = float(active_rig.db.rig_rating or 0)
        wear_mod = 1.0 - (float(active_rig.db.wear or 0) * WEAR_OUTPUT_PENALTY)
        mode_mod, power_mod = rig_output_modifiers(active_rig)
        tons_out = (
            base_tons
            * richness
            * rig_rating
            * mode_mod
            * power_mod
            * wear_mod
        )
        for k, frac in raw_comp.items():
            total += tons_out * float(frac) * get_commodity_bid(k, location=loc)
    else:
        tons_out = base_tons * richness
        for k, frac in raw_comp.items():
            total += tons_out * float(frac) * get_commodity_bid(k, location=loc)
    return int(round(total))


def _jitter(value, pct=0.15):
    """Return value ± pct (relative), rounded to 2dp."""
    delta = float(value) * pct
    return round(float(value) + random.uniform(-delta, delta), 2)


def _composition_families(composition):
    """Return a set of family names present in the composition."""
    families = set()
    for key in composition:
        cat = RESOURCE_CATALOG.get(key, {}).get("category", "")
        for fam, cats in FAMILY_CATEGORIES.items():
            if cat in cats and fam != "mixed":
                families.add(fam)
    return families


# ---------------------------------------------------------------------------
# MiningSite
# ---------------------------------------------------------------------------

class MiningSite(ObjectParent, DefaultObject):
    """
    A claimable mineral deposit placed in a room.

    Pass-2 db additions
    -------------------
    db.survey_level  int   0-3; advanced by the survey command each use
    deposit dict gains:
        depletion_rate   float  richness lost per cycle (default 0.002)
        richness_floor   float  minimum richness (default 0.10)
    db.last_ore_deposit_at  str  ISO UTC when ore last hit linked storage (hauler pickup +15m)
    """

    def at_object_creation(self):
        self.db.is_mining_site = True
        self.db.is_claimed = False
        self.db.owner = None
        self.db.rigs = []
        self.db.linked_storage = None
        self.db.next_cycle_at = None
        self.db.last_ore_deposit_at = None
        self.db.last_processed_at = None
        self.db.cycle_log = []
        self.db.survey_level = 0
        self.db.deposit = {
            "richness": 1.0,
            "base_output_tons": 10.0,
            "composition": {"iron_ore": 1.0},
            "depletion_rate": 0.002,
            "richness_floor": 0.10,
        }
        # Pass 3
        self.db.license_level = 0
        self.db.tax_rate = 0.0
        self.db.hazard_level = 0.0
        self.db.hazard_log = []
        self.tags.add("mining_site", category="mining")
        self.db.allowed_purposes = ["mining"]
        self.locks.add("get:false()")

    def at_init(self):
        """
        Persisted sites may predate db.rigs or list fields; normalize so
        iteration never sees None (avoids 500s in dashboard/API).
        """
        super().at_init()
        if self.db.rigs is None:
            self.db.rigs = []
        if self.db.cycle_log is None:
            self.db.cycle_log = []
        if self.db.hazard_log is None:
            self.db.hazard_log = []
        if self.db.deposit is None:
            self.db.deposit = {
                "richness": 1.0,
                "base_output_tons": 10.0,
                "composition": {"iron_ore": 1.0},
                "depletion_rate": 0.002,
                "richness_floor": 0.10,
            }
        if self.db.survey_level is None:
            self.db.survey_level = 0
        if self.db.license_level is None:
            self.db.license_level = 0
        if self.db.tax_rate is None:
            self.db.tax_rate = 0.0
        if self.db.hazard_level is None:
            self.db.hazard_level = 0.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self):
        if not self.db.is_claimed or not self.db.owner:
            return False
        if not self.db.linked_storage:
            return False
        rigs = self.db.rigs
        if not rigs:
            return False
        return any(rig.db.is_operational for rig in rigs if rig)

    # ------------------------------------------------------------------
    # Survey
    # ------------------------------------------------------------------

    def advance_survey(self):
        """
        Advance survey_level by 1 (max 3).
        Returns (new_level, report_string).
        """
        current = int(self.db.survey_level or 0)
        if current >= 3:
            return current, "This site has already been fully surveyed."
        new_level = current + 1
        self.db.survey_level = new_level
        report = self.get_survey_report(level=new_level)
        return new_level, report

    def get_survey_report(self, level=None):
        """
        Return a survey report at the given (or current) level.

        Level 0 — basic presence only
        Level 1 — richness tier + composition family
        Level 2 — approximate richness + named resources with ±15 % estimates
        Level 3 — exact richness + exact composition
        """
        level = int(level if level is not None else (self.db.survey_level or 0))
        deposit = self.db.deposit or {}
        richness = float(deposit.get("richness", 1.0))
        base_tons = float(deposit.get("base_output_tons", 10.0))
        composition = deposit.get("composition", {})
        level_label = SURVEY_LEVELS.get(level, "?")

        lines = [
            f"|wSurvey Report: {self.key}|n  [{level_label}]",
        ]

        if level == 0:
            lines.append("  A mineral deposit is present but has not been assessed.")
            lines.append("  Use |wsurvey|n to begin a geological scan.")
            return "\n".join(lines)

        claimed_str = (
            "yes — by " + site_owner.key
            if (self.db.is_claimed and (site_owner := self.db.owner))
            else "no"
        )
        lines.append(f"  Claimed : {claimed_str}")

        if level == 1:
            lines.append(f"  Richness: {_richness_tier(richness)}")
            fams = _composition_families(composition)
            lines.append(f"  Content : {', '.join(sorted(fams)) or 'unknown'}")
            est_low = round(base_tons * richness * 0.7, 1)
            est_high = round(base_tons * richness * 1.3, 1)
            lines.append(f"  Est. output (per cycle): {est_low}–{est_high} t")
            return "\n".join(lines)

        if level == 2:
            approx_richness = _jitter(richness, 0.15)
            lines.append(f"  Richness: ~{approx_richness:.2f}  ({_richness_tier(richness)})")
            approx_tons = _jitter(base_tons * richness, 0.15)
            lines.append(f"  Est. output (per cycle): ~{approx_tons:.1f} t")
            lines.append("  Composition (estimated):")
            for key, frac in composition.items():
                info = RESOURCE_CATALOG.get(key, {})
                name = info.get("name", key)
                approx_pct = max(1, int(_jitter(float(frac) * 100, 0.15)))
                cr = info.get("base_price_cr_per_ton", 0)
                lines.append(f"    {name:<28} ~{approx_pct:>3}%   {cr:,} cr/t")
            return "\n".join(lines)

        # level 3 — exact
        lines.append(f"  Richness : {richness:.3f}  ({_richness_tier(richness)})")
        lines.append(f"  Base output: {base_tons} t/cycle")
        dep_rate = deposit.get("depletion_rate", 0.002)
        floor = deposit.get("richness_floor", 0.10)
        lines.append(f"  Depletion rate : {dep_rate}/cycle  (floor {floor})")
        lines.append("  Composition (exact):")
        for key, frac in composition.items():
            info = RESOURCE_CATALOG.get(key, {})
            name = info.get("name", key)
            pct = int(float(frac) * 100)
            cr = info.get("base_price_cr_per_ton", 0)
            est = round(base_tons * richness * float(frac), 2)
            lines.append(
                f"    {name:<28} {pct:>3}%   ~{est:.2f} t/cycle   {cr:,} cr/t"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Status report
    # ------------------------------------------------------------------

    def get_status_report(self, looker=None):
        owner_str = self.db.owner.key if self.db.owner else "unclaimed"
        rigs = [r for r in (self.db.rigs or []) if r]
        storage = self.db.linked_storage
        storage_str = storage.key if storage else "none"

        deposit = self.db.deposit or {}
        richness = deposit.get("richness", "?")
        base_tons = deposit.get("base_output_tons", "?")
        composition = deposit.get("composition", {})
        dep_rate = deposit.get("depletion_rate", 0.002)

        comp_lines = []
        for key, frac in composition.items():
            info = RESOURCE_CATALOG.get(key, {})
            name = info.get("name", key)
            pct = int(float(frac) * 100)
            cr = info.get("base_price_cr_per_ton", 0)
            comp_lines.append(f"      {name}: {pct}%  ({cr:,} cr/t)")
        comp_str = "\n".join(comp_lines) or "      Unknown"

        next_cycle = self.db.next_cycle_at
        if next_cycle:
            next_cycle = next_cycle[:16].replace("T", " ") + " UTC"
        else:
            next_cycle = "not scheduled"

        active_flag = "|gyes|n" if self.is_active else "|rno|n"
        survey_label = SURVEY_LEVELS.get(int(self.db.survey_level or 0), "?")
        license_labels = {0: "|runsurveyed / unlicensed|n", 1: "|ystandard|n", 2: "|gcertified|n"}
        license_str = license_labels.get(int(self.db.license_level or 0), "?")
        tax_str = f"{int(float(self.db.tax_rate or 0) * 100)}%"
        hazard_str = f"{int(float(self.db.hazard_level or 0) * 100)}%"

        rig_lines = []
        for r in rigs:
            wear_pct = int(r.db.wear * 100)
            wear_color = "|g" if wear_pct < 40 else "|y" if wear_pct < 75 else "|r"
            op_label = "|gOP|n" if r.db.is_operational else "|rBROKEN|n"
            rig_lines.append(
                f"    {r.key}  {op_label}  wear {wear_color}{wear_pct}%|n"
            )
        rig_block = "\n".join(rig_lines) if rig_lines else "    none"

        storage_cap_str = ""
        if storage:
            cap = float(storage.db.capacity_tons)
            used = storage.total_mass()
            storage_cap_str = f"\n  Storage    : {used:.1f}/{cap:.0f} t"

        lines = [
            f"|wMining Site: {self.key}|n",
            f"  Owner      : {owner_str}",
            f"  Survey     : {survey_label}",
            f"  License    : {license_str}",
            f"  Tax rate   : {tax_str}",
            f"  Hazard     : {hazard_str}",
            f"  Claimed    : {'yes' if self.db.is_claimed else 'no'}",
            f"  Rigs ({len(rigs)}):",
            rig_block,
            f"  Storage    : {storage_str}{storage_cap_str}",
            f"  Active     : {active_flag}",
            f"  Richness   : {richness}  (depletes {dep_rate}/cycle)",
            f"  Output     : {base_tons} t/cycle (base)",
            f"  Composition:",
            comp_str,
            f"  Next cycle : {next_cycle}",
        ]
        log = self.db.cycle_log or []
        if log:
            lines.append("  Recent output:")
            for entry in log[-3:]:
                lines.append(f"    {entry}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Cycle scheduling
    # ------------------------------------------------------------------

    def schedule_next_cycle(self, completed_boundary=None):
        """
        Set next_cycle_at on the global UTC 3h grid (MINING_DELIVERY_PERIOD).

        Args:
            completed_boundary: Grid instant for the cycle just processed; next is +period.
            If None: earliest grid instant >= now (deploy, storage full skip, engine init).
        """
        if completed_boundary is not None:
            nxt = next_period_after_completed(
                completed_boundary, MINING_DELIVERY_PERIOD
            )
            self.db.next_cycle_at = to_iso(nxt)
        else:
            self.db.next_cycle_at = to_iso(
                ceil_period(utc_now(), MINING_DELIVERY_PERIOD)
            )

    def _append_log(self, entry):
        log = self.db.cycle_log or []
        log.append(entry)
        self.db.cycle_log = log[-20:]

    # ------------------------------------------------------------------
    # Production (Pass 2)
    # ------------------------------------------------------------------

    def process_cycle(self):
        """
        Run one production cycle and deposit output into linked storage.

        Formula:
            total_tons = base_output_tons * richness * rig_rating
                         * mode_output_mod * power_output_mod
                         * (1 - wear * WEAR_OUTPUT_PENALTY)

        The best available rig (lowest wear among operational rigs) is used.
        Raises RuntimeError if called when no operational rigs exist — the
        engine guards against this via is_active; the error surfaces bugs.

        Sites owned by an NPC character (``owner.db.is_npc``) or with
        ``owner.db.mining_owner_uses_npc_production`` do not accumulate wear,
        cannot break down, and ignore stored wear for output calculation.
        """
        from typeclasses.system_alerts import enqueue_system_alert

        operational_rigs = [r for r in (self.db.rigs or []) if r and r.db.is_operational]
        if not operational_rigs:
            raise RuntimeError(
                f"[mining] {self.key}: process_cycle called with no operational rigs"
            )
        rig = min(operational_rigs, key=lambda r: r.db.wear)

        due_raw = _parse_ts(self.db.next_cycle_at)
        due_boundary = (
            floor_period(due_raw, MINING_DELIVERY_PERIOD) if due_raw else None
        )

        storage = self.db.linked_storage
        deposit = self.db.deposit

        _owner = self.db.owner
        npc_owned = mining_owner_skips_wear_and_breakdown(_owner)

        # -- Storage capacity check --
        capacity = float(storage.db.capacity_tons)
        if storage.total_mass() >= capacity:
            msg = "Storage full — cycle skipped. Collect ore to resume production."
            self._append_log(f"[{_fmt_ts(_now())[:16].replace('T', ' ')}] {msg}")
            enqueue_system_alert(
                severity="warning",
                category="mining",
                title="Mine storage full",
                detail=f"{self.key} is at capacity; production skipped.",
                source=self.key,
                dedupe_key=f"storage-full:{self.id}",
            )
            self.schedule_next_cycle()
            return msg

        # -- Rig settings --
        richness = float(deposit["richness"])
        base_tons = float(deposit["base_output_tons"])
        rig_rating = float(rig.db.rig_rating or 0)
        target_family = rig.db.target_family
        if target_family not in FAMILY_CATEGORIES:
            target_family = "mixed"
        purity_cutoff = rig.db.purity_cutoff
        if purity_cutoff not in PURITY_THRESHOLDS:
            purity_cutoff = "medium"
        maintenance = rig.db.maintenance_level
        wear = float(rig.db.wear or 0)

        mode_out, power_out = rig_output_modifiers(rig)
        wear_out = (
            1.0 if npc_owned else (1.0 - (wear * WEAR_OUTPUT_PENALTY))
        )

        point_mult = 1.0
        if _owner and _owner.is_typeclass("typeclasses.characters.Character", exact=False):
            from world.point_store.perk_resolver import mining_output_multiplier

            point_mult = mining_output_multiplier(_owner)

        total_tons = (
            base_tons * richness * rig_rating * mode_out * power_out * wear_out * point_mult
        )

        # -- Composition filtering (target_family + purity_cutoff) --
        composition = deposit["composition"]
        allowed_cats = FAMILY_CATEGORIES[target_family]
        min_price = PURITY_THRESHOLDS[purity_cutoff]

        eligible = {}
        for key, frac in composition.items():
            info = RESOURCE_CATALOG.get(key, {})
            if info.get("category") not in allowed_cats:
                continue
            if info.get("base_price_cr_per_ton", 0) < min_price:
                continue
            eligible[key] = float(frac)

        total_frac = sum(eligible.values()) or 1.0
        output = {}
        for key, frac in eligible.items():
            tons = round(total_tons * (frac / total_frac), 2)
            if tons > 0:
                output[key] = tons

        # -- Hazard events — before deposit so stored amounts match log --
        hazard_note = ""
        hazard_level = float(self.db.hazard_level)
        if hazard_level > 0 and random.random() < hazard_level * HAZARD_CHANCE_BASE:
            hazard_type = random.choice(["raid", "geological"])
            hazard_log = self.db.hazard_log

            if hazard_type == "raid":
                raid_frac = HAZARD_RAID_STEAL_FRAC
                if (
                    _owner
                    and _owner.is_typeclass("typeclasses.characters.Character", exact=False)
                ):
                    from world.point_store.perk_resolver import hazard_raid_steal_multiplier

                    raid_frac = max(
                        0.0,
                        min(1.0, HAZARD_RAID_STEAL_FRAC * hazard_raid_steal_multiplier(_owner)),
                    )
                inv = storage.db.inventory
                stolen = {}
                for k, v in inv.items():
                    amount = round(float(v) * raid_frac, 2)
                    if amount > 0:
                        stolen[k] = amount
                        inv[k] = round(float(v) - amount, 2)
                storage.db.inventory = {k: v for k, v in inv.items() if v > 0}
                parts_stolen = [
                    f"{RESOURCE_CATALOG.get(k, {}).get('name', k)}: {v}t"
                    for k, v in stolen.items()
                ]
                hazard_note = f" |r[RAID — stolen: {', '.join(parts_stolen) or 'nothing'}]|n"
                hazard_log.append(f"[{_fmt_ts(_now())[:16].replace('T', ' ')}] Raid: {parts_stolen}")

            elif hazard_type == "geological":
                if (
                    _owner
                    and _owner.is_typeclass("typeclasses.characters.Character", exact=False)
                ):
                    from world.point_store.perk_resolver import hazard_geo_floor_params

                    gmin, gmax = hazard_geo_floor_params(
                        _owner, HAZARD_GEO_OUTPUT_MIN, HAZARD_GEO_OUTPUT_MAX
                    )
                    geo_mod = random.uniform(gmin, gmax)
                else:
                    geo_mod = random.uniform(HAZARD_GEO_OUTPUT_MIN, HAZARD_GEO_OUTPUT_MAX)
                output = {k: round(v * geo_mod, 2) for k, v in output.items() if round(v * geo_mod, 2) > 0}
                geo_pct = int(geo_mod * 100)
                hazard_note = f" |y[GEOLOGICAL EVENT — output reduced to {geo_pct}%]|n"
                hazard_log.append(
                    f"[{_fmt_ts(_now())[:16].replace('T', ' ')}] "
                    f"Geological event: output at {geo_pct}%"
                )

            self.db.hazard_log = hazard_log[-10:]

        # -- Deposit to storage (respect capacity) --
        remaining_space = max(0.0, capacity - storage.total_mass())
        if remaining_space < sum(output.values()):
            scale = remaining_space / max(sum(output.values()), 0.001)
            output = {k: round(v * scale, 2) for k, v in output.items() if round(v * scale, 2) > 0}

        inventory = storage.db.inventory
        for key, tons in output.items():
            inventory[key] = round(float(inventory.get(key, 0.0)) + tons, 2)
        storage.db.inventory = inventory

        # -- Depletion --
        dep_rate = float(deposit["depletion_rate"])
        dep_floor = float(deposit["richness_floor"])
        dep_mult = 1.0
        if _owner and _owner.is_typeclass("typeclasses.characters.Character", exact=False):
            from world.point_store.perk_resolver import mining_depletion_multiplier

            dep_mult = mining_depletion_multiplier(_owner)
        new_richness = max(dep_floor, richness - dep_rate * dep_mult)
        deposit["richness"] = round(new_richness, 4)
        self.db.deposit = deposit

        # -- Wear accumulation & breakdown (skipped for NPC-owned sites) --
        broke_down = False
        if not npc_owned:
            wear_mode, wear_power = rig_normalized_mode_power(rig)
            mode_wear = MODE_WEAR_MODIFIERS[wear_mode]
            power_wear = POWER_WEAR_MODIFIERS[wear_power]
            maint_key = maintenance if maintenance in MAINTENANCE_WEAR_MODIFIERS else "standard"
            maint_wear = MAINTENANCE_WEAR_MODIFIERS[maint_key]
            wg = 1.0
            if _owner and _owner.is_typeclass("typeclasses.characters.Character", exact=False):
                from world.point_store.perk_resolver import rig_wear_gain_multiplier

                wg = rig_wear_gain_multiplier(_owner)
            new_wear = min(
                1.0,
                wear + WEAR_PER_CYCLE_BASE * mode_wear * power_wear * maint_wear * wg,
            )

            breakdown_base = BREAKDOWN_BASE[maint_key]
            breakdown_chance = breakdown_base * (1.0 + wear * 2.0)
            broke_down = random.random() < breakdown_chance or new_wear >= 1.0

            rig.db.wear = round(new_wear, 4)
            if broke_down:
                rig.db.is_operational = False
                rig.db.wear = 1.0
                enqueue_system_alert(
                    severity="critical",
                    category="mining",
                    title="Mining rig breakdown",
                    detail=f"{rig.key} at {self.key} requires repair.",
                    source=self.key,
                    dedupe_key=f"rig-breakdown:{self.id}:{rig.id}",
                )

        # -- Extraction tax --
        tax_note = ""
        tax_rate = float(self.db.tax_rate)
        if tax_rate > 0 and output:
            output_value = sum(
                int(float(tons) * RESOURCE_CATALOG.get(k, {}).get("base_price_cr_per_ton", 0))
                for k, tons in output.items()
            )
            eff_rate = tax_rate
            if _owner and _owner.is_typeclass("typeclasses.characters.Character", exact=False):
                from world.point_store.perk_resolver import (
                    clamped_fee_rate,
                    extraction_tax_multiplier,
                )

                eff_rate = clamped_fee_rate(tax_rate, extraction_tax_multiplier(_owner))
            tax_amount = int(output_value * eff_rate)
            if tax_amount > 0:
                owner = self.db.owner
                from .economy import get_economy
                econ = get_economy(create_missing=False)
                if econ and owner:
                    player_acct = econ.get_character_account(owner)
                    treasury_acct = econ.get_treasury_account("alpha-prime")
                    econ.ensure_account(
                        player_acct,
                        opening_balance=int(owner.db.credits),
                    )
                    econ.ensure_account(treasury_acct)
                    bal = econ.get_balance(player_acct)
                    if bal >= tax_amount:
                        econ.transfer(
                            player_acct,
                            treasury_acct,
                            tax_amount,
                            memo=f"Extraction tax: {self.key}",
                        )
                        owner.db.credits = econ.get_balance(player_acct)
                        tax_note = f" [tax: {tax_amount:,} cr]"
                    else:
                        tax_note = " [tax due but insufficient balance]"

        # -- Summary --
        ts = _fmt_ts(_now())
        parts = [
            f"{RESOURCE_CATALOG[k]['name']}: {v}t"
            for k, v in output.items()
        ]
        breakdown_note = "  |r[RIG BREAKDOWN — repair required]|n" if broke_down else ""
        plain_summary = (
            f"[{ts[:16].replace('T', ' ')}] "
            f"{', '.join(parts) or 'no output'}"
            f"{' [BREAKDOWN]' if broke_down else ''}"
            f"{tax_note if tax_note else ''}"
        )
        self._append_log(plain_summary)
        self.db.last_processed_at = ts
        if due_boundary is not None:
            self.schedule_next_cycle(completed_boundary=due_boundary)
        else:
            self.schedule_next_cycle()

        if output:
            self.db.last_ore_deposit_at = to_iso(utc_now())
            from typeclasses.haulers import arm_hauler_pickup_after_mining_deposit

            arm_hauler_pickup_after_mining_deposit(self)

        full_summary = plain_summary + hazard_note + breakdown_note
        return full_summary


# ---------------------------------------------------------------------------
# MiningRig
# ---------------------------------------------------------------------------

class MiningRig(ObjectParent, DefaultObject):
    """
    An extracting unit deployable at a MiningSite.

    Pass-2 db additions
    -------------------
    db.wear             float  0.0 (new) to 1.0 (broken); accumulates each cycle
    db.mode             str    "balanced" | "selective" | "overdrive"
    db.power_level      str    "low" | "normal" | "high"
    db.target_family    str    "metals" | "gems" | "mixed"
    db.purity_cutoff    str    "low" | "medium" | "high"
    db.maintenance_level str   "low" | "standard" | "premium"
    """

    # Valid option sets for validation
    VALID_MODES = ("balanced", "selective", "overdrive")
    VALID_POWER = ("low", "normal", "high")
    VALID_FAMILY = ("metals", "gems", "mixed")
    VALID_PURITY = ("low", "medium", "high")
    VALID_MAINT = ("low", "standard", "premium")

    def at_object_creation(self):
        self.db.is_mining_rig = True
        self.db.owner = None
        self.db.site = None
        self.db.rig_rating = 1.0
        self.db.is_installed = False
        self.db.is_operational = False
        # Pass 2
        self.db.wear = 0.0
        self.db.mode = "balanced"
        self.db.power_level = "normal"
        self.db.target_family = "mixed"
        self.db.purity_cutoff = "low"
        self.db.maintenance_level = "standard"
        self.tags.add("mining_rig", category="mining")

    # ------------------------------------------------------------------

    def install(self, site, owner=None):
        self.db.site = site
        self.db.is_installed = True
        self.db.is_operational = True
        if owner:
            self.db.owner = owner
        rigs = list(site.db.rigs or [])
        if self not in rigs:
            rigs.append(self)
        site.db.rigs = rigs

    def uninstall(self):
        site = self.db.site
        if site:
            rigs = list(site.db.rigs or [])
            if self in rigs:
                rigs.remove(self)
            site.db.rigs = rigs
        self.db.site = None
        self.db.is_installed = False
        self.db.is_operational = False

    def repair(self):
        """Reset wear to 0 and restore operational status."""
        self.db.wear = 0.0
        self.db.is_operational = True

    def set_option(self, field, value):
        """
        Set a tunable option.  Returns (success, message).
        field: one of mode, power_level, target_family, purity_cutoff, maintenance_level
        """
        valid_map = {
            "mode": self.VALID_MODES,
            "power_level": self.VALID_POWER,
            "target_family": self.VALID_FAMILY,
            "purity_cutoff": self.VALID_PURITY,
            "maintenance_level": self.VALID_MAINT,
        }
        if field not in valid_map:
            return False, (
                f"Unknown field '{field}'. Valid fields: "
                + ", ".join(valid_map)
            )
        if value not in valid_map[field]:
            return False, (
                f"Invalid value '{value}' for {field}. "
                f"Options: {', '.join(valid_map[field])}"
            )
        setattr(self.db, field, value)
        return True, f"{field} set to '{value}'."

    def get_status_report(self):
        owner_str = self.db.owner.key if self.db.owner else "unassigned"
        site_str = self.db.site.key if self.db.site else "none"
        wear = float(getattr(self.db, "wear", 0.0) or 0.0)
        wear_pct = int(wear * 100)
        op_flag = "|gyes|n" if self.db.is_operational else "|rno|n"
        wear_color = "|g" if wear_pct < 40 else "|y" if wear_pct < 75 else "|r"
        lines = [
            f"|wMining Rig: {self.key}|n",
            f"  Owner         : {owner_str}",
            f"  Installed at  : {site_str}",
            f"  Rating        : {self.db.rig_rating}",
            f"  Operational   : {op_flag}",
            f"  Wear          : {wear_color}{wear_pct}%|n",
            f"  Mode          : {getattr(self.db, 'mode', 'balanced')}",
            f"  Power         : {getattr(self.db, 'power_level', 'normal')}",
            f"  Target family : {getattr(self.db, 'target_family', 'mixed')}",
            f"  Purity cutoff : {getattr(self.db, 'purity_cutoff', 'low')}",
            f"  Maintenance   : {getattr(self.db, 'maintenance_level', 'standard')}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# MiningStorage
# ---------------------------------------------------------------------------

class MiningStorage(ObjectParent, DefaultObject):
    """
    Aggregate ore storage container linked to a MiningSite.

    Pass-2 db addition
    ------------------
    db.capacity_tons  float  hard cap on total stored mass (default 500 t)
    """

    def at_object_creation(self):
        self.db.is_mining_storage = True
        self.db.owner = None
        self.db.site = None
        self.db.inventory = {}
        self.db.capacity_tons = 500.0
        self.tags.add("mining_storage", category="mining")
        self.locks.add("get:false()")

    # ------------------------------------------------------------------

    def total_mass(self):
        return round(sum(float(v) for v in (self.db.inventory or {}).values()), 2)

    def is_full(self):
        cap = float(getattr(self.db, "capacity_tons", 500.0) or 500.0)
        return self.total_mass() >= cap

    def get_inventory_report(self):
        inventory = self.db.inventory or {}
        cap = float(getattr(self.db, "capacity_tons", 500.0) or 500.0)
        used = self.total_mass()
        cap_pct = int(used / cap * 100) if cap else 0

        if not inventory:
            return f"|w{self.key}|n — storage is empty.  [{used:.1f}/{cap:.0f} t]"

        cap_color = "|g" if cap_pct < 70 else "|y" if cap_pct < 90 else "|r"
        lines = [
            f"|w{self.key} — Stored Resources|n  "
            f"[{cap_color}{used:.1f}/{cap:.0f} t  {cap_pct}%|n]"
        ]
        total_value = 0
        for key in sorted(inventory):
            tons = float(inventory[key])
            info = RESOURCE_CATALOG.get(key, {})
            name = info.get("name", key)
            price = info.get("base_price_cr_per_ton", 0)
            value = int(tons * price)
            total_value += value
            lines.append(f"  {name:<28} {tons:>8.2f}t   |y{value:>10,}|n cr")
        lines.append(f"  {'Total base value':<28} {'':>8}    |y{total_value:>10,}|n cr")
        return "\n".join(lines)

    def withdraw_all(self):
        contents = dict(self.db.inventory or {})
        self.db.inventory = {}
        return contents

    def withdraw(self, resource_key, tons):
        inventory = self.db.inventory or {}
        available = float(inventory.get(resource_key, 0.0))
        removed = min(available, float(tons))
        remaining = round(available - removed, 2)
        if remaining <= 0.0:
            inventory.pop(resource_key, None)
        else:
            inventory[resource_key] = remaining
        self.db.inventory = inventory
        return round(removed, 2)


# ---------------------------------------------------------------------------
# MiningEngine
# ---------------------------------------------------------------------------

class MiningEngine(Script):
    """
    Global persistent script that drives mining production cycles.

    Wakes every 30 minutes (interval = 1800 s), scans all MiningSite objects
    via tag search, and processes any active site whose next_cycle_at has passed.
    Delivery times use the shared UTC grid (world.time.MINING_DELIVERY_PERIOD).
    Catch-up is capped at MAX_CATCHUP_CYCLES per wakeup.

    Execution is staggered by MINING_ENGINE_STAGGER_MOD (logical due times unchanged).

    Online owners receive an in-game notification on each cycle, including
    breakdown warnings from Pass 2.
    """

    def at_script_creation(self):
        self.key = "mining_engine"
        self.desc = "Drives global UTC mining delivery cycles (world.time grid)."
        self.persistent = True
        self.interval = 60
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self, **kwargs):
        now = _now()
        self.ndb.stagger_tick = (self.ndb.stagger_tick or 0) + 1
        tick = self.ndb.stagger_tick
        sites = search_tag("mining_site", category="mining")
        processed = 0
        errors = 0

        for site in sites:
            try:
                if not getattr(site.db, "is_mining_site", False):
                    continue

                next_cycle = _parse_ts(site.db.next_cycle_at)

                if not site.is_active:
                    # Advance an overdue timestamp even when inactive so the
                    # frontend does not show a permanently stuck "now".
                    # Use the missed boundary as the completed_boundary so the
                    # clock steps forward by exactly one period on the grid
                    # (avoids ceil_period edge case when now == boundary).
                    if next_cycle is not None and next_cycle <= now:
                        site_rigs = site.db.rigs or []
                        operational = [r for r in site_rigs if r and r.db.is_operational]
                        if not site_rigs:
                            reason = "no rigs installed"
                        elif not operational:
                            broken = [r.key for r in site_rigs if r]
                            reason = f"all rigs broken ({', '.join(broken)})"
                        elif not site.db.linked_storage:
                            reason = "no linked storage"
                        else:
                            reason = "unknown"
                        logger.log_info(
                            f"[mining_engine] {site.key}: cycle due but site inactive "
                            f"({reason}) — advancing clock without production."
                        )
                        site.schedule_next_cycle(
                            completed_boundary=floor_period(next_cycle, MINING_DELIVERY_PERIOD)
                        )
                    continue
                if next_cycle is None:
                    site.schedule_next_cycle()
                    continue

                sid = int(site.id) if site.id is not None else 0
                stagger_ok = sid % MINING_ENGINE_STAGGER_MOD == tick % MINING_ENGINE_STAGGER_MOD
                # Due/overdue sites run every tick; stagger only spreads future-due checks.
                if not stagger_ok and next_cycle > now:
                    continue

                catchup = 0
                while next_cycle <= now and catchup < MAX_CATCHUP_CYCLES:
                    summary = site.process_cycle()
                    logger.log_info(f"[mining_engine] {site.key}: {summary}")

                    owner = site.db.owner
                    if owner and hasattr(owner, "sessions") and owner.sessions.count():
                        owner.msg(f"|w[Mine: {site.key}]|n {summary}")

                    next_cycle = _parse_ts(site.db.next_cycle_at)
                    catchup += 1
                    processed += 1
                    if next_cycle is None:
                        break

            except Exception as err:
                errors += 1
                logger.log_err(
                    f"[mining_engine] Error on site {getattr(site, 'key', '?')}: {err}"
                )

        if processed or errors:
            logger.log_info(
                f"[mining_engine] Tick complete — {processed} cycle(s), {errors} error(s)."
            )


# ---------------------------------------------------------------------------
# Rig repair (credits + ledger, parallel to shop sales tax split)
# ---------------------------------------------------------------------------


def rig_needs_service(rig):
    """True if wear > 0 or rig is not operational."""
    if not rig:
        return False
    wear = float(getattr(rig.db, "wear", 0) or 0)
    if wear > 0:
        return True
    return not bool(getattr(rig.db, "is_operational", True))


def compute_rig_repair_charge(rig):
    """Total credits charged for one repair (before tax split)."""
    wear_pct = int(round(float(getattr(rig.db, "wear", 0) or 0) * 100))
    rating = float(getattr(rig.db, "rig_rating", 1.0) or 1.0)
    total = (
        RIG_REPAIR_BASE_CR
        + int(rating * RIG_REPAIR_PER_RATING_CR)
        + wear_pct * RIG_REPAIR_WEAR_UNIT_CR
    )
    return max(RIG_REPAIR_MIN_TOTAL_CR, int(total))


def split_rig_repair_revenue(total_cr):
    """Return (vendor_credits, tax_credits) for a total repair bill (same rounding as shops)."""
    total_cr = int(total_cr)
    tax = int(round(total_cr * RIG_REPAIR_TAX_RATE))
    vendor = total_cr - tax
    return vendor, tax


def get_rig_for_repair(site, name_fragment=None):
    """
    Pick which rig to repair (same rules as CmdRepairRig).

    Returns:
        (rig, None) on success, or (None, error_message) with a player-facing string (no color codes).
    """
    installed = [r for r in (site.db.rigs or []) if r]
    if not installed:
        return None, f"{site.key} has no installed rigs to repair."

    if name_fragment:
        nf = str(name_fragment).strip().lower()
        matches = [r for r in installed if nf in r.key.lower()]
        if not matches:
            return None, f"No installed rig matching '{name_fragment}' at {site.key}."
        return matches[0], None

    if len(installed) == 1:
        return installed[0], None

    broken = [r for r in installed if not r.db.is_operational]
    if broken:
        return broken[0], None
    return max(installed, key=lambda r: float(getattr(r.db, "wear", 0) or 0)), None


def pay_rig_repair(owner, rig, site=None):
    """
    Charge ``owner`` for one rig service: split vendor / treasury, then ``rig.repair()``.

    Args:
        owner: Character paying (must own ``site`` when ``site`` is used for rescheduling).
        rig: MiningRig instance.
        site: Optional MiningSite for rescheduling production after a breakdown fix.

    Returns:
        (ok, message, info) where ``info`` is a dict with totals on success, else None.
    """
    from typeclasses.economy import get_economy

    if not rig_needs_service(rig):
        return False, "That rig does not need repair.", None

    total = compute_rig_repair_charge(rig)
    if owner and owner.is_typeclass("typeclasses.characters.Character", exact=False):
        from world.point_store.perk_resolver import rig_repair_cost_multiplier

        total = max(
            RIG_REPAIR_MIN_TOTAL_CR,
            int(round(total * rig_repair_cost_multiplier(owner))),
        )
    vendor_amt, tax_amt = split_rig_repair_revenue(total)

    econ = get_economy(create_missing=True)
    player_acct = econ.get_character_account(owner)
    vendor_acct = econ.get_vendor_account(RIG_REPAIR_VENDOR_ID)
    treasury_acct = econ.get_treasury_account("alpha-prime")

    econ.ensure_account(player_acct, opening_balance=int(owner.db.credits or 0))
    econ.ensure_account(vendor_acct, opening_balance=0)
    econ.ensure_account(treasury_acct, opening_balance=int(econ.db.tax_pool or 0))

    balance = econ.get_balance(player_acct)
    if balance < total:
        return (
            False,
            f"Repair costs {total:,} cr. You have {balance:,} cr.",
            None,
        )

    was_broken = not bool(getattr(rig.db, "is_operational", True))
    old_wear_pct = int(round(float(getattr(rig.db, "wear", 0) or 0) * 100))

    wmemo = f"Rig repair: {rig.key}"
    econ.withdraw(player_acct, total, memo=wmemo)
    econ.deposit(vendor_acct, vendor_amt, memo=f"Rig repair service: {rig.key}")
    if tax_amt > 0:
        econ.deposit(treasury_acct, tax_amt, memo=f"Rig repair tax (3%): {rig.key}")

    econ.record_transaction(
        tx_type="rig_repair",
        amount=total,
        from_account=player_acct,
        to_account=vendor_acct,
        memo=f"{owner.key} rig repair {rig.key}",
        extra={
            "tax_amount": tax_amt,
            "treasury_account": treasury_acct,
            "vendor_account": vendor_acct,
            "rig_id": getattr(rig, "id", None),
        },
    )

    owner.db.credits = econ.get_balance(player_acct)
    econ.db.tax_pool = econ.get_balance(treasury_acct)

    rig.repair()

    if was_broken and site is not None:
        if site.db.linked_storage and not site.db.next_cycle_at:
            site.schedule_next_cycle()

    return True, "", {
        "total": total,
        "vendor_amount": vendor_amt,
        "tax_amount": tax_amt,
        "was_broken": was_broken,
        "old_wear_pct": old_wear_pct,
    }
