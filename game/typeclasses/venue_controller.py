"""Tickless script: records venue_id and hub dbref for admin / future schedulers."""

from evennia.scripts.scripts import DefaultScript

from world.venues import VENUE_CONTROLLER_SCRIPT_TAG_CATEGORY


class VenueController(DefaultScript):
    def at_script_creation(self):
        self.persistent = True
        self.interval = 0
        self.start_delay = False
        if self.db.venue_id is None:
            self.db.venue_id = None
        if self.db.hub_dbref is None:
            self.db.hub_dbref = None

    def at_start(self):
        vid = self.db.venue_id
        if vid:
            self.tags.add(vid, category=VENUE_CONTROLLER_SCRIPT_TAG_CATEGORY)
