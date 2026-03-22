# Evennia vehicle import starter package

Included:

- `vehicle_evennia_mapping_spec.md` — schema and mapping spec for the current vehicle CSV
- `typeclasses/vehicles.py` — first-pass Vehicle typeclass skeletons
- `world/import_vehicles.py` — first-pass Evennia batchcode importer

## Recommended placement inside your Evennia game

- `typeclasses/vehicles.py` → `yourgame/typeclasses/vehicles.py`
- `world/import_vehicles.py` → `yourgame/world/batchcode/import_vehicles.py`

## Run flow

1. Copy the files into your game.
2. Update `CSV_PATH` in `world/import_vehicles.py`.
3. Verify your `BATCH_IMPORT_PATH` includes the folder containing the batchcode file.
4. Test with:
   - `batchcode/debug world.batchcode.import_vehicles`
   - or `batchcode/interactive world.batchcode.import_vehicles`
5. Once satisfied, run:
   - `batchcode world.batchcode.import_vehicles`

## Notes

- The importer uses a unique tag in category `vehicle_id` as the canonical upsert key.
- The importer stores most row data under grouped `db` dicts rather than 80+ flat attributes.
- This is a **catalog importer** first. It does not yet model multiple spawned instances per catalog row.
