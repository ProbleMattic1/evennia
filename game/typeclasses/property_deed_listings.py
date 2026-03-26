"""
Global script: player-to-player property deed listings (hub escrow).
"""

from typeclasses.scripts import Script


class PropertyDeedListingsScript(Script):
    """
    db.listings = [{"claim_id": int, "seller_id": int, "price": int}, ...]
    """

    def at_script_creation(self):
        if not self.db.listings:
            self.db.listings = []
