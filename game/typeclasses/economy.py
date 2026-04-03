"""
Economy Engine v1 for an Evennia-based RPG.

Design goals:
- Keep the canonical economy state in one global Script.
- Support base prices, category/domain modifiers, faction modifiers,
  and location/shop modifiers.
- Work cleanly with imported vehicle objects that already store their
  economy data in obj.db.economy and classification data in obj.db.specs.
- Provide a small API that can be called from commands, shops, scripts,
  and batchcode.

Suggested bootstrap:
    from evennia import create_script
    create_script("typeclasses.economy.EconomyEngine")

Suggested lookup:
    from typeclasses.economy import get_economy
    econ = get_economy()
    price = econ.get_final_price(vehicle, buyer=caller, location=caller.location)
"""

from copy import deepcopy
from datetime import UTC, datetime

from evennia import GLOBAL_SCRIPTS, search_script

from .scripts import Script


DEFAULT_ECONOMY_STATE = {
    "version": 1,
    "currency": "credits",
    "rounding_mode": "nearest_int",
    "global_modifier": 1.0,
    "buy_rate": 1.00,
    "sell_rate": 0.45,
    "black_market_buy_rate": 1.35,
    "black_market_sell_rate": 0.70,
    "scarcity_floor": 0.60,
    "scarcity_ceiling": 1.80,
    "default_tax_rate": 0.00,
    "category_modifiers": {
        # values are multiplicative
        "vehicle": 1.00,
        "surface_vehicle": 1.00,
        "watercraft": 1.05,
        "aircraft": 1.12,
        "spacecraft": 1.30,
    },
    "domain_modifiers": {
        "surface": 1.00,
        "water": 1.04,
        "air": 1.10,
        "space": 1.28,
    },
    "rarity_modifiers": {
        "common": 1.00,
        "uncommon": 1.10,
        "rare": 1.30,
        "very-rare": 1.55,
        "legendary": 2.10,
    },
    "legal_class_modifiers": {
        "open": 1.00,
        "licensed": 1.08,
        "restricted": 1.25,
        "military": 1.50,
        "prohibited": 2.10,
    },
    "faction_modifiers": {
        # seller/buyer friendly faction examples; override in game data
        "civilian": 1.00,
        "corporate": 1.08,
        "government": 1.05,
        "black-market": 1.40,
        "pirate": 1.18,
    },
    "standing_bands": {
        # standing score thresholds -> discount/premium modifiers
        "ally": 0.90,
        "friendly": 0.96,
        "neutral": 1.00,
        "unfriendly": 1.10,
        "hostile": 1.30,
    },
    "regional_modifiers": {},
    "location_modifiers": {},
    "item_overrides": {},
}


