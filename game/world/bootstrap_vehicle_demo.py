"""Create a tiny vehicle interaction sandbox for testing."""

from evennia import create_object, search_object

ROOM = 'typeclasses.rooms.Room'
SPACECRAFT = 'typeclasses.vehicles.Spacecraft'
CHARACTER = 'typeclasses.characters.Character'


def get_or_create_room(key, desc=''):
    found = search_object(key)
    if found:
        room = found[0]
    else:
        room = create_object(ROOM, key=key)
    if desc:
        room.db.desc = desc
    return room


def get_or_create_ship(key, location, owner=None):
    found = search_object(key)
    if found:
        ship = found[0]
    else:
        ship = create_object(SPACECRAFT, key=key, location=location)
    ship.location = location
    ship.db.owner = owner
    ship.db.allowed_boarders = [owner] if owner else []
    ship.db.fuel = 25
    ship.db.max_fuel = 25
    ship.db.specs = {
        'domain': 'space',
        'domain_slug': 'space',
        'vehicle_type': 'light_freighter',
        'vehicle_type_slug': 'light-freighter',
        'crew_min': 1,
        'crew_std': 3,
    }
    ship.db.combat = {'hp': 120}
    ship.db.economy = {'total_price_cr': 150000}
    ship.db.catalog = {'vehicle_id': 'DEMO-SPARROW-MKV'}
    ship.db.desc = 'A compact starter freighter set up for local runs.'
    return ship


def update_owned_vehicles(owner, ship):
    if not owner:
        return
    owned = owner.db.owned_vehicles or []
    if ship not in owned:
        owned.append(ship)
    owner.db.owned_vehicles = owned


def run():
    shipyard = get_or_create_room('Meridian Civil Shipyard', 'A polished commercial yard with bright sales signage.')
    hangar = get_or_create_room('Meridian Delivery Hangar', 'A secure hangar for newly delivered or registered ships.')
    orbit = get_or_create_room('Low Meridian Orbit', 'A quiet orbital lane above Meridian with room for maneuvering.')

    character = None
    # optional convenience: first available Character gets starter ownership
    try:
        chars = [obj for obj in search_object('#1') if isinstance(obj, object)]
        if chars:
            character = chars[0]
    except Exception:
        character = None

    ship = get_or_create_ship('Sparrow Mk V', hangar, owner=character)
    if character:
        update_owned_vehicles(character, ship)
        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        acct = econ.get_character_account(character)
        econ.ensure_account(acct, opening_balance=int(character.db.credits or 0))
        target = max(econ.get_balance(acct), 500_000)
        econ.set_balance(acct, target)
        character.db.credits = econ.get_balance(acct)

    print('Created/updated rooms: Meridian Civil Shipyard, Meridian Delivery Hangar, Low Meridian Orbit')
    print('Created/updated demo ship: Sparrow Mk V')
