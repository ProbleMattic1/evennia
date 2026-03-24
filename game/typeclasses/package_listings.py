"""
Package listings script for mining packages for sale.
"""

from typeclasses.scripts import Script


class PackageListingsScript(Script):
    """
    Global script holding mining package listings.
    db.listings = [{"package_id": int, "seller_id": int, "price": int}, ...]
    """

    def at_script_creation(self):
        if not self.db.listings:
            self.db.listings = []
