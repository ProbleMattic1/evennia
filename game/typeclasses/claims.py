"""
Mining claims — tradeable deeds entitling the bearer to deploy at a site.
Deploy consumes the claim. Undeploy does not return a claim.
"""

from .objects import Object


class MiningClaim(Object):
    """Deed to deploy at a specific mining site. Tradeable."""

    def at_object_creation(self):
        self.db.site_ref = None
        self.db.site_key = None
        self.db.is_jackpot = False
        self.tags.add("mining_claim", category="mining")
        self.locks.add("get:true();drop:true();give:true()")
