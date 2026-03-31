# Merge Plan

## Overview

This is the concrete merge order for applying the starter package to the current game.

## Step 1 — Copy files

Copy these into the live game package:

- `game/world/econ_automation/*`
- `game/typeclasses/economy_automation.py`
- `game/server/conf/economy_automation_hook.py`

## Step 2 — Add the startup hook

In the game’s preferred cold-start path, import and call:

```python
from game.server.conf.economy_automation_hook import ensure_economy_automation
ensure_economy_automation()
```

If there is already an idempotent startup bootstrap chain, add it there instead of creating a second startup mechanism.

## Step 3 — Verify boot

Expected result:

- one script with key `economy_automation_controller`
- `global_economy` still present
- no exceptions from imports

## Step 4 — Start using the pricing adapters

Target these first:

- shops
- property listings
- shipyard catalog
- claims market

## Step 5 — Start using passive settlement

Target these first:

- kiosks
- automated vendors
- rental properties
- passive claims

## Step 6 — Add observability

Recommended small admin command set:

- economy status
- category repricing dry-run
- force settle object
- set global phase

