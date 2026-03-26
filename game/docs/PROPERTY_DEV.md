# Property (developer)

- **Authority:** `PropertyLot` (parcel), `PropertyClaim` (deed), `PropertyHolding` (simulation + place layer).
- **Income tick:** `PropertyOperationsEngine` + `property_operation_registry` (`active_holding_ids`).
- **Extend income:** `OPERATION_HANDLERS` in `typeclasses/property_operation_handlers.py`.
- **New structure blueprint:** `PropertyStructure`, `apply_blueprint(id)`; tags on `realty`.
- **Structure upgrades:** `world/property_structure_upgrade_registry.py` (`STRUCTURE_UPGRADE_DEFS`, `STRUCTURE_UPGRADE_TICK`); purchase via `typeclasses/property_structure_upgrades.py` and `POST …/ui/property/structure-upgrade` `{ claimId, structureId, upgradeKey }`.
- **Extra structure slots:** `property_development.purchase_extra_structure_slot`; `POST …/ui/property/purchase-extra-slot` `{ claimId }`. In-game: `buypropertyslot`, `upgradeproperty`.
- **Place layer:** `typeclasses.property_places` — `open_property_shell`, `resolve_property_root_room`, `ensure_district_exit`.
- **Events:** `PropertyEventsEngine` (hourly); `holding.db.event_queue`, `holding.db.staff`.
- **Combat hook:** `property_combat.property_raid_outcome`.
- **Web:** `property_claim_detail_state` includes `holding` (camelCase). `POST …/ui/property/start-operation` body `{ claimId, kind? }` (deed must be on character). Ownership changes go through `PropertyHolding.set_title_owner` only.
- **In-game:** `startproperty` / `startpropertyop` / `propertystart` — same rules as POST.
- **Ops health (staff Django user):** `GET …/ui/property/ops-health` (see `web.urls` mount; Next proxy may use `/api/ui/…`).

## Evennia shell diagnostics

```text
# Count holdings
from evennia import search_tag
len(search_tag("property_holding", category="realty"))
```

Structured payout logs use the prefix `[property_ops]` with `holding_id`, `lot_key`, `amount`.
