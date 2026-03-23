#
# Evennia batchcode importer for vehicle catalog rows.
#
# Usage (example):
#   > batchcode world.batchcode.import_vehicles
#   > batchcode/debug world.batchcode.import_vehicles
#   > batchcode/interactive world.batchcode.import_vehicles
#
# Put this file somewhere under BATCH_IMPORT_PATH, commonly in:
#   yourgame/world/batchcode/import_vehicles.py
#
# IMPORTANT:
# - This batchcode assumes the CSV is reachable by the Evennia server process.
# - Update CSV_PATH below to point at your actual file location.
#

#HEADER
import csv
import math
import re
from pathlib import Path

from django.conf import settings
from evennia import create_object, search_tag

CSV_PATH = Path(settings.GAME_DIR).parent / "batch_imps/vehicle_import/world/Vehicles-Table-1.csv"
IMPORT_VERSION = "vehicle-import-v1"
DRY_RUN = bool(DEBUG)

TYPECLASS_MAP = {
    "surface": "typeclasses.vehicles.SurfaceVehicle",
    "water": "typeclasses.vehicles.Watercraft",
    "air": "typeclasses.vehicles.Aircraft",
    "space": "typeclasses.vehicles.Spacecraft",
}

SEARCH_TAG_CATEGORY = "vehicle_id"


def caller_msg(text):
    if caller:
        caller.msg(text)


def clean_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        if math.isnan(value):
            return None
    except Exception:
        pass
    return value


