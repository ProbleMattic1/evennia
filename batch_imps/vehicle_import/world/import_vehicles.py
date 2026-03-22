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
# - This version is designed for the cleaned Evennia-ready CSV.
#

#HEADER
import csv
import math
import re
from pathlib import Path

from django.conf import settings
from evennia import create_object, search_object, search_tag

# Path works in Docker (volume at /usr/src/game) and local runs
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
MANAGED_TAG_CATEGORIES = {
    "vehicle_id",
    "template",
    "manufacturer",
    "vendor",
    "prototype",
    "domain",
    "family",
    "vehicle_type",
    "size_class",
    "role",
    "tech_tier",
    "availability",
    "legal_class",
    "rarity",
    "economy_band",
    "encounter_role",
    "civilian_use",
    "faction",
    "status",
}
SUPPORTED_IMPORT_ACTIONS = {"upsert", "create", "update", "skip", "deactivate"}


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


def parse_bool(value, default=True):
    value = clean_text(value)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


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


def first_value(*values):
    for value in values:
        cleaned = clean_text(value)
        if cleaned is not None:
            return cleaned
    return None


def row_slug(row, slug_column, fallback_column):
    return first_value(row.get(slug_column), slugify(row.get(fallback_column)))


def parse_import_action(row):
    action = (clean_text(row.get("Import_Action")) or "upsert").lower()
    if action not in SUPPORTED_IMPORT_ACTIONS:
        caller_msg(f"|yUnknown Import_Action '{action}' for {row.get('Vehicle_ID')}; defaulting to upsert.|n")
        return "upsert"
    return action


def resolve_typeclass(row):
    explicit = clean_text(row.get("Evennia_Typeclass"))
    if explicit:
        return explicit
    domain = row_slug(row, "Domain_Slug", "Domain")
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
        "vehicle_name": clean_text(row.get("Vehicle_Name")),
        "vehicle_slug": row_slug(row, "Vehicle_Slug", "Vehicle_Name"),
        "template_id": clean_text(row.get("Template_ID")),
        "template_name": clean_text(row.get("Template_Name")),
        "manufacturer_id": clean_text(row.get("Manufacturer_ID")),
        "manufacturer_name": clean_text(row.get("Manufacturer_Name")),
        "tech_tier_id": parse_number(row.get("Tech_Tier_ID"), integer=True),
        "tech_tier_name": clean_text(row.get("Tech_Tier_Name")),
        "tech_tier_slug": row_slug(row, "Tech_Tier_Slug", "Tech_Tier_Name"),
        "prototype_key": clean_text(row.get("Prototype_Key")),
        "import_action": parse_import_action(row),
        "active": parse_bool(row.get("Active"), default=True),
        "import_version": IMPORT_VERSION,
        "last_import_source": CSV_PATH.name,
    }


def build_specs(row):
    return {
        "domain": clean_text(row.get("Domain")),
        "domain_slug": row_slug(row, "Domain_Slug", "Domain"),
        "family": clean_text(row.get("Family")),
        "family_slug": row_slug(row, "Family_Slug", "Family"),
        "vehicle_type": clean_text(row.get("Vehicle_Type")),
        "vehicle_type_slug": row_slug(row, "Vehicle_Type_Slug", "Vehicle_Type"),
        "size_class": clean_text(row.get("Size_Class")),
        "role": clean_text(row.get("Role")),
        "role_slug": row_slug(row, "Role_Slug", "Role"),
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
        "encounter_role_slug": row_slug(row, "Encounter_Role_Slug", "Encounter_Role"),
    }


