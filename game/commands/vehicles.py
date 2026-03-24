"""
Vehicle interaction commands v2.

Adds a lightweight but playable vehicle loop:
- board/enter a vehicle you own or have access to
- exit/disembark back to the exterior room
- take or release the pilot seat
- move the vehicle between rooms while piloting
- list owned vehicles
"""

from evennia import search_object
from commands.command import Command


class VehicleCommandMixin:
    def _find_vehicle_here_or_inside(self, caller, name):
        name = (name or '').strip()
        if not name:
            return None

        # if caller is inside a vehicle, first allow matching that vehicle
        current = caller.location
        if current and getattr(current.db, 'is_vehicle', False):
            if current.key.lower() == name.lower():
                return current
            found = caller.search(name, location=current.location, quiet=True)
            if found:
                return found[0]

        found = caller.search(name, location=caller.location, quiet=True)
        if found:
            return found[0]
        return None

    def _current_vehicle(self, caller):
        loc = caller.location
        if loc and getattr(loc.db, 'is_vehicle', False):
            return loc
        return None


class CmdBoardVehicle(VehicleCommandMixin, Command):
    """
    Board a vehicle.

    Usage:
      board <vehicle>
      enter <vehicle>
    """

    key = 'board'
    aliases = ['enter']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg('Board what?')
            return

        if self._current_vehicle(caller):
            caller.msg('You are already inside a vehicle. Use |wexit|n first.')
            return

        vehicle = self._find_vehicle_here_or_inside(caller, self.args)
        if not vehicle:
            return
        if not getattr(vehicle.db, 'is_vehicle', False):
            caller.msg(f'{vehicle.key} is not a vehicle.')
            return
        ok, reason = vehicle.can_board(caller)
        if not ok:
            caller.msg(reason)
            return

        old_location = caller.location
        caller.location = vehicle
        vehicle.at_board(caller, old_location=old_location)
        caller.msg(f'You board |w{vehicle.key}|n.')
        if old_location:
            old_location.msg_contents(f'{caller.key} boards {vehicle.key}.', exclude=caller)
        vehicle.msg_contents(f'{caller.key} comes aboard.', exclude=caller)
        caller.msg(vehicle.get_interior_appearance(caller))


class CmdExitVehicle(VehicleCommandMixin, Command):
    """
    Exit the vehicle you are currently inside.

    Usage:
      exit
      disembark
    """

    key = 'exit'
    aliases = ['disembark', 'leavevehicle']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You are not inside a vehicle.')
            return

        exterior = vehicle.get_exterior_location()
        if not exterior:
            caller.msg('This vehicle has nowhere safe to exit to.')
            return

        if vehicle.db.pilot == caller:
            vehicle.db.pilot = None
            caller.msg('You release the pilot controls as you leave.')

        caller.location = exterior
        vehicle.at_disembark(caller, new_location=exterior)
        caller.msg(f'You exit |w{vehicle.key}|n.')
        vehicle.msg_contents(f'{caller.key} disembarks.', exclude=caller)
        exterior.msg_contents(f'{caller.key} exits {vehicle.key}.', exclude=caller)


class CmdPilotVehicle(VehicleCommandMixin, Command):
    """
    Take control of a vehicle.

    Usage:
      pilot
      pilot <vehicle>
    """

    key = 'pilot'
    aliases = ['helm', 'drive', 'fly', 'sail']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle and self.args:
            vehicle = self._find_vehicle_here_or_inside(caller, self.args)
            if vehicle and getattr(vehicle.db, 'is_vehicle', False):
                ok, reason = vehicle.can_board(caller)
                if not ok:
                    caller.msg(reason)
                    return
                old_location = caller.location
                caller.location = vehicle
                vehicle.at_board(caller, old_location=old_location)

        if not vehicle:
            caller.msg('You must be inside a vehicle to pilot it.')
            return

        ok, reason = vehicle.can_pilot(caller)
        if not ok:
            caller.msg(reason)
            return

        current_pilot = vehicle.db.pilot
        if current_pilot and current_pilot != caller:
            caller.msg(f'{current_pilot.key} is already piloting this vehicle.')
            return

        vehicle.db.pilot = caller
        caller.msg(f'You take the pilot seat of |w{vehicle.key}|n.')
        vehicle.msg_contents(f'{caller.key} takes the pilot seat.', exclude=caller)


class CmdUnpilotVehicle(VehicleCommandMixin, Command):
    """
    Release the pilot seat.

    Usage:
      unpilot
      standdown
    """

    key = 'unpilot'
    aliases = ['standdown', 'releasehelm']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You are not inside a vehicle.')
            return
        if vehicle.db.pilot != caller:
            caller.msg('You are not the current pilot.')
            return
        vehicle.db.pilot = None
        caller.msg(f'You release the pilot seat of |w{vehicle.key}|n.')
        vehicle.msg_contents(f'{caller.key} steps away from the pilot controls.', exclude=caller)


