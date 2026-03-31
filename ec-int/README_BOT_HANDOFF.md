# Evennia Economy Automation Starter Package

## Purpose

This package is a concrete starter implementation for adding a **bot-friendly, production-oriented economy automation layer** to an Evennia game that already has:

- a global economy script (`typeclasses.economy.EconomyEngine`)
- shop/vendor objects (`typeclasses.shops.CatalogVendor`)
- property operations and other scheduled systems
- a canonical UTC time module (`world.time`)

This package does **not** replace the current economy. It adds a clean automation layer that can be merged in incrementally.

The design goal is to standardize three things:

1. **Pricing policy** — all prices derive from time-to-earn, progression tier, and ROI expectations.
2. **Settlement policy** — passive income assets are settled on-demand from elapsed time instead of requiring a constant per-object ticker.
3. **Control policy** — one global balancing script can adjust modifiers, sinks, floors/ceilings, and cadence-driven maintenance.

---

## What this package assumes about the existing codebase

The attached codebase already contains the following patterns that this package intentionally follows:

- `game/typeclasses/economy.py` defines a persistent `EconomyEngine` and exposes ledger helpers and price lookup helpers.
- `game/typeclasses/shops.py` already routes purchases through the economy ledger.
- `game/typeclasses/property_operations_engine.py` shows the preferred style for a bounded global repeating script.
- `game/world/time.py` is the canonical time authority and should remain the source of truth for UTC/timing math.
- `game/world/bootstrap_economy.py` shows the preferred idempotent bootstrap pattern.

This starter package is intentionally shaped to fit those conventions instead of introducing a second unrelated architecture.

---

## Package contents

```text
README_BOT_HANDOFF.md
MERGE_PLAN.md

game/
  world/
    econ_automation/
      __init__.py
      constants.py
      pricing.py
      settlement.py
      rebalancer.py
      bootstrap.py
      adapters.py
  typeclasses/
    economy_automation.py
  server/
    conf/
      economy_automation_hook.py

tools/
  diff_notes.md
```

---

## Architecture summary

### 1. Domain logic in plain Python modules

Located in `game/world/econ_automation/`.

These modules do the following:

- define earning anchors and price bands
- translate `days_to_afford` into a stable credits price
- compute recurring upkeep and settlement values
- provide category adapters for shops, properties, claims, kiosks, and vehicles
- compute market balancing outputs without needing live Evennia objects everywhere

This code is meant to be easy for another bot to test and modify.

### 2. Thin Evennia integration layer

Located in `game/typeclasses/economy_automation.py`.

This file defines:

- `EconomyAutomationController` — one global script that performs bounded balancing work on a cadence
- `PassiveIncomeMixin` — optional mixin for assets that should support on-demand settlement
- helper APIs for syncing to the existing `EconomyEngine`

### 3. Bootstrap hook

Located in `game/world/econ_automation/bootstrap.py` and `game/server/conf/economy_automation_hook.py`.

This is an idempotent startup path that:

- ensures the automation controller script exists
- seeds default balancing policy
- does not overwrite live production settings unless explicitly told to

---

## Design principles

### A. Price by time, not by arbitrary raw numbers

The most stable pricing anchor for this game is:

- baseline daily income: `2000`
- strong hustle daily income: `5000`
- default blended balancing income: `3000`

A price should usually be derived from:

```text
price = target_days_to_afford * blended_daily_income * category_multiplier * region_multiplier
```

The starter package uses a blended daily income constant so one knob can rebalance large parts of the economy.

### B. Prefer on-demand settlement for passive assets

Do not give every kiosk, property, claim, and automated node its own constantly running ticker.

Instead store:

- `last_settled_iso`
- `base_daily_profit`
- `base_upkeep_daily`
- `efficiency`
- `stored_earnings`

Then resolve earnings when:

- a player inspects the asset
- a collection command is called
- a control screen is opened
- an admin rebalance pass runs

This scales much better than thousands of active timers.

### C. Keep the global balancing script small and bounded

The repeating script should not directly simulate the whole world every tick.

It should only do global work such as:

- update global economic phase
- apply soft modifier drift
- clamp runaway category multipliers
- prune queues / rotate reports
- optionally process a bounded list of flagged assets

### D. The existing `EconomyEngine` remains the ledger authority

This package does **not** replace the ledger in `typeclasses.economy.EconomyEngine`.

It should continue to be the source of truth for:

- player balances
- treasury balances
- vendor balances
- transaction recording
- final debit/credit movement

The automation layer is primarily a **policy and settlement layer**, not a second bank.

---

## Recommended merge strategy for a bot

### Phase 1 — safe additive merge

1. Copy `game/world/econ_automation/` into the live game.
2. Copy `game/typeclasses/economy_automation.py` into the live game.
3. Add a startup call to `bootstrap_economy_automation()` from a safe server-start hook.
4. Do **not** change any live vendor/property command behavior yet.

Goal of phase 1:

- make the controller exist
- make pricing functions importable
- keep runtime risk low

### Phase 2 — pricing adoption

Use the adapter functions in `adapters.py` to reprice:

- shop templates
- property listings
- claims
- kiosks
- vehicles / spacecraft

