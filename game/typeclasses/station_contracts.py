from evennia import create_script, search_script

from typeclasses.scripts import Script


class StationContractsScript(Script):
    """
    Rotating / static contracts. One global instance (key station_contracts).
    """

    def at_script_creation(self):
        self.key = "station_contracts"
        self.desc = "Rotating station contracts for players."
        self.persistent = True
        self.interval = 3600
        self.repeats = 0
        self.db.schema_version = 1
        self.db.rotation_index = 0
        self.db.contracts = []

    def at_repeat(self):
        pass


def get_contracts_script(create_missing: bool = True):
    found = search_script("station_contracts")
    if found:
        return found[0]
    if create_missing:
        return create_script("typeclasses.station_contracts.StationContractsScript")
    return None