class CmdVehicleTravel(VehicleCommandMixin, Command):
    """
    Move your current vehicle to another room.

    Usage:
      travel <destination room>
      goto <destination room>
      course <destination room>
    """

    key = 'travel'
    aliases = ['goto', 'course', 'launch', 'movevehicle']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg('Travel where?')
            return

        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You must be inside a vehicle to travel.')
            return
        if vehicle.db.pilot != caller:
            caller.msg('You must be the pilot to move this vehicle.')
            return

        matches = search_object(self.args)
        destinations = [obj for obj in matches if hasattr(obj, 'contents')]
        if not destinations:
            caller.msg('No matching destination room was found.')
            return
        destination = destinations[0]

        if destination == vehicle.location:
            caller.msg(f'{vehicle.key} is already at {destination.key}.')
            return

        ok, reason = vehicle.can_travel(caller, destination)
        if not ok:
            caller.msg(reason)
            return

        origin = vehicle.location
        vehicle.move_to(destination, quiet=True, move_hooks=False)
        vehicle.db.last_docked_at = destination.key
        vehicle.at_travel(caller, origin=origin, destination=destination)

        if origin:
            origin.msg_contents(f'{vehicle.key} departs under the control of {caller.key}.')
        destination.msg_contents(f'{vehicle.key} arrives and settles into place.')
        vehicle.msg_contents(f'{vehicle.key} travels from {origin.key if origin else "somewhere"} to {destination.key}.')
        caller.msg(f'You pilot |w{vehicle.key}|n to |w{destination.key}|n.')


class CmdVehicleStatus(VehicleCommandMixin, Command):
    """
    Show the current vehicle state.

    Usage:
      vehicle
      vehiclestatus
    """

    key = 'vehicle'
    aliases = ['vehiclestatus', 'shipstatus']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You are not currently inside a vehicle.')
            return
        caller.msg(vehicle.get_status_report(looker=caller))


class CmdMyShips(Command):
    """
    List vehicles you own.

    Usage:
      myships
    """

    key = 'myships'
    aliases = ['hangarlist', 'ownedships']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicles = caller.db.owned_vehicles or []
        if not vehicles:
            caller.msg('You do not own any vehicles yet.')
            return

        lines = ['|wOwned Vehicles|n']
        for entry in vehicles:
            if hasattr(entry, 'key'):
                obj = entry
            else:
                found = search_object(entry)
                obj = found[0] if found else None
            if not obj:
                continue
            location = obj.location.key if obj.location else 'Nowhere'
            pilot = obj.db.pilot.key if obj.db.pilot else 'none'
            lines.append(f'- {obj.key} | location: {location} | pilot: {pilot}')

        caller.msg('\n'.join(lines))


class CmdCargoStatus(VehicleCommandMixin, Command):
    """
    Show the cargo hold contents of the vehicle you are in.

    Usage:
      cargo
      cargostatus
    """

    key = 'cargo'
    aliases = ['cargostatus', 'hold']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You are not inside a vehicle.')
            return
        caller.msg(vehicle.get_cargo_report())


class CmdLoadCargo(VehicleCommandMixin, Command):
    """
    Load ore from a nearby mining storage unit into this vehicle's cargo hold.

    Usage:
      loadcargo <resource> <tons>

    You must be piloting (or aboard) a vehicle with a cargo hold, docked next
    to a mining storage unit you own.  Resource names are partial-match.

    Example:
      loadcargo iron 50
      loadcargo copper 20
    """

    key = 'loadcargo'
    aliases = ['loadore']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You must be inside a vehicle to load cargo.')
            return
        if not vehicle.is_allowed_boarder(caller):
            caller.msg('You are not authorised to manage this vehicle\'s cargo.')
            return

        args = self.args.strip().split(None, 1)
        if len(args) < 2:
            caller.msg('Usage: loadcargo <resource name> <tons>')
            return
        resource_query, tons_str = args
        try:
            tons_req = float(tons_str)
        except ValueError:
            caller.msg('Tons must be a number.')
            return
        if tons_req <= 0:
            caller.msg('Tons must be greater than zero.')
            return

        # Find a mining storage unit in the vehicle's exterior location
        ext = vehicle.get_exterior_location()
        if not ext:
            caller.msg('The vehicle has no known docking location.')
            return

        storage = None
        for obj in ext.contents:
            if obj.tags.has('mining_storage', category='mining'):
                if getattr(obj.db, 'owner', None) == caller or getattr(obj.db, 'owner', None) is None:
                    storage = obj
                    break
        if not storage:
            caller.msg('No accessible mining storage unit found at this location.')
            return

        from typeclasses.mining import RESOURCE_CATALOG
        inventory = storage.db.inventory or {}

        # Partial-match resource key
        matched_key = None
        for key in inventory:
            name = RESOURCE_CATALOG.get(key, {}).get('name', key)
            if resource_query.lower() in name.lower() or resource_query.lower() in key.lower():
                matched_key = key
                break
        if not matched_key:
            caller.msg(
                f"No resource matching '{resource_query}' found in {storage.key}.\n"
                f"Use |wcargo|n to see the storage inventory."
            )
            return

        available = float(inventory.get(matched_key, 0.0))
        if available <= 0:
            caller.msg(f'{RESOURCE_CATALOG.get(matched_key, {}).get("name", matched_key)} is not in storage.')
            return

        try:
            actual = vehicle.load_cargo(matched_key, min(tons_req, available))
        except ValueError as err:
            caller.msg(str(err))
            return

        storage.withdraw(matched_key, actual)
        name = RESOURCE_CATALOG.get(matched_key, {}).get('name', matched_key)
        caller.msg(
            f'Loaded |w{actual}t|n of {name} into |w{vehicle.key}|n cargo hold. '
            f'({vehicle.cargo_total_mass():.1f}/{vehicle.db.cargo_capacity_tons:.0f} t used)'
        )