Goal of phase 2:

- unify price generation without changing settlement logic yet

### Phase 3 — passive settlement adoption

Add `PassiveIncomeMixin` to selected typeclasses or call the plain settlement helpers manually in existing typeclasses.

Best first targets:

- kiosks
- automated vendors
- rental properties
- claims with periodic output

Goal of phase 3:

- reduce live ticking complexity
- move toward a stable scalable economy loop

### Phase 4 — balancing controls and admin visibility

Expose controller state to admin commands or dashboards.

Useful next additions:

- `@econ/status`
- `@econ/reprice <category>`
- `@econ/setphase boom|stable|scarcity|recession`
- `@econ/settle <obj>`

---

## Operational model

### Price bands

The package uses these suggested effort bands:

| Band | Days to afford | Typical use |
|---|---:|---|
| trivial | 0.05 to 0.25 | food, basic supplies, entry consumables |
| light | 0.5 to 1.0 | basic gear, low-end tools |
| moderate | 2 to 5 | starter vehicles, entry kiosks |
| meaningful | 7 to 20 | apartments, claims, advanced gear |
| major | 30 to 90 | homes, industrial assets, light ships |
| elite | 120 to 240 | fleets, large properties, heavy spacecraft |
| endgame | 300+ | large territorial or capital-scale assets |

### Money sink guidance

Default sinks should be present in all profit-generating systems:

- maintenance
- labor or staffing
- fuel / power
- listing fees or transaction taxes
- repair / degradation

A healthy target is that a meaningful fraction of generated money leaves the system continuously.

### Anti-inflation policy

Use these levers before touching player base income:

1. upkeep rates
2. category scarcity multipliers
3. market saturation curves
4. payout ceilings for passive loops
5. delayed activation or buildout time for large assets

---

## Bot instructions for implementation

Another coding bot should follow these rules exactly:

1. **Do not delete or replace `typeclasses.economy.EconomyEngine`.**
2. **Do not introduce a second ledger.**
3. **Do not manually instantiate raw Django model rows for Evennia objects/scripts if Evennia creation helpers exist.**
4. **Do not attach one repeating timer per passive asset unless explicitly required.**
5. **Use `world.time.utc_now()` and ISO timestamps for time math.**
6. **Treat this package as additive and incremental.**
7. **Preserve compatibility with existing object `.db` storage.**
8. **Prefer adapter functions over broad in-place rewrites.**

---

## Data contract for passive assets

Any passive asset integrated with the settlement helpers should support these attributes, either directly or via adapters:

```python
obj.db.base_daily_profit
obj.db.base_upkeep_daily
obj.db.efficiency
obj.db.last_settled_iso
obj.db.stored_earnings
obj.db.automation_enabled
```

Optional advanced attributes:

```python
obj.db.region_multiplier
obj.db.category_multiplier
obj.db.asset_tier
obj.db.asset_kind
obj.db.inflation_sensitivity
obj.db.upkeep_override
obj.db.max_unclaimed_earnings
```

---

## Existing codebase integration notes

### Shop integration

The existing `CatalogVendor.get_shop_state_for_api()` already calls into the global economy script for price resolution. That is a strong integration point.

A bot can safely replace ad hoc price derivation for templates by calling:

- `price_shop_template(obj, ...)`
- `price_vehicle_listing(obj, ...)`

and then either:

- store the resolved price on the object for display, or
- feed it directly into UI serialization

### Property integration

The current property engine already uses a global repeating script pattern.

The safest migration path is **not** to delete it. Instead:

- keep the repeating engine for bounded orchestration
- move per-property profit/upkeep math into `world.econ_automation.settlement`
- call the settlement helper from each property’s operation tick or inspection path

### Claims and mining

Claims and mining can be high-inflation systems. Use extra caution.

Recommended policy:

- claims produce value on a cadence
- the settlement helper computes gross output from elapsed time
- the economy layer applies taxes / fees / transport / processing deductions
- claim output should hit storage or a payout buffer, not always instant free liquid credits

### Vehicles and spacecraft

The current codebase already has strong economic metadata patterns under `.db.economy`, `.db.specs`, and `.db.catalog`.

The adapter functions in this package assume those shapes and read from them instead of trying to redesign them.

---

## Acceptance criteria

A merge is successful when all of the following are true:

- server boots with the automation package installed
- `EconomyAutomationController` exists exactly once
- no duplicate ledger is introduced
- price helper imports work from both commands and typeclasses
- passive settlement helpers return stable output when called multiple times
- settlement only advances on elapsed time and updates `last_settled_iso`
- existing shop purchase flow still works
- category repricing can be done without manual price editing object-by-object

---

## Suggested follow-up work after merge

1. Add admin commands for inspection and tuning.
2. Add a JSON/CSV balancing sheet importer for category defaults.
3. Add a web/admin status page for economic phase and inflation pressure.
4. Add replay-safe audit logs for repricing passes.
5. Add unit tests around settlement drift and price band correctness.

---

## Human summary

This package gives you a clean starting point for Evennia-friendly automation that is:

- modular
- scalable
- easy to hand to another bot
- compatible with your current economy engine
- designed to support pricing and passive income systems without turning the game into a timer jungle

