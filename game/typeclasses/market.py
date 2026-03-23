"""
Global market script for game-wide commodity prices.
"""

import random

from .scripts import Script


class MarketScript(Script):
    """
    Tracks and updates global market prices.
    Access via: from evennia import GLOBAL_SCRIPTS; GLOBAL_SCRIPTS.market
    """

    def at_script_creation(self):
        self.key = "market"
        self.desc = "Handles game-wide market prices."
        self.persistent = True
        if not hasattr(self, "interval") or self.interval <= 0:
            self.interval = 3600
        if not hasattr(self, "repeats") or self.repeats is None:
            self.repeats = 0
        self.db.prices = self.db.prices or {
            "wheat": 10,
            "iron": 50,
            "gems": 500,
        }

    def at_repeat(self, **kwargs):
        prices = self.db.prices or {}
        for item in list(prices.keys()):
            change = random.randint(-2, 2)
            prices[item] = max(1, prices.get(item, 1) + change)
        self.db.prices = prices

    def get_price(self, commodity):
        return (self.db.prices or {}).get(commodity, 0)
