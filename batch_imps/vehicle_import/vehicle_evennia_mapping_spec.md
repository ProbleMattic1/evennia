# Evennia Vehicle Import Schema / Mapping Spec

This spec converts the current `Vehicles-Table 1.csv` into an Evennia-friendly import contract.

It is designed for a **hybrid Evennia model**:

- **Typeclasses** define behavior.
- **Object Attributes (`obj.db`)** hold persistent vehicle data.
- **Tags** hold searchable classification data.
- **Aliases** hold stable lookup keys.
- **Batchcode** imports/upserts the CSV into live Evennia objects.


## 1) Import target

Each row becomes one Evennia object with:

- `key` = `Vehicle_Name`
- `typeclass` = resolved from `Domain` / `Vehicle_Type` or explicit override column
- unique tag = `Vehicle_ID` in category `vehicle_id`
- aliases = `Vehicle_ID`, optional `Template_ID`, optional sanitized slug
- `db.vehicle_id` = immutable canonical ID
- `db.vehicle_data_version` = importer version stamp
- `db.catalog`, `db.specs`, `db.combat`, `db.economy`, `db.options`, `db.weapon_profiles`, `db.lore` = normalized grouped data

## 2) Recommended CSV additions

Add these columns before you scale imports further:

- `Evennia_Typeclass`
- `Prototype_Key`
- `Lockstring`
- `Spawn_Location_Tag`
- `Home_Tag`
- `Import_Action` (`upsert`, `skip`, `delete`)
- `Active` (`true/false`)

None of these are required for the first importer below, but they will make the pipeline much cleaner.

## 3) Native Evennia fields vs custom data

### Native Evennia fields used directly

| CSV / Derived | Evennia field | Notes |
|---|---|---|
| `Vehicle_Name` | `key` | Primary in-game name |
| `Evennia_Typeclass` or derived | `typeclass` | Defaults by domain/type mapping |
| derived aliases | `aliases` | Includes `Vehicle_ID` |
| derived tags | `tags` | For search/filter/category |
| `Lockstring` (future) | `locks` | Optional import-time access controls |

### Persistent object Attributes (`obj.db`)

All gameplay data beyond the object identity should live in `obj.db`.

#### Identity / catalog
- `vehicle_id`
- `template_id`
- `template_name`
- `manufacturer_id`
- `manufacturer_name`
- `tech_tier_id`
- `tech_tier_name`

#### Specs
- `domain`
- `family`
- `vehicle_type`
- `size_class`
- `role`
- `genre_tag`
- `lift_mode`
- `propulsion`
- `power_source`
- `hull_type`
- `crew_min`
- `crew_std`
- `passenger_cap`
- `cargo_t`
- `length_m`
- `beam_m`
- `height_m`
- `mass_t`
- `local_cruise_kph`
- `water_cruise_kph`
- `dive_depth_m`
- `vacuum_deltav_kps`
- `ftl_pc_day`
- `range_km`
- `endurance_days`
- `maintenance_hours_100h`
- `crew_quality_minimum`

#### Combat / tactical
- `agility`
- `sensors`
- `stealth`
- `armor`
- `shields`
- `hp`
- `hardpoints`
- `option_slots`
- `combat_rating`
- `threat_rating`
- `campaign_balance_points`
- `encounter_role`

#### Economy / ownership
- `operating_cost_cr_day`
- `base_price_cr`
- `total_price_cr`
- `default_loadout_cost_cr`
- `salvage_value_cr`
- `refit_cap_cr`
- `availability`
- `legal_class`
- `economy_band`
- `acquisition_tier`
- `license_requirement`
- `upkeep_band`
- `rarity_score`
- `rarity`
- `vendor_id`
- `vendor_name`
- `vendor_class`

#### Loadout / options
- `default_options` = list of dicts
- `weapon_profiles` = list of dicts

#### Lore / notes
- `notes`
- `source_note`
- `primary_faction_tag`
- `secondary_faction_tag`
- `civilian_use_tag`

### Tags

Tags make searching and filtering easier than trying to query everything from attributes.

Recommended tag categories:

- `vehicle_id` → `Vehicle_ID`
- `template` → `Template_ID`
- `manufacturer` → `Manufacturer_ID`
- `vendor` → `Vendor_ID`
- `domain` → `Domain`
- `family` → `Family`
- `vehicle_type` → `Vehicle_Type`
- `size_class` → `Size_Class`
- `role` → `Role`
- `tech_tier` → slugged `Tech_Tier_Name`
- `availability` → `Availability`
- `legal_class` → `Legal_Class`
- `rarity` → `Rarity`
- `faction` → `Primary_Faction_Tag`, `Secondary_Faction_Tag`
- `civilian_use` → `Civilian_Use_Tag`
- `economy_band` → `Economy_Band`
- `encounter_role` → `Encounter_Role`

## 4) Normalization rules