class EconomyEngine(Script):
    """
    Global economy controller.

    Persistent state lives on `self.db.state`.
    Volatile caches can live on `self.ndb` if needed later.
    """

    def at_script_creation(self):
        self.key = "global_economy"
        self.desc = "Global economy controller for market pricing."
        self.interval = 0
        self.persistent = True
        self.start_delay = False
        self.db.state = deepcopy(DEFAULT_ECONOMY_STATE)
        self.db.price_history = {}
        self.db.last_tick = None
        self.db.accounts = {}
        self.db.transactions = []
        self.db.tax_pool = 0

    # -----------------------------
    # Basic state helpers
    # -----------------------------

    @property
    def state(self):
        return self.db.state or deepcopy(DEFAULT_ECONOMY_STATE)

    def save_state(self, new_state):
        self.db.state = new_state
        return self.db.state

    def reset_defaults(self):
        self.db.state = deepcopy(DEFAULT_ECONOMY_STATE)
        return self.db.state

    def get_modifier_table(self, table_name):
        return (self.state or {}).get(table_name, {}) or {}

    def set_modifier(self, table_name, key, value):
        state = deepcopy(self.state)
        state.setdefault(table_name, {})[str(key)] = float(value)
        self.save_state(state)
        return state[table_name][str(key)]

    def remove_modifier(self, table_name, key):
        state = deepcopy(self.state)
        table = state.setdefault(table_name, {})
        table.pop(str(key), None)
        self.save_state(state)

    def set_global_modifier(self, value):
        state = deepcopy(self.state)
        state["global_modifier"] = float(value)
        self.save_state(state)
        return state["global_modifier"]

    # -----------------------------
    # Ledger helpers
    # -----------------------------

    def ensure_account(self, account_key, opening_balance=0):
        """
        Create ``account_key`` in the ledger if missing, seeded with ``opening_balance``.

        If the account already exists, the balance is left unchanged; ``opening_balance``
        applies only on first creation.
        """
        accounts = self.db.accounts or {}
        if account_key not in accounts:
            accounts[account_key] = int(opening_balance or 0)
            self.db.accounts = accounts
        return accounts[account_key]

    def get_balance(self, account_key):
        return int((self.db.accounts or {}).get(str(account_key), 0))

    def set_balance(self, account_key, amount):
        accounts = self.db.accounts or {}
        accounts[str(account_key)] = int(amount)
        self.db.accounts = accounts
        return accounts[str(account_key)]

    def deposit(self, account_key, amount, memo=""):
        amount = int(amount or 0)
        if amount < 0:
            raise ValueError("deposit amount must be >= 0")
        new_balance = self.get_balance(account_key) + amount
        self.set_balance(account_key, new_balance)
        self.record_transaction(
            tx_type="deposit",
            amount=amount,
            to_account=account_key,
            memo=memo,
        )
        return new_balance

    def withdraw(self, account_key, amount, memo=""):
        amount = int(amount or 0)
        if amount < 0:
            raise ValueError("withdraw amount must be >= 0")
        current = self.get_balance(account_key)
        if current < amount:
            raise ValueError(f"insufficient funds in {account_key}")
        new_balance = current - amount
        self.set_balance(account_key, new_balance)
        self.record_transaction(
            tx_type="withdraw",
            amount=amount,
            from_account=account_key,
            memo=memo,
        )
        return new_balance

    def transfer(self, from_account, to_account, amount, memo="", *, tx_type=None, extra=None):
        amount = int(amount or 0)
        if amount < 0:
            raise ValueError("transfer amount must be >= 0")
        if amount == 0:
            return {
                "from_balance": self.get_balance(from_account),
                "to_balance": self.get_balance(to_account),
            }
        current = self.get_balance(from_account)
        if current < amount:
            raise ValueError(f"insufficient funds in {from_account}")
        self.set_balance(from_account, current - amount)
        self.set_balance(to_account, self.get_balance(to_account) + amount)
        self.record_transaction(
            tx_type=tx_type or "transfer",
            amount=amount,
            from_account=from_account,
            to_account=to_account,
            memo=memo,
            extra=extra,
        )
        return {
            "from_balance": self.get_balance(from_account),
            "to_balance": self.get_balance(to_account),
        }

    def record_transaction(self, tx_type, amount, from_account=None, to_account=None, memo="", extra=None):
        ledger = self.db.transactions or []
        ledger.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "type": tx_type,
            "amount": int(amount or 0),
            "from_account": from_account,
            "to_account": to_account,
            "memo": memo,
            "extra": extra or {},
        })
        self.db.transactions = ledger
        return ledger[-1]

    def get_character_account(self, character):
        return f"player:{character.id}"

    def get_character_balance(self, character):
        """
        Ledger balance for this character. ``character.db.credits`` is used only as
        ``opening_balance`` when the player account is first created; afterward the
        ledger is authoritative.
        """
        account_key = self.get_character_account(character)
        opening = int(character.db.credits or 0)
        self.ensure_account(account_key, opening_balance=opening)
        return self.get_balance(account_key)

    def sync_character_balance(self, character):
        balance = self.get_character_balance(character)
        character.db.credits = balance
        return balance

    def get_vendor_account(self, vendor_id):
        return f"vendor:{vendor_id}"

    def get_treasury_account(self, bank_id="alpha-prime"):
        return f"treasury:{bank_id}"

    def record_miner_treasury_payout(
        self, amount: int, *, gross: int = 0, fee: int = 0
    ) -> None:
        """
        Track credits paid from treasury to a player for miner settlement
        (plant raw purchase, refined collect). Bucketed by epoch-aligned
        ``MINING_DELIVERY_PERIOD`` slots (same grid as mining delivery UI).

        ``amount`` is net paid to the miner. Optional ``gross`` / ``fee`` track
        settlement face value and retained fees for web totals (gross − fee ≈ net).
        """
        from world.time import MINING_DELIVERY_PERIOD, floor_period, utc_now, to_iso

        amount = int(amount or 0)
        if amount <= 0:
            return
        gross = max(0, int(gross or 0))
        fee = max(0, int(fee or 0))
        slot_iso = to_iso(floor_period(utc_now(), MINING_DELIVERY_PERIOD)) or ""
        cur_slot = getattr(self.db, "miner_payout_current_slot_start_iso", None) or ""
        if cur_slot != slot_iso:
            self.db.miner_payout_last_cycle_cr = int(
                getattr(self.db, "miner_payout_this_slot_cr", 0) or 0
            )
            self.db.miner_payout_this_slot_cr = 0
            self.db.miner_payout_current_slot_start_iso = slot_iso
            self.db.miner_settlement_gross_last_cycle_cr = int(
                getattr(self.db, "miner_settlement_gross_this_slot_cr", 0) or 0
            )
            self.db.miner_settlement_fees_last_cycle_cr = int(
                getattr(self.db, "miner_settlement_fees_this_slot_cr", 0) or 0
            )
            self.db.miner_settlement_gross_this_slot_cr = 0
            self.db.miner_settlement_fees_this_slot_cr = 0
        self.db.miner_payout_this_slot_cr = int(
            getattr(self.db, "miner_payout_this_slot_cr", 0) or 0
        ) + amount
        self.db.miner_payout_total_cr = int(
            getattr(self.db, "miner_payout_total_cr", 0) or 0
        ) + amount
        self.db.miner_settlement_gross_this_slot_cr = int(
            getattr(self.db, "miner_settlement_gross_this_slot_cr", 0) or 0
        ) + gross
        self.db.miner_settlement_fees_this_slot_cr = int(
            getattr(self.db, "miner_settlement_fees_this_slot_cr", 0) or 0
        ) + fee
        self.db.miner_settlement_gross_total_cr = int(
            getattr(self.db, "miner_settlement_gross_total_cr", 0) or 0
        ) + gross
        self.db.miner_settlement_fees_total_cr = int(
            getattr(self.db, "miner_settlement_fees_total_cr", 0) or 0
        ) + fee

    def get_miner_payout_totals_for_web(self) -> tuple[int, int]:
        """(credits in last *completed* mining slot, all-time treasury miner payouts)."""
        last = int(getattr(self.db, "miner_payout_last_cycle_cr", 0) or 0)
        total = int(getattr(self.db, "miner_payout_total_cr", 0) or 0)
        return last, total

    def get_miner_settlement_value_totals_for_web(self) -> tuple[int, int, int, int]:
        """
        (last_slot_gross, last_slot_fees, all_time_gross, all_time_fees) in cr.
        Last-slot values are for the previous completed mining UTC slot.
        """
        lg = int(getattr(self.db, "miner_settlement_gross_last_cycle_cr", 0) or 0)
        lf = int(getattr(self.db, "miner_settlement_fees_last_cycle_cr", 0) or 0)
        tg = int(getattr(self.db, "miner_settlement_gross_total_cr", 0) or 0)
        tf = int(getattr(self.db, "miner_settlement_fees_total_cr", 0) or 0)
        return lg, lf, tg, tf

    def get_miner_settlement_this_slot_for_web(self) -> tuple[int, int, int]:
        """
        (net_to_miners, gross_face_value, fees_retained) for the in-progress
        mining UTC slot — updates as settlements occur; same grid as web clock.
        """
        net = int(getattr(self.db, "miner_payout_this_slot_cr", 0) or 0)
        g = int(getattr(self.db, "miner_settlement_gross_this_slot_cr", 0) or 0)
        f = int(getattr(self.db, "miner_settlement_fees_this_slot_cr", 0) or 0)
        return net, g, f

    # -----------------------------
    # Price extraction helpers
    # -----------------------------

    def get_base_price(self, item):
        """
        Determine an item's canonical base price.

        Priority:
        1. obj.db.economy['total_price_cr']
        2. obj.db.economy['base_price_cr']
        3. obj.db.price
        4. obj.db.base_price
        """
        if not item:
            return 0

        economy = getattr(item.db, "economy", None) or {}
        for key in ("total_price_cr", "base_price_cr"):
            value = economy.get(key)
            if isinstance(value, (int, float)):
                return value

        for attr in ("price", "base_price"):
            value = getattr(item.db, attr, None)
            if isinstance(value, (int, float)):
                return value

        return 0

    def get_item_key(self, item):
        catalog = getattr(item.db, "catalog", None) or {}
        return catalog.get("vehicle_id") or item.key

    def get_item_category(self, item):
        return getattr(item.db, "vehicle_kind", None) or "vehicle"

    def get_item_domain(self, item):
        specs = getattr(item.db, "specs", None) or {}
        return specs.get("domain_slug") or specs.get("domain")

    def get_item_rarity(self, item):
        economy = getattr(item.db, "economy", None) or {}
        return economy.get("rarity_slug") or economy.get("rarity")

    def get_item_legal_class(self, item):
        economy = getattr(item.db, "economy", None) or {}
        return economy.get("legal_class_slug") or economy.get("legal_class")

    def get_item_faction(self, item):
        catalog = getattr(item.db, "catalog", None) or {}
        lore = getattr(item.db, "lore", None) or {}
        return (
            catalog.get("primary_faction_slug")
            or lore.get("primary_faction_slug")
            or lore.get("primary_faction")
        )

    # -----------------------------
    # Context resolution helpers
    # -----------------------------

    def get_location_modifier(self, location=None):
        if not location:
            return 1.0

        # direct object override wins
        explicit = getattr(location.db, "price_modifier", None)
        if isinstance(explicit, (int, float)):
            return float(explicit)

        # then named location override by key/id/tag
        table = self.get_modifier_table("location_modifiers")
        candidates = [str(location.key)]
        if getattr(location.db, "location_id", None):
            candidates.append(str(location.db.location_id))
        for cand in candidates:
            if cand in table:
                return float(table[cand])
        return 1.0

    def get_region_modifier(self, location=None):
        if not location:
            return 1.0

        region = getattr(location.db, "region", None) or getattr(location.db, "market_region", None)
        if not region:
            return 1.0
        return float(self.get_modifier_table("regional_modifiers").get(str(region), 1.0))

    def get_faction_modifier(self, faction_key=None):
        if not faction_key:
            return 1.0
        return float(self.get_modifier_table("faction_modifiers").get(str(faction_key), 1.0))

    def get_standing_modifier(self, standing="neutral"):
        return float(self.get_modifier_table("standing_bands").get(str(standing), 1.0))

    def get_tax_rate(self, location=None):
        explicit = getattr(getattr(location, "db", None), "tax_rate", None) if location else None
        if isinstance(explicit, (int, float)):
            return float(explicit)
        return float(self.state.get("default_tax_rate", 0.0))

    def get_scarcity_modifier(self, item=None, location=None):
        """
        Scarcity can come from location state or item state.
        Expected values are multiplicative, such as 0.85 or 1.25.
        """
        scarcity = None

        if location:
            scarcity = getattr(location.db, "scarcity_modifier", None)
        if scarcity is None and item:
            scarcity = getattr(item.db, "scarcity_modifier", None)
        if scarcity is None:
            scarcity = 1.0

        try:
            scarcity = float(scarcity)
        except (TypeError, ValueError):
            scarcity = 1.0

        floor = float(self.state.get("scarcity_floor", 0.60))
        ceil = float(self.state.get("scarcity_ceiling", 1.80))
        return max(floor, min(ceil, scarcity))

    # -----------------------------
    # Price computation
    # -----------------------------

    def get_item_override(self, item):
        item_key = self.get_item_key(item)
        return self.get_modifier_table("item_overrides").get(str(item_key))

    def get_buy_sell_rate(self, market_type="normal", transaction_type="buy"):
        if market_type == "black_market":
            return float(self.state.get(
                "black_market_buy_rate" if transaction_type == "buy" else "black_market_sell_rate", 1.0
            ))
        return float(self.state.get("buy_rate" if transaction_type == "buy" else "sell_rate", 1.0))

    def get_final_price(self, item, buyer=None, seller=None, location=None,
                        market_type="normal", transaction_type="buy", standing="neutral"):
        base_price = float(self.get_base_price(item) or 0)
        if base_price <= 0:
            return 0

        override = self.get_item_override(item)
        if isinstance(override, (int, float)):
            base_price = float(override)

        global_mod = float(self.state.get("global_modifier", 1.0))
        category_mod = float(self.get_modifier_table("category_modifiers").get(self.get_item_category(item), 1.0))
        domain_mod = float(self.get_modifier_table("domain_modifiers").get(self.get_item_domain(item), 1.0))
        rarity_mod = float(self.get_modifier_table("rarity_modifiers").get(self.get_item_rarity(item), 1.0))
        legal_mod = float(self.get_modifier_table("legal_class_modifiers").get(self.get_item_legal_class(item), 1.0))
        faction_mod = float(self.get_faction_modifier(self.get_item_faction(item)))
        region_mod = float(self.get_region_modifier(location))
        location_mod = float(self.get_location_modifier(location))
        scarcity_mod = float(self.get_scarcity_modifier(item=item, location=location))
        standing_mod = float(self.get_standing_modifier(standing))
        buy_sell_mod = float(self.get_buy_sell_rate(market_type=market_type, transaction_type=transaction_type))

        subtotal = (
            base_price
            * global_mod
            * category_mod
            * domain_mod
            * rarity_mod
            * legal_mod
            * faction_mod
            * region_mod
            * location_mod
            * scarcity_mod
            * standing_mod
            * buy_sell_mod
        )

        tax_rate = self.get_tax_rate(location=location)
        if transaction_type == "buy" and tax_rate:
            subtotal *= (1.0 + tax_rate)

        rounding_mode = self.state.get("rounding_mode", "nearest_int")
        if rounding_mode == "floor":
            final = int(subtotal)
        elif rounding_mode == "ceil":
            final = int(subtotal) if subtotal == int(subtotal) else int(subtotal) + 1
        else:
            final = int(round(subtotal))
        return max(final, 0)

    def get_price_breakdown(self, item, buyer=None, seller=None, location=None,
                            market_type="normal", transaction_type="buy", standing="neutral"):
        base_price = float(self.get_base_price(item) or 0)
        return {
            "base_price": base_price,
            "global_modifier": float(self.state.get("global_modifier", 1.0)),
            "category_modifier": float(self.get_modifier_table("category_modifiers").get(self.get_item_category(item), 1.0)),
            "domain_modifier": float(self.get_modifier_table("domain_modifiers").get(self.get_item_domain(item), 1.0)),
            "rarity_modifier": float(self.get_modifier_table("rarity_modifiers").get(self.get_item_rarity(item), 1.0)),
            "legal_class_modifier": float(self.get_modifier_table("legal_class_modifiers").get(self.get_item_legal_class(item), 1.0)),
            "faction_modifier": float(self.get_faction_modifier(self.get_item_faction(item))),
            "regional_modifier": float(self.get_region_modifier(location)),
            "location_modifier": float(self.get_location_modifier(location)),
            "scarcity_modifier": float(self.get_scarcity_modifier(item=item, location=location)),
            "standing_modifier": float(self.get_standing_modifier(standing)),
            "buy_sell_modifier": float(self.get_buy_sell_rate(market_type=market_type, transaction_type=transaction_type)),
            "tax_rate": float(self.get_tax_rate(location=location)),
            "market_type": market_type,
            "transaction_type": transaction_type,
            "standing": standing,
            "final_price": self.get_final_price(
                item,
                buyer=buyer,
                seller=seller,
                location=location,
                market_type=market_type,
                transaction_type=transaction_type,
                standing=standing,
            ),
        }

    # -----------------------------
    # Optional simple market tick
    # -----------------------------

    def apply_market_shift(self, scope="global", key=None, pct_change=0.0):
        """
        A simple manual tuning helper for v1.
        pct_change is additive against an existing multiplier:
            current 1.00 + pct_change 0.10 => 1.10
        """
        if scope == "global":
            current = float(self.state.get("global_modifier", 1.0))
            return self.set_global_modifier(max(0.01, current + float(pct_change)))

        scope_map = {
            "region": "regional_modifiers",
            "location": "location_modifiers",
            "faction": "faction_modifiers",
            "item": "item_overrides",
        }
        table_name = scope_map.get(scope)
        if not table_name or key is None:
            raise ValueError("Unsupported scope or missing key.")

        table = self.get_modifier_table(table_name)
        current = float(table.get(str(key), 1.0))
        return self.set_modifier(table_name, key, max(0.01, current + float(pct_change)))


# -----------------------------
# Module-level convenience helpers
# -----------------------------

def get_economy(create_missing=True):
    """
    Find the global economy script.
    """
    try:
        econ = GLOBAL_SCRIPTS.global_economy
        if econ:
            return econ
    except Exception:
        pass

    found = search_script("global_economy")
    if found:
        return found[0]

    if create_missing:
        from evennia import create_script
        return create_script("typeclasses.economy.EconomyEngine")
    return None


def grant_character_credits(character, amount, memo="grant"):
    """
    Deposit credits into the character's ledger account and refresh ``character.db.credits``.
    """
    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(character)
    econ.ensure_account(acct, opening_balance=int(character.db.credits or 0))
    econ.deposit(acct, int(amount), memo=memo)
    character.db.credits = econ.get_balance(acct)
    return character.db.credits


def get_price(item, location=None, market_type="normal", transaction_type="buy", standing="neutral"):
    econ = get_economy(create_missing=True)
    return econ.get_final_price(
        item,
        location=location,
        market_type=market_type,
        transaction_type=transaction_type,
        standing=standing,
    )
