"""
Flora harvest pipeline — UTC hourly production grid (world.time.FLORA_DELIVERY_PERIOD).

Mirrors mining structure for scheduling and hauler integration: FloraSite, FloraHarvester,
FloraStorage, FloraEngine. Pickup offset is FLORA_HAULER_PICKUP_OFFSET_SEC (15 min), not
half of the flora period.
"""

from evennia import search_tag
from evennia.objects.objects import DefaultObject
from evennia.utils import logger

from world.time import (
    FLORA_DELIVERY_PERIOD,
    ceil_period,
    floor_period,
    next_period_after_completed,
    parse_iso,
    to_iso,
    utc_now,
)

from .objects import ObjectParent
from .scripts import Script


MAX_CATCHUP_CYCLES = 10
FLORA_ENGINE_STAGGER_MOD = 4

# Raw flora keys (ton-priced like mining RESOURCE_CATALOG). Used for harvest output and
# Marcus Killstar full-catalog composition (even spread across all keys).
FLORA_RESOURCE_CATALOG = {
    "wild_harvest_biomass": {
        "name": "Wild Harvest Biomass",
        "category": "flora_raw",
        "rarity": "common",
        "base_price_cr_per_ton": 50,
        "desc": "Unprocessed botanical harvest suitable for processing.",
    },
    "structural_cane": {
        "name": "Structural Cane",
        "category": "flora_structural",
        "rarity": "common",
        "base_price_cr_per_ton": 65,
        "desc": "Dense fibre cane for composites and framing.",
    },
    "cellulose_pulp_bale": {
        "name": "Cellulose Pulp Bale",
        "category": "flora_structural",
        "rarity": "common",
        "base_price_cr_per_ton": 70,
        "desc": "Bleached pulp stock for paper and bioplastics.",
    },
    "algal_mat": {
        "name": "Algal Mat",
        "category": "flora_raw",
        "rarity": "common",
        "base_price_cr_per_ton": 85,
        "desc": "Tank-cultured algae mass for feed and chemistry.",
    },
    "lichen_aggregate": {
        "name": "Lichen Aggregate",
        "category": "flora_raw",
        "rarity": "common",
        "base_price_cr_per_ton": 95,
        "desc": "Symbiotic lichen sheets for slow-release compounds.",
    },
    "medicinal_sap": {
        "name": "Medicinal Sap",
        "category": "flora_medicinal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 420,
        "desc": "Sterile sap fraction for pharma precursors.",
    },
    "volatile_terpene_resin": {
        "name": "Volatile Terpene Resin",
        "category": "flora_medicinal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 580,
        "desc": "High-note terpene resin for solvents and scents.",
    },
    "spore_culture_mass": {
        "name": "Spore Culture Mass",
        "category": "flora_exotic",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 640,
        "desc": "Controlled spore biomass for enzymes and inoculants.",
    },
    "xenohybrid_foliage": {
        "name": "Xenohybrid Foliage",
        "category": "flora_exotic",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 720,
        "desc": "Lab-cross foliage with nonstandard metabolites.",
    },
    "crystalline_nectar_concentrate": {
        "name": "Crystalline Nectar Concentrate",
        "category": "flora_exotic",
        "rarity": "rare",
        "base_price_cr_per_ton": 2100,
        "desc": "Ultra-refined floral nectar solids.",
    },
    "deep_root_tuber": {
        "name": "Deep Root Tuber",
        "category": "flora_raw",
        "rarity": "common",
        "base_price_cr_per_ton": 110,
        "desc": "Starch-dense tubers from deep aquifer-fed stands.",
    },
    "pollen_aggregate": {
        "name": "Pollen Aggregate",
        "category": "flora_medicinal",
        "rarity": "uncommon",
        "base_price_cr_per_ton": 510,
        "desc": "Filtered pollen protein for allergen and nutrient lines.",
    },
    "vascular_sheath_fibre": {
        "name": "Vascular Sheath Fibre",
        "category": "flora_structural",
        "rarity": "common",
        "base_price_cr_per_ton": 120,
        "desc": "Long-chain vascular bundles for tensile textiles.",
    },
    "bioluminescent_moss": {
        "name": "Bioluminescent Moss",
        "category": "flora_exotic",
        "rarity": "rare",
        "base_price_cr_per_ton": 2800,
        "desc": "Living moss culture retaining luciferase pathways.",
    },
    "heritage_seed_pod_lot": {
        "name": "Heritage Seed Pod Lot",
        "category": "flora_exotic",
        "rarity": "rare",
        "base_price_cr_per_ton": 3400,
        "desc": "Certified heritage genotype pods for vault and breeding.",
    },
}


