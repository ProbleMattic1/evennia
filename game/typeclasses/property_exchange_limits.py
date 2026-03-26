"""
Shared limits for the sovereign property exchange (discovery + on-demand mint).
"""

# Max listable (unclaimed) parcels worldwide. Discovery and impulse generation both obey this.
MAX_LISTABLE_PROPERTY_LOTS = 100

# Rare prime parcel roll when generating exchange lots (discovery and random purchase).
PROPERTY_PARCEL_JACKPOT_CHANCE = 0.005
