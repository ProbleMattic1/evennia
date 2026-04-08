"""
Stationary mining scanner — deploy in a mine room to run geological surveys (see world.mining_survey_ops).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from evennia.objects.objects import DefaultObject

from typeclasses.objects import ObjectParent

if TYPE_CHECKING:
    pass


class MiningScanner(ObjectParent, DefaultObject):
    def at_object_creation(self):
        self.db.owner = None
        self.db.is_deployed = False
        self.db.deploy_site_ref = None
        self.tags.add("mining_scanner", category="mining")
        self.tags.add("tool", category="inventory")
        self.locks.add("get:true();drop:true();give:true()")

    def deploy_at_site(self, character, site):
        """Move scanner into the site's room and bind to this MiningSite."""
        if not site or not site.tags.has("mining_site", category="mining"):
            raise ValueError("Not a mining site.")
        room = site.location
        if not room:
            raise ValueError("Site has no room.")
        if self.db.owner not in (None, character):
            raise ValueError("Not your scanner.")
        self.db.owner = character
        self.db.deploy_site_ref = site
        self.db.is_deployed = True
        self.move_to(room, quiet=True)
        self.home = room
        self.locks.add("get:false()")

    def undeploy_to_inventory(self, character):
        if self.db.owner != character:
            raise ValueError("Not your scanner.")
        self.db.is_deployed = False
        self.db.deploy_site_ref = None
        self.move_to(character, quiet=True)
        self.home = character
        self.locks.add("get:true();drop:true();give:true()")
