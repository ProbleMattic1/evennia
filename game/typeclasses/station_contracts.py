from evennia import search_script

from typeclasses.scripts import Script

_DEFAULT_ROTATION_HOURS = 6


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
        self.db.schema_version = 2
        self.db.rotation_index = 0
        self.db.contracts = []
        if self.db.contracts_in_flight is None:
            self.db.contracts_in_flight = []
        if getattr(self.db, "rotation_interval_hours", None) is None:
            self.db.rotation_interval_hours = _DEFAULT_ROTATION_HOURS

    def at_repeat(self):
        from world.station_contract_rotation import build_visible_contracts
        from world.time import parse_iso, to_iso, utc_now

        now = utc_now()
        interval_h = max(1, int(getattr(self.db, "rotation_interval_hours", _DEFAULT_ROTATION_HOURS) or _DEFAULT_ROTATION_HOURS))
        last = getattr(self.db, "last_contract_rotation_at", None)
        if last:
            prev = parse_iso(str(last))
            if prev and (now - prev).total_seconds() < interval_h * 3600:
                return

        inflight = set(str(x) for x in (self.db.contracts_in_flight or []) if x)
        prev_list = list(self.db.contracts or [])
        ri = int(self.db.rotation_index or 0)
        new_list, next_ri = build_visible_contracts(
            rotation_index=ri,
            previous_contracts=prev_list,
            in_flight_ids=inflight,
        )
        self.db.contracts = new_list
        self.db.rotation_index = next_ri
        self.db.last_contract_rotation_at = to_iso(now) or ""


def register_station_contract_in_flight(contract_id: str) -> None:
    script = get_contracts_script(create_missing=True)
    if not script:
        return
    cid = str(contract_id or "").strip()
    if not cid:
        return
    s = {str(x) for x in (script.db.contracts_in_flight or []) if x}
    s.add(cid)
    script.db.contracts_in_flight = sorted(s)


def unregister_station_contract_in_flight(contract_id: str) -> None:
    script = get_contracts_script(create_missing=False)
    if not script:
        return
    cid = str(contract_id or "").strip()
    s = {str(x) for x in (script.db.contracts_in_flight or []) if x}
    s.discard(cid)
    script.db.contracts_in_flight = sorted(s)


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