def parse_number(value, integer=False):
    value = clean_text(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if integer else float(value)

    raw = str(value).strip().lower()
    raw = raw.replace(",", "")
    raw = raw.replace(" cr", "")
    raw = raw.replace("cr", "")
    raw = raw.strip()

    if raw in {"", "nan", "none", "null"}:
        return None

    try:
        num = float(raw)
        return int(num) if integer else num
    except ValueError:
        return None


def slugify(value):
    value = clean_text(value)
    if not value:
        return None
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or None


def resolve_typeclass(row):
    explicit = clean_text(row.get("Evennia_Typeclass"))
    if explicit:
        return explicit
    domain = slugify(row.get("Domain"))
    return TYPECLASS_MAP.get(domain, "typeclasses.vehicles.Vehicle")


def normalize_options(row):
    options = []
    for idx in (1, 2, 3):
        option_id = clean_text(row.get(f"Default_Option_{idx}_ID"))
        option_name = clean_text(row.get(f"Default_Option_{idx}"))
        option_cost = parse_number(row.get(f"Option_{idx}_Cost_cr"), integer=True)
        if option_id or option_name or option_cost is not None:
            options.append({"slot": idx, "id": option_id, "name": option_name, "cost_cr": option_cost})
    return options


def normalize_weapon_profiles(row):
    profiles = []
    for idx in (1, 2):
        profile_id = clean_text(row.get(f"Weapon_Profile_{idx}_ID"))
        profile_name = clean_text(row.get(f"Weapon_Profile_{idx}"))
        if profile_id or profile_name:
            profiles.append({"slot": idx, "id": profile_id, "name": profile_name})
    return profiles


def build_catalog(row):
    return {
        "vehicle_id": clean_text(row.get("Vehicle_ID")),
        "template_id": clean_text(row.get("Template_ID")),
        "template_name": clean_text(row.get("Template_Name")),
        "manufacturer_id": clean_text(row.get("Manufacturer_ID")),
        "manufacturer_name": clean_text(row.get("Manufacturer_Name")),
        "tech_tier_id": parse_number(row.get("Tech_Tier_ID"), integer=True),
        "tech_tier_name": clean_text(row.get("Tech_Tier_Name")),
        "import_version": IMPORT_VERSION,
        "last_import_source": CSV_PATH.name,
    }


def build_specs(row):
    return {
        "domain": clean_text(row.get("Domain")),
        "family": clean_text(row.get("Family")),
        "vehicle_type": clean_text(row.get("Vehicle_Type")),
        "size_class": clean_text(row.get("Size_Class")),
        "role": clean_text(row.get("Role")),
        "genre_tag": clean_text(row.get("Genre_Tag")),
        "lift_mode": clean_text(row.get("Lift_Mode")),
        "propulsion": clean_text(row.get("Propulsion")),
        "power_source": clean_text(row.get("Power_Source")),
        "hull_type": clean_text(row.get("Hull_Type")),
        "crew_min": parse_number(row.get("Crew_Min"), integer=True),
        "crew_std": parse_number(row.get("Crew_Std"), integer=True),
        "passenger_cap": parse_number(row.get("Passenger_Cap"), integer=True),
        "cargo_t": parse_number(row.get("Cargo_t")),
        "length_m": parse_number(row.get("Length_m")),
        "beam_m": parse_number(row.get("Beam_m")),
        "height_m": parse_number(row.get("Height_m")),
        "mass_t": parse_number(row.get("Mass_t")),
        "local_cruise_kph": parse_number(row.get("Local_Cruise_kph")),
        "water_cruise_kph": parse_number(row.get("Water_Cruise_kph")),
        "dive_depth_m": parse_number(row.get("Dive_Depth_m")),
        "vacuum_deltav_kps": parse_number(row.get("Vacuum_DeltaV_kps")),
        "ftl_pc_day": parse_number(row.get("FTL_pc_day")),
        "range_km": parse_number(row.get("Range_km")),
        "endurance_days": parse_number(row.get("Endurance_days")),
        "maintenance_hours_100h": parse_number(row.get("Maintenance_Hours_100h")),
        "crew_quality_minimum": clean_text(row.get("Crew_Quality_Minimum")),
    }


def build_combat(row):
    return {
        "agility": parse_number(row.get("Agility")),
        "sensors": parse_number(row.get("Sensors")),
        "stealth": parse_number(row.get("Stealth")),
        "armor": parse_number(row.get("Armor")),
        "shields": parse_number(row.get("Shields")),
        "hp": parse_number(row.get("HP"), integer=True),
        "hardpoints": parse_number(row.get("Hardpoints"), integer=True),
        "option_slots": parse_number(row.get("Option_Slots"), integer=True),
        "combat_rating": parse_number(row.get("Combat_Rating")),
        "threat_rating": parse_number(row.get("Threat_Rating")),
        "campaign_balance_points": parse_number(row.get("Campaign_Balance_Points")),
        "encounter_role": clean_text(row.get("Encounter_Role")),
    }


def build_economy(row):
    return {
        "operating_cost_cr_day": parse_number(row.get("Operating_Cost_cr_day"), integer=True),
        "availability": clean_text(row.get("Availability")),
        "legal_class": clean_text(row.get("Legal_Class")),
        "base_price_cr": parse_number(row.get("Base_Price_cr"), integer=True),
        "total_price_cr": parse_number(row.get("Total_Price_cr"), integer=True),
        "default_loadout_cost_cr": parse_number(row.get("Default_Loadout_Cost_cr"), integer=True),
        "vendor_id": clean_text(row.get("Vendor_ID")),
        "vendor_name": clean_text(row.get("Vendor_Name")),
        "vendor_class": clean_text(row.get("Vendor_Class")),
        "economy_band": clean_text(row.get("Economy_Band")),
        "acquisition_tier": clean_text(row.get("Acquisition_Tier")),
        "license_requirement": clean_text(row.get("License_Requirement")),
        "upkeep_band": clean_text(row.get("Upkeep_Band")),
        "rarity_score": parse_number(row.get("Rarity_Score"), integer=True),
        "rarity": clean_text(row.get("Rarity")),
        "salvage_value_cr": parse_number(row.get("Salvage_Value_cr"), integer=True),
        "refit_cap_cr": parse_number(row.get("Refit_Cap_cr"), integer=True),
    }


def build_lore(row):
    return {
        "notes": clean_text(row.get("Notes")),
        "source_note": clean_text(row.get("Source_Note")),
        "primary_faction_tag": clean_text(row.get("Primary_Faction_Tag")),
        "secondary_faction_tag": clean_text(row.get("Secondary_Faction_Tag")),
        "civilian_use_tag": clean_text(row.get("Civilian_Use_Tag")),
    }


def build_tags(row):
    tags = []
    maybe_tags = [
        (clean_text(row.get("Vehicle_ID")), "vehicle_id"),
        (clean_text(row.get("Template_ID")), "template"),
        (clean_text(row.get("Manufacturer_ID")), "manufacturer"),
        (clean_text(row.get("Vendor_ID")), "vendor"),
        (slugify(row.get("Domain")), "domain"),
        (slugify(row.get("Family")), "family"),
        (slugify(row.get("Vehicle_Type")), "vehicle_type"),
        (slugify(row.get("Size_Class")), "size_class"),
        (slugify(row.get("Role")), "role"),
        (slugify(row.get("Tech_Tier_Name")), "tech_tier"),
        (slugify(row.get("Availability")), "availability"),
        (slugify(row.get("Legal_Class")), "legal_class"),
        (slugify(row.get("Rarity")), "rarity"),
        (slugify(row.get("Economy_Band")), "economy_band"),
        (slugify(row.get("Encounter_Role")), "encounter_role"),
        (slugify(row.get("Civilian_Use_Tag")), "civilian_use"),
        (clean_text(row.get("Primary_Faction_Tag")), "faction"),
        (clean_text(row.get("Secondary_Faction_Tag")), "faction"),
    ]
    for tagkey, category in maybe_tags:
        if tagkey:
            tags.append((tagkey, category))
    return tags


def build_aliases(row):
    aliases = []
    for value in (clean_text(row.get("Vehicle_ID")), clean_text(row.get("Template_ID")), slugify(row.get("Vehicle_Name"))):
        if value and value not in aliases:
            aliases.append(value)
    return aliases


def get_existing_vehicle(vehicle_id):
    matches = search_tag(vehicle_id, category=SEARCH_TAG_CATEGORY)
    if not matches:
        return None
    if len(matches) > 1:
        caller_msg(f"|rWarning: multiple vehicle matches for {vehicle_id}; using first.|n")
    return matches[0]


def apply_vehicle_payload(obj, row):
    obj.key = clean_text(row.get("Vehicle_Name")) or obj.key
    obj.db.catalog = build_catalog(row)
    obj.db.specs = build_specs(row)
    obj.db.combat = build_combat(row)
    obj.db.economy = build_economy(row)
    obj.db.options = normalize_options(row)
    obj.db.weapon_profiles = normalize_weapon_profiles(row)
    obj.db.lore = build_lore(row)
    obj.db.vehicle_id = obj.db.catalog.get("vehicle_id")
    obj.db.vehicle_data_version = IMPORT_VERSION

    existing_aliases = set(obj.aliases.all())
    for alias in build_aliases(row):
        if alias not in existing_aliases:
            obj.aliases.add(alias)

    existing_tag_pairs = {(tag.db_key, tag.db_category) for tag in obj.tags.all(return_objs=True)}
    for tag_key, tag_category in build_tags(row):
        if (tag_key, tag_category) not in existing_tag_pairs:
            obj.tags.add(tag_key, category=tag_category)

    return obj


def upsert_vehicle(row):
    vehicle_id = clean_text(row.get("Vehicle_ID"))
    if not vehicle_id:
        caller_msg("|rSkipping row with no Vehicle_ID.|n")
        return None, "skipped"

    obj = get_existing_vehicle(vehicle_id)

    if obj:
        apply_vehicle_payload(obj, row)
        return obj, "updated"

    if DRY_RUN:
        caller_msg(f"[DRY RUN] Would create {vehicle_id}: {clean_text(row.get('Vehicle_Name'))}")
        return None, "dry-run"

    obj = create_object(
        typeclass=resolve_typeclass(row),
        key=clean_text(row.get("Vehicle_Name")) or vehicle_id,
        aliases=build_aliases(row),
        tags=build_tags(row),
    )
    apply_vehicle_payload(obj, row)
    return obj, "created"


def load_rows():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


#CODE
rows = load_rows()
caller_msg(f"Vehicle import starting from {CSV_PATH} with {len(rows)} rows. DEBUG={DEBUG}")

created = 0
updated = 0
skipped = 0
dry_run = 0

for ix, row in enumerate(rows, start=1):
    obj, status = upsert_vehicle(row)
    if status == "created":
        created += 1
    elif status == "updated":
        updated += 1
    elif status == "dry-run":
        dry_run += 1
    else:
        skipped += 1

    if ix % 250 == 0:
        caller_msg(
            f"Processed {ix}/{len(rows)} | created={created} updated={updated} dry_run={dry_run} skipped={skipped}"
        )

caller_msg(
    f"|gVehicle import complete.|n rows={len(rows)} created={created} updated={updated} dry_run={dry_run} skipped={skipped}"
)