def build_economy(row):
    return {
        "operating_cost_cr_day": parse_number(row.get("Operating_Cost_cr_day"), integer=True),
        "availability": clean_text(row.get("Availability")),
        "availability_slug": row_slug(row, "Availability_Slug", "Availability"),
        "legal_class": clean_text(row.get("Legal_Class")),
        "legal_class_slug": row_slug(row, "Legal_Class_Slug", "Legal_Class"),
        "base_price_cr": parse_number(row.get("Base_Price_cr"), integer=True),
        "total_price_cr": parse_number(row.get("Total_Price_cr"), integer=True),
        "default_loadout_cost_cr": parse_number(row.get("Default_Loadout_Cost_cr"), integer=True),
        "vendor_id": clean_text(row.get("Vendor_ID")),
        "vendor_name": clean_text(row.get("Vendor_Name")),
        "vendor_class": clean_text(row.get("Vendor_Class")),
        "economy_band": clean_text(row.get("Economy_Band")),
        "economy_band_slug": row_slug(row, "Economy_Band_Slug", "Economy_Band"),
        "acquisition_tier": clean_text(row.get("Acquisition_Tier")),
        "license_requirement": clean_text(row.get("License_Requirement")),
        "upkeep_band": clean_text(row.get("Upkeep_Band")),
        "rarity_score": parse_number(row.get("Rarity_Score"), integer=True),
        "rarity": clean_text(row.get("Rarity")),
        "rarity_slug": row_slug(row, "Rarity_Slug", "Rarity"),
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


def build_import_meta(row):
    return {
        "lockstring": clean_text(row.get("Lockstring")),
        "spawn_location_tag": clean_text(row.get("Spawn_Location_Tag")),
        "home_tag": clean_text(row.get("Home_Tag")),
        "import_action": parse_import_action(row),
        "active": parse_bool(row.get("Active"), default=True),
    }


def build_tags(row):
    tags = []
    maybe_tags = [
        (clean_text(row.get("Vehicle_ID")), "vehicle_id"),
        (clean_text(row.get("Template_ID")), "template"),
        (clean_text(row.get("Manufacturer_ID")), "manufacturer"),
        (clean_text(row.get("Vendor_ID")), "vendor"),
        (clean_text(row.get("Prototype_Key")), "prototype"),
        (row_slug(row, "Domain_Slug", "Domain"), "domain"),
        (row_slug(row, "Family_Slug", "Family"), "family"),
        (row_slug(row, "Vehicle_Type_Slug", "Vehicle_Type"), "vehicle_type"),
        (slugify(row.get("Size_Class")), "size_class"),
        (row_slug(row, "Role_Slug", "Role"), "role"),
        (row_slug(row, "Tech_Tier_Slug", "Tech_Tier_Name"), "tech_tier"),
        (row_slug(row, "Availability_Slug", "Availability"), "availability"),
        (row_slug(row, "Legal_Class_Slug", "Legal_Class"), "legal_class"),
        (row_slug(row, "Rarity_Slug", "Rarity"), "rarity"),
        (row_slug(row, "Economy_Band_Slug", "Economy_Band"), "economy_band"),
        (row_slug(row, "Encounter_Role_Slug", "Encounter_Role"), "encounter_role"),
        (clean_text(row.get("Civilian_Use_Tag")), "civilian_use"),
        (clean_text(row.get("Primary_Faction_Tag")), "faction"),
        (clean_text(row.get("Secondary_Faction_Tag")), "faction"),
        (("active" if parse_bool(row.get("Active"), default=True) else "inactive"), "status"),
    ]
    for tagkey, category in maybe_tags:
        if tagkey:
            tags.append((tagkey, category))
    return tags


def build_aliases(row):
    aliases = []
    for value in (
        clean_text(row.get("Vehicle_ID")),
        clean_text(row.get("Template_ID")),
        clean_text(row.get("Prototype_Key")),
        row_slug(row, "Vehicle_Slug", "Vehicle_Name"),
    ):
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


def parse_tag_reference(ref):
    ref = clean_text(ref)
    if not ref:
        return None, None
    if ":" in ref:
        left, right = ref.split(":", 1)
        return clean_text(right), clean_text(left)
    if "|" in ref:
        left, right = ref.split("|", 1)
        return clean_text(left), clean_text(right)
    return ref, None


def resolve_object_by_tag_reference(ref, field_label):
    tag_key, category = parse_tag_reference(ref)
    if not tag_key:
        return None
    matches = search_tag(tag_key, category=category)
    if not matches:
        caller_msg(f"|yNo object found for {field_label} tag '{ref}'. Leaving unset.|n")
        return None
    if len(matches) > 1:
        caller_msg(f"|yMultiple objects found for {field_label} tag '{ref}'. Using first.|n")
    return matches[0]


def apply_aliases(obj, row):
    desired_aliases = build_aliases(row)
    current_aliases = set(obj.aliases.all())
    for alias in list(current_aliases):
        if alias not in desired_aliases:
            obj.aliases.remove(alias)
    for alias in desired_aliases:
        if alias not in current_aliases:
            obj.aliases.add(alias)


def apply_managed_tags(obj, row):
    desired_tags = set(build_tags(row))
    existing_tags = {(tag.db_key, tag.db_category) for tag in obj.tags.all(return_objs=True)}

    for tag_key, tag_category in existing_tags:
        if tag_category in MANAGED_TAG_CATEGORIES and (tag_key, tag_category) not in desired_tags:
            obj.tags.remove(tag_key, category=tag_category)

    for tag_key, tag_category in desired_tags:
        if (tag_key, tag_category) not in existing_tags:
            obj.tags.add(tag_key, category=tag_category)


def apply_lockstring(obj, row):
    lockstring = clean_text(row.get("Lockstring"))
    if lockstring:
        obj.locks.clear()
        obj.locks.add(lockstring)


def apply_locations(obj, row):
    spawn_ref = clean_text(row.get("Spawn_Location_Tag"))
    home_ref = clean_text(row.get("Home_Tag"))

    location_obj = resolve_object_by_tag_reference(spawn_ref, "Spawn_Location_Tag") if spawn_ref else None
    home_obj = resolve_object_by_tag_reference(home_ref, "Home_Tag") if home_ref else None

    if location_obj:
        obj.location = location_obj
    if home_obj:
        obj.home = home_obj


def apply_vehicle_payload(obj, row):
    obj.key = clean_text(row.get("Vehicle_Name")) or obj.key
    obj.db.catalog = build_catalog(row)
    obj.db.specs = build_specs(row)
    obj.db.combat = build_combat(row)
    obj.db.economy = build_economy(row)
    obj.db.options = normalize_options(row)
    obj.db.weapon_profiles = normalize_weapon_profiles(row)
    obj.db.lore = build_lore(row)
    obj.db.import_meta = build_import_meta(row)
    obj.db.prototype_key = clean_text(row.get("Prototype_Key"))
    obj.db.vehicle_id = obj.db.catalog.get("vehicle_id")
    obj.db.vehicle_slug = row_slug(row, "Vehicle_Slug", "Vehicle_Name")
    obj.db.vehicle_data_version = IMPORT_VERSION
    obj.db.is_active = parse_bool(row.get("Active"), default=True)

    apply_aliases(obj, row)
    apply_managed_tags(obj, row)
    apply_lockstring(obj, row)
    apply_locations(obj, row)
    return obj


def deactivate_vehicle(obj, row):
    if DRY_RUN:
        caller_msg(f"[DRY RUN] Would deactivate {obj.key} ({obj.db.vehicle_id})")
        return obj, "dry-run"

    obj.db.is_active = False
    obj.db.import_meta = build_import_meta(row)
    obj.tags.remove("active", category="status")
    obj.tags.add("inactive", category="status")
    return obj, "deactivated"


def upsert_vehicle(row):
    vehicle_id = clean_text(row.get("Vehicle_ID"))
    if not vehicle_id:
        caller_msg("|rSkipping row with no Vehicle_ID.|n")
        return None, "skipped"

    action = parse_import_action(row)
    obj = get_existing_vehicle(vehicle_id)

    if action == "skip":
        return None, "skipped"

    if action == "deactivate":
        if obj:
            return deactivate_vehicle(obj, row)
        caller_msg(f"|yDeactivation requested but no existing object found for {vehicle_id}.|n")
        return None, "skipped"

    if action == "create" and obj:
        caller_msg(f"|yCreate-only row found existing object for {vehicle_id}; skipping.|n")
        return obj, "skipped"

    if action == "update" and not obj:
        caller_msg(f"|yUpdate-only row found no existing object for {vehicle_id}; skipping.|n")
        return None, "skipped"

    if obj:
        if DRY_RUN:
            caller_msg(f"[DRY RUN] Would update {vehicle_id}: {clean_text(row.get('Vehicle_Name'))}")
            return obj, "dry-run"
        apply_vehicle_payload(obj, row)
        return obj, "updated"

    if not parse_bool(row.get("Active"), default=True):
        caller_msg(f"|yInactive row with no existing object for {vehicle_id}; not creating.|n")
        return None, "skipped"

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
deactivated = 0
skipped = 0
dry_run = 0

for ix, row in enumerate(rows, start=1):
    obj, status = upsert_vehicle(row)
    if status == "created":
        created += 1
    elif status == "updated":
        updated += 1
    elif status == "deactivated":
        deactivated += 1
    elif status == "dry-run":
        dry_run += 1
    else:
        skipped += 1

    if ix % 250 == 0:
        caller_msg(
            f"Processed {ix}/{len(rows)} | created={created} updated={updated} deactivated={deactivated} dry_run={dry_run} skipped={skipped}"
        )

caller_msg(
    f"|gVehicle import complete.|n rows={len(rows)} created={created} updated={updated} deactivated={deactivated} dry_run={dry_run} skipped={skipped}"
)