### Numeric normalization

The importer should convert the following to numbers:

- integer-like: `Crew_Min`, `Crew_Std`, `Passenger_Cap`, `HP`, `Hardpoints`, `Option_Slots`, `Rarity_Score`
- float-like: `Cargo_t`, `Length_m`, `Beam_m`, `Height_m`, `Mass_t`, `Local_Cruise_kph`, `Water_Cruise_kph`, `Dive_Depth_m`, `Vacuum_DeltaV_kps`, `FTL_pc_day`, `Range_km`, `Endurance_days`, `Agility`, `Sensors`, `Stealth`, `Armor`, `Shields`, `Maintenance_Hours_100h`, `Combat_Rating`, `Threat_Rating`, `Campaign_Balance_Points`
- currency-like strings stripped to integer credits:
  - `Operating_Cost_cr_day`
  - `Option_1_Cost_cr`
  - `Option_2_Cost_cr`
  - `Option_3_Cost_cr`
  - `Base_Price_cr`
  - `Total_Price_cr`
  - `Default_Loadout_Cost_cr`
  - `Salvage_Value_cr`
  - `Refit_Cap_cr`

Examples:
- `"125 cr"` → `125`
- `"2,700"` → `2700`
- `""` or NaN → `None`

### Text normalization

- Empty strings and NaN → `None`
- Tag values should be slugged/lowercased when category search consistency matters
- Preserve display strings in attributes when useful for UI output

## 5) Typeclass resolution

Default mapping for first pass:

- `Domain == "Surface"` → `typeclasses.vehicles.SurfaceVehicle`
- `Domain == "Water"` → `typeclasses.vehicles.Watercraft`
- `Domain == "Air"` → `typeclasses.vehicles.Aircraft`
- `Domain == "Space"` → `typeclasses.vehicles.Spacecraft`
- fallback → `typeclasses.vehicles.Vehicle`

You can refine later with `Vehicle_Type`, `Family`, or a dedicated `Evennia_Typeclass` column.

## 6) Nested attribute structure

Each imported vehicle stores grouped data for maintainability.

```python
obj.db.catalog = {
    "vehicle_id": "...",
    "template_id": "...",
    "template_name": "...",
    "manufacturer_id": "...",
    "manufacturer_name": "...",
    "tech_tier_id": 1,
    "tech_tier_name": "Frontier",
}

obj.db.specs = {
    "domain": "Surface",
    "family": "Personal Lift",
    "vehicle_type": "Hover-board",
    ...
}

obj.db.economy = {
    "base_price_cr": 1289,
    "total_price_cr": 14844,
    ...
}
```

This is easier to maintain than writing 70+ flat `obj.db.*` fields.

## 7) Import semantics

The first importer should behave as an **upsert**:

- find existing object by unique tag category `vehicle_id`
- if found: update fields/tags/aliases
- if not found: create object
- keep object name in sync with CSV unless intentionally customized later
- store `last_imported_from = "Vehicles-Table 1.csv"`

## 8) Search and uniqueness rules

Never trust name-only lookup for updates.

Use one canonical unique identifier:

- tag key = `Vehicle_ID`
- tag category = `vehicle_id`

Optional redundancy:
- alias = `Vehicle_ID`
- `db.vehicle_id` = `Vehicle_ID`

## 9) Suggested future expansion

After the first import works, add:

- `Prototype_Key` support for archetype spawning
- location/home assignment using room tags
- ownership linkage to character/account IDs
- installable modules as child objects rather than only list data
- timed upkeep/fuel/repair via Scripts
- separate `VehicleTemplate` / `VehicleInstance` split if you later want one catalog row to spawn many physical instances

## 10) Column-by-column mapping

