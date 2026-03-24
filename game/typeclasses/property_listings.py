"""
Player-listed mining properties for sale on the claims market.

db.listings = [{"site_id": int, "seller_id": int, "price": int}, ...]
"""

from typeclasses.scripts import Script


class PropertyListingsScript(Script):
    def at_script_creation(self):
        if not self.db.listings:
            self.db.listings = []
