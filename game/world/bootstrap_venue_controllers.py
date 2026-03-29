"""Create tickless VenueController scripts for each venue hub. Idempotent."""

from evennia import create_script, search_script

from world.venue_resolve import hub_room_for_venue
from world.venues import VENUE_CONTROLLER_SCRIPT_TAG_CATEGORY, all_venue_ids


def bootstrap_venue_controllers():
    for venue_id in all_venue_ids():
        key = f"venue_controller__{venue_id}"
        hub = hub_room_for_venue(venue_id)
        found = search_script(key)
        if found:
            script = found[0]
        else:
            script = create_script("typeclasses.venue_controller.VenueController", key=key)
        script.db.venue_id = venue_id
        script.db.hub_dbref = hub.id if hub else None
        if venue_id:
            script.tags.add(venue_id, category=VENUE_CONTROLLER_SCRIPT_TAG_CATEGORY)
        print(f"[venue-controllers] {key} → hub_dbref={script.db.hub_dbref}")