| CSV Column | Normalized destination | Type |
|---|---|---|
| Vehicle_ID | `db.catalog.vehicle_id`, tag:`vehicle_id` | str |
| Vehicle_Name | `key` | str |
| Template_ID | `db.catalog.template_id`, tag:`template` | str |
| Template_Name | `db.catalog.template_name` | str |
| Manufacturer_ID | `db.catalog.manufacturer_id`, tag:`manufacturer` | str |
| Manufacturer_Name | `db.catalog.manufacturer_name` | str |
| Tech_Tier_ID | `db.catalog.tech_tier_id` | int |
| Tech_Tier_Name | `db.catalog.tech_tier_name`, tag:`tech_tier` | str |
| Domain | `db.specs.domain`, tag:`domain` | str |
| Family | `db.specs.family`, tag:`family` | str |
| Vehicle_Type | `db.specs.vehicle_type`, tag:`vehicle_type` | str |
| Size_Class | `db.specs.size_class`, tag:`size_class` | str |
| Role | `db.specs.role`, tag:`role` | str |
| Genre_Tag | `db.specs.genre_tag` | str |
| Lift_Mode | `db.specs.lift_mode` | str |
| Propulsion | `db.specs.propulsion` | str |
| Power_Source | `db.specs.power_source` | str |
| Hull_Type | `db.specs.hull_type` | str |
| Crew_Min | `db.specs.crew_min` | int |
| Crew_Std | `db.specs.crew_std` | int |
| Passenger_Cap | `db.specs.passenger_cap` | int |
| Cargo_t | `db.specs.cargo_t` | float |
| Length_m | `db.specs.length_m` | float |
| Beam_m | `db.specs.beam_m` | float |
| Height_m | `db.specs.height_m` | float |
| Mass_t | `db.specs.mass_t` | float |
| Local_Cruise_kph | `db.specs.local_cruise_kph` | float |
| Water_Cruise_kph | `db.specs.water_cruise_kph` | float |
| Dive_Depth_m | `db.specs.dive_depth_m` | float |
| Vacuum_DeltaV_kps | `db.specs.vacuum_deltav_kps` | float |
| FTL_pc_day | `db.specs.ftl_pc_day` | float |
| Range_km | `db.specs.range_km` | float |
| Endurance_days | `db.specs.endurance_days` | float |
| Agility | `db.combat.agility` | float |
| Sensors | `db.combat.sensors` | float |
| Stealth | `db.combat.stealth` | float |
| Armor | `db.combat.armor` | float |
| Shields | `db.combat.shields` | float |
| HP | `db.combat.hp` | int |
| Hardpoints | `db.combat.hardpoints` | int |
| Option_Slots | `db.combat.option_slots` | int |
| Operating_Cost_cr_day | `db.economy.operating_cost_cr_day` | int |
| Maintenance_Hours_100h | `db.specs.maintenance_hours_100h` | float |
| Availability | `db.economy.availability`, tag:`availability` | str |
| Legal_Class | `db.economy.legal_class`, tag:`legal_class` | str |
| Default_Option_1_ID | `db.options[0].id` | str |
| Default_Option_1 | `db.options[0].name` | str |
| Option_1_Cost_cr | `db.options[0].cost_cr` | int |
| Default_Option_2_ID | `db.options[1].id` | str |
| Default_Option_2 | `db.options[1].name` | str |
| Option_2_Cost_cr | `db.options[1].cost_cr` | int |
| Default_Option_3_ID | `db.options[2].id` | str |
| Default_Option_3 | `db.options[2].name` | str |
| Option_3_Cost_cr | `db.options[2].cost_cr` | int |
| Base_Price_cr | `db.economy.base_price_cr` | int |
| Total_Price_cr | `db.economy.total_price_cr` | int |
| Notes | `db.lore.notes` | str |
| Source_Note | `db.lore.source_note` | str |
| Weapon_Profile_1_ID | `db.weapon_profiles[0].id` | str |
| Weapon_Profile_1 | `db.weapon_profiles[0].name` | str |
| Weapon_Profile_2_ID | `db.weapon_profiles[1].id` | str |
| Weapon_Profile_2 | `db.weapon_profiles[1].name` | str |
| Default_Loadout_Cost_cr | `db.economy.default_loadout_cost_cr` | int |
| Combat_Rating | `db.combat.combat_rating` | float |
| Threat_Rating | `db.combat.threat_rating` | float |
| Primary_Faction_Tag | `db.lore.primary_faction_tag`, tag:`faction` | str |
| Secondary_Faction_Tag | `db.lore.secondary_faction_tag`, tag:`faction` | str |
| Civilian_Use_Tag | `db.lore.civilian_use_tag`, tag:`civilian_use` | str |
| Rarity_Score | `db.economy.rarity_score` | int |
| Rarity | `db.economy.rarity`, tag:`rarity` | str |
| Vendor_ID | `db.economy.vendor_id`, tag:`vendor` | str |
| Vendor_Name | `db.economy.vendor_name` | str |
| Vendor_Class | `db.economy.vendor_class` | str |
| Economy_Band | `db.economy.economy_band`, tag:`economy_band` | str |
| Acquisition_Tier | `db.economy.acquisition_tier` | str |
| License_Requirement | `db.economy.license_requirement` | str |
| Upkeep_Band | `db.economy.upkeep_band` | str |
| Campaign_Balance_Points | `db.combat.campaign_balance_points` | float |
| Encounter_Role | `db.combat.encounter_role`, tag:`encounter_role` | str |
| Salvage_Value_cr | `db.economy.salvage_value_cr` | int |
| Refit_Cap_cr | `db.economy.refit_cap_cr` | int |
| Crew_Quality_Minimum | `db.specs.crew_quality_minimum` | str |

## 11) What this first pass intentionally does not solve

- multiple physical instances from one catalog row
- room/ship interior generation
- ownership / hangar assignment
- installable component objects
- fuel/ammo/maintenance Scripts
- prototype inheritance trees

Those can layer on cleanly after the catalog import is stable.
