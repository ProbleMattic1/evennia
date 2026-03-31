# Diff Notes for a Bot

## Intended insertion points

### 1. Startup/bootstrap

Find the existing cold-start/bootstrap chain and add:

```python
from game.server.conf.economy_automation_hook import ensure_economy_automation
ensure_economy_automation()
```

### 2. Shop price calls

Where shop UI or purchase flows currently derive a price, consider replacing the display-time price with calls into:

- `world.econ_automation.adapters.price_shop_template`
- `world.econ_automation.adapters.price_vehicle_listing`

### 3. Passive assets

For any object that already behaves like a passive producer, either:

- subclass `PassiveIncomeMixin`, or
- call `settle_passive_income_asset(obj, ...)` from its existing update path

### 4. Property engine

Do not delete the current property operations script.

Instead move per-holding math into the settlement helper and call it from the property typeclass or operation handler.