def _now():
    return utc_now()


def _parse_ts(ts_str):
    return parse_iso(ts_str)


def _fmt_ts(dt):
    return to_iso(dt)


class FloraSite(ObjectParent, DefaultObject):
    """Claimable flora stand; hourly UTC cycle grid and last_flora_deposit_at for haulers."""

    def at_object_creation(self):
        self.db.is_flora_site = True
        self.db.is_claimed = False
        self.db.owner = None
        self.db.rigs = []
        self.db.linked_storage = None
        self.db.next_cycle_at = None
        self.db.last_flora_deposit_at = None
        self.db.last_processed_at = None
        self.db.cycle_log = []
        self.db.deposit = {
            "richness": 1.0,
            "base_output_tons": 10.0,
            "composition": {"wild_harvest_biomass": 1.0},
            "depletion_rate": 0.002,
            "richness_floor": 0.10,
        }
        self.tags.add("flora_site", category="flora")
        self.db.allowed_purposes = ["flora"]
        self.locks.add("get:false()")

    def at_init(self):
        super().at_init()
        if self.db.rigs is None:
            self.db.rigs = []
        if self.db.cycle_log is None:
            self.db.cycle_log = []
        if self.db.deposit is None:
            self.db.deposit = {
                "richness": 1.0,
                "base_output_tons": 10.0,
                "composition": {"wild_harvest_biomass": 1.0},
                "depletion_rate": 0.002,
                "richness_floor": 0.10,
            }

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

    def schedule_next_cycle(self, completed_boundary=None):
        if completed_boundary is not None:
            nxt = next_period_after_completed(completed_boundary, FLORA_DELIVERY_PERIOD)
            self.db.next_cycle_at = to_iso(nxt)
        else:
            self.db.next_cycle_at = to_iso(ceil_period(utc_now(), FLORA_DELIVERY_PERIOD))

    def _append_log(self, entry):
        log = self.db.cycle_log or []
        log.append(entry)
        self.db.cycle_log = log[-20:]

    def process_cycle(self):
        """One harvest cycle into linked_storage; arms flora haulers via last_flora_deposit_at."""
        from typeclasses.system_alerts import enqueue_system_alert

        operational_rigs = [r for r in (self.db.rigs or []) if r and r.db.is_operational]
        if not operational_rigs:
            raise RuntimeError(
                f"[flora] {self.key}: process_cycle called with no operational harvesters"
            )
        rig = min(operational_rigs, key=lambda r: float(getattr(r.db, "wear", 0) or 0))

        due_raw = _parse_ts(self.db.next_cycle_at)
        due_boundary = (
            floor_period(due_raw, FLORA_DELIVERY_PERIOD) if due_raw else None
        )

        storage = self.db.linked_storage
        deposit = self.db.deposit

        capacity = float(storage.db.capacity_tons)
        if storage.total_mass() >= capacity:
            msg = "Storage full — cycle skipped. Collect harvest to resume production."
            self._append_log(f"[{_fmt_ts(_now())[:16].replace('T', ' ')}] {msg}")
            enqueue_system_alert(
                severity="warning",
                category="flora",
                title="Flora storage full",
                detail=f"{self.key} is at capacity; production skipped.",
                source=self.key,
                dedupe_key=f"flora-storage-full:{self.id}",
            )
            self.schedule_next_cycle()
            return msg

        richness = float(deposit["richness"])
        base_tons = float(deposit["base_output_tons"])
        rig_rating = float(rig.db.rig_rating)
        total_tons = base_tons * richness * rig_rating

        composition = deposit.get("composition") or {}
        output = {}
        total_frac = sum(float(f) for f in composition.values()) or 1.0
        for key, frac in composition.items():
            if key not in FLORA_RESOURCE_CATALOG:
                continue
            tons = round(total_tons * (float(frac) / total_frac), 2)
            if tons > 0:
                output[key] = tons

        remaining_space = max(0.0, capacity - storage.total_mass())
        if remaining_space < sum(output.values()):
            scale = remaining_space / max(sum(output.values()), 0.001)
            output = {
                k: round(v * scale, 2)
                for k, v in output.items()
                if round(v * scale, 2) > 0
            }

        inventory = storage.db.inventory or {}
        for key, tons in output.items():
            inventory[key] = round(float(inventory.get(key, 0.0)) + tons, 2)
        storage.db.inventory = inventory

        dep_rate = float(deposit.get("depletion_rate", 0.002))
        dep_floor = float(deposit.get("richness_floor", 0.10))
        new_richness = max(dep_floor, richness - dep_rate)
        deposit["richness"] = round(new_richness, 4)
        self.db.deposit = deposit

        ts = _fmt_ts(_now())
        parts = [f"{FLORA_RESOURCE_CATALOG[k]['name']}: {v}t" for k, v in output.items()]
        plain_summary = f"[{ts[:16].replace('T', ' ')}] {', '.join(parts) or 'no output'}"
        self._append_log(plain_summary)
        self.db.last_processed_at = ts
        if due_boundary is not None:
            self.schedule_next_cycle(completed_boundary=due_boundary)
        else:
            self.schedule_next_cycle()

        if output:
            self.db.last_flora_deposit_at = to_iso(utc_now())
            from typeclasses.haulers import arm_hauler_pickup_after_flora_deposit

            arm_hauler_pickup_after_flora_deposit(self)

        return plain_summary


