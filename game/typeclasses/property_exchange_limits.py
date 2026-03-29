"""
Shared limits for sovereign property exchanges (discovery + on-demand mint), per venue.
"""

# Max listable (unclaimed) parcels per venue. Discovery and impulse generation obey this per exchange.
MAX_LISTABLE_PROPERTY_LOTS_PER_VENUE = 100

# Rare prime parcel roll when generating exchange lots (discovery and random purchase).
PROPERTY_PARCEL_JACKPOT_CHANCE = 0.005
