"""Procedural exchange lots; tag exchange_listing for discovery-spawned rows."""

import random

from evennia import create_object, search_object, search_tag

from typeclasses.property_exchange_limits import PROPERTY_PARCEL_JACKPOT_CHANCE
from typeclasses.property_lots import ZONE_LABELS

from world.venues import apply_venue_metadata, get_venue

# Minimum tier for discovery-spawned exchange lots (1 = Starter … 3 = Prime).
MIN_EXCHANGE_TIER = 2
MAX_EXCHANGE_TIER = 3

PARCEL_PREFIXES = [
    "Aurora", "Civic", "Crown", "District", "Eclipse", "Founders", "Gridline",
    "Harbor", "Horizon", "Meridian", "Metro", "Nova", "Orbit", "Pinnacle",
    "Quorum", "Riverside", "Skygate", "Station", "Summit", "Vector", "Vista",
]

PARCEL_SUFFIXES = [
    "Annex", "Arcade", "Block", "Commons", "Court", "Enclave", "Exchange",
    "Gardens", "Landing", "Lot", "Park", "Pier", "Plaza", "Point", "Quarter",
    "Reach", "Row", "Terrace", "Tract", "Yard", "Zone",
]


def _existing_property_lot_keys():
    return {obj.key for obj in search_tag("property_lot", category="realty")}


def _pick_unique_lot_key(zone):
    letter = (zone or "r")[0].upper()
    existing = _existing_property_lot_keys()
    for _ in range(80):
        stem = f"{random.choice(PARCEL_PREFIXES)} {random.choice(PARCEL_SUFFIXES)}"
        key = f"Parcel {letter}-{stem}"
        if key not in existing:
            return key
    for _ in range(40):
        key = f"Parcel {letter}-{random.randint(10000, 999999)}"
        if key not in existing:
            return key
    return f"Parcel {letter}-{random.randint(1, 9999999)}"


def _random_tier_and_size():
    tier = random.randint(MIN_EXCHANGE_TIER, MAX_EXCHANGE_TIER)
    if tier == 2:
        size = random.randint(2, 3)
    else:
        size = random.randint(3, 5)
    return tier, size


def generate_market_property_lot(zone, *, roll_jackpot=True, venue_id="nanomega_core"):
    """
    Procedural exchange lot. If ``roll_jackpot`` is True, small chance to force a prime parcel.
    """
    zone = (zone or "residential").lower()
    if zone not in ZONE_LABELS:
        zone = "residential"

    office_key = get_venue(venue_id)["realty"]["office_key"]
    found = search_object(office_key)
    assert found, f"realty office {office_key!r} missing for venue {venue_id!r}"
    room = found[0]
    apply_venue_metadata(room, venue_id)

    jackpot = roll_jackpot and (random.random() < PROPERTY_PARCEL_JACKPOT_CHANCE)
    if jackpot:
        tier = MAX_EXCHANGE_TIER
        size_units = random.randint(4, 6)
    else:
        tier, size_units = _random_tier_and_size()
    key = _pick_unique_lot_key(zone)

    lot = create_object(
        "typeclasses.property_lots.PropertyLot",
        key=key,
        location=room,
        home=room,
    )
    lot.db.lot_tier = tier
    lot.db.zone = zone
    lot.db.size_units = size_units
    label = get_venue(venue_id).get("label") or venue_id
    lot.db.desc = (
        f"Exchange-listed {zone} parcel (Tier {tier}, {size_units} units). "
        f"Survey complete; title available through {label} Real Estate."
    )
    if jackpot:
        lot.db.desc += " ★ Prime exchange listing — exceptional footprint. ★"
    lot.tags.add("exchange_listing", category="realty")
    return lot