class CmdUnloadCargo(VehicleCommandMixin, Command):
    """
    Unload ore from this vehicle's cargo hold into a nearby mining storage unit.

    Usage:
      unloadcargo <resource> <tons>
      unloadcargo all

    Transfers to the first accessible mining storage unit at the docking location.

    Examples:
      unloadcargo iron 50
      unloadcargo all
    """

    key = 'unloadcargo'
    aliases = ['unloadore', 'offload']
    help_category = 'Vehicles'

    def func(self):
        caller = self.caller
        vehicle = self._current_vehicle(caller)
        if not vehicle:
            caller.msg('You must be inside a vehicle to unload cargo.')
            return
        if not vehicle.is_allowed_boarder(caller):
            caller.msg('You are not authorised to manage this vehicle\'s cargo.')
            return

        cargo = vehicle.db.cargo or {}
        if not cargo:
            caller.msg(f'|w{vehicle.key}|n cargo hold is empty.')
            return

        ext = vehicle.get_exterior_location()
        if not ext:
            caller.msg('The vehicle has no known docking location.')
            return

        storage = None
        for obj in ext.contents:
            if obj.tags.has('mining_storage', category='mining'):
                if getattr(obj.db, 'owner', None) == caller or getattr(obj.db, 'owner', None) is None:
                    storage = obj
                    break
        if not storage:
            caller.msg('No accessible mining storage unit found at this location.')
            return

        from typeclasses.mining import RESOURCE_CATALOG

        args = self.args.strip().lower()

        if args == 'all':
            contents = vehicle.unload_all_cargo()
            inventory = storage.db.inventory or {}
            lines = [f'Unloaded from |w{vehicle.key}|n into |w{storage.key}|n:']
            for key, tons in contents.items():
                # Respect storage capacity
                cap = float(getattr(storage.db, 'capacity_tons', 500.0) or 500.0)
                space = max(0.0, cap - storage.total_mass())
                deposited = round(min(float(tons), space), 2)
                if deposited > 0:
                    inventory[key] = round(float(inventory.get(key, 0.0)) + deposited, 2)
                    name = RESOURCE_CATALOG.get(key, {}).get('name', key)
                    lines.append(f'  {name}: {deposited}t')
            storage.db.inventory = inventory
            caller.msg('\n'.join(lines))
            return

        parts = args.split(None, 1)
        if len(parts) < 2:
            caller.msg('Usage: unloadcargo <resource> <tons>  OR  unloadcargo all')
            return
        resource_query, tons_str = parts
        try:
            tons_req = float(tons_str)
        except ValueError:
            caller.msg('Tons must be a number.')
            return

        matched_key = None
        for key in cargo:
            name = RESOURCE_CATALOG.get(key, {}).get('name', key)
            if resource_query in name.lower() or resource_query in key.lower():
                matched_key = key
                break
        if not matched_key:
            caller.msg(f"No resource matching '{resource_query}' in cargo.")
            return

        cap = float(getattr(storage.db, 'capacity_tons', 500.0) or 500.0)
        space = max(0.0, cap - storage.total_mass())
        tons_req = min(tons_req, space)
        if tons_req <= 0:
            caller.msg(f'|w{storage.key}|n is at capacity.')
            return

        actual = vehicle.unload_cargo(matched_key, tons_req)
        inventory = storage.db.inventory or {}
        inventory[matched_key] = round(float(inventory.get(matched_key, 0.0)) + actual, 2)
        storage.db.inventory = inventory

        name = RESOURCE_CATALOG.get(matched_key, {}).get('name', matched_key)
        caller.msg(
            f'Unloaded |w{actual}t|n of {name} into |w{storage.key}|n. '
            f'Vehicle hold: {vehicle.cargo_total_mass():.1f}/{vehicle.db.cargo_capacity_tons:.0f} t'
        )
