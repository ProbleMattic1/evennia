from evennia import search_script

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
    from evennia import GLOBAL_SCRIPTS

    script = GLOBAL_SCRIPTS.get("station_contracts")
    if script:
        return script
    found = search_script("station_contracts")
    if found:
        return found[0]
    if create_missing:
        raise RuntimeError(
            "station_contracts global script missing. Add it to server.conf.settings.GLOBAL_SCRIPTS."
        )
    return None