class FloraHarvester(ObjectParent, DefaultObject):
    """Harvesting unit installed at a FloraSite."""

    def at_object_creation(self):
        self.db.is_flora_harvester = True
        self.db.owner = None
        self.db.site = None
        self.db.rig_rating = 1.0
        self.db.is_installed = False
        self.db.is_operational = False
        self.db.wear = 0.0
        self.tags.add("flora_harvester", category="flora")

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


class FloraStorage(ObjectParent, DefaultObject):
    """Aggregate harvest storage linked to a FloraSite."""

    def at_object_creation(self):
        self.db.is_flora_storage = True
        self.db.owner = None
        self.db.site = None
        self.db.inventory = {}
        self.db.capacity_tons = 500.0
        self.tags.add("flora_storage", category="flora")
        self.locks.add("get:false()")

    def total_mass(self):
        return round(sum(float(v) for v in (self.db.inventory or {}).values()), 2)

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


class FloraEngine(Script):
    """
    Global script: flora production on FLORA_DELIVERY_PERIOD UTC grid.
    Interval 60s with stagger (same pattern as MiningEngine).
    """

    def at_script_creation(self):
        self.key = "flora_engine"
        self.desc = "Drives global UTC flora harvest cycles (world.time.FLORA_DELIVERY_PERIOD)."
        self.persistent = True
        self.interval = 60
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self, **kwargs):
        now = _now()
        self.ndb.stagger_tick = (self.ndb.stagger_tick or 0) + 1
        tick = self.ndb.stagger_tick
        sites = search_tag("flora_site", category="flora")
        processed = 0
        errors = 0

        for site in sites:
            try:
                if not getattr(site.db, "is_flora_site", False):
                    continue

                next_cycle = _parse_ts(site.db.next_cycle_at)

                if not site.is_active:
                    if next_cycle is not None and next_cycle <= now:
                        site_rigs = site.db.rigs or []
                        operational = [r for r in site_rigs if r and r.db.is_operational]
                        if not site_rigs:
                            reason = "no harvesters installed"
                        elif not operational:
                            broken = [r.key for r in site_rigs if r]
                            reason = f"all harvesters broken ({', '.join(broken)})"
                        elif not site.db.linked_storage:
                            reason = "no linked storage"
                        else:
                            reason = "unknown"
                        logger.log_info(
                            f"[flora_engine] {site.key}: cycle due but site inactive "
                            f"({reason}) — advancing clock without production."
                        )
                        site.schedule_next_cycle(
                            completed_boundary=floor_period(
                                next_cycle, FLORA_DELIVERY_PERIOD
                            )
                        )
                    continue
                if next_cycle is None:
                    site.schedule_next_cycle()
                    continue

                sid = int(site.id) if site.id is not None else 0
                stagger_ok = sid % FLORA_ENGINE_STAGGER_MOD == tick % FLORA_ENGINE_STAGGER_MOD
                if not stagger_ok and next_cycle > now:
                    continue

                catchup = 0
                while next_cycle <= now and catchup < MAX_CATCHUP_CYCLES:
                    summary = site.process_cycle()
                    logger.log_info(f"[flora_engine] {site.key}: {summary}")

                    owner = site.db.owner
                    if owner and hasattr(owner, "sessions") and owner.sessions.count():
                        owner.msg(f"|w[Flora: {site.key}]|n {summary}")

                    next_cycle = _parse_ts(site.db.next_cycle_at)
                    catchup += 1
                    processed += 1
                    if next_cycle is None:
                        break

            except Exception as err:
                errors += 1
                logger.log_err(
                    f"[flora_engine] Error on site {getattr(site, 'key', '?')}: {err}"
                )

        if processed or errors:
            logger.log_info(
                f"[flora_engine] Tick complete — {processed} cycle(s), {errors} error(s)."
            )
