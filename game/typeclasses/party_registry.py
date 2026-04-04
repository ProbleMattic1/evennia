"""
Lightweight party / fleet registry for shared space sorties and UI.
"""

from __future__ import annotations

import uuid

from evennia import GLOBAL_SCRIPTS

from typeclasses.scripts import Script


class PartyRegistry(Script):
    def at_script_creation(self):
        self.key = "party_registry"
        self.desc = "Character party membership for space / surface ops."
        self.persistent = True
        self.interval = 0
        if self.db.parties is None:
            self.db.parties = {}
        if self.db.char_to_party is None:
            self.db.char_to_party = {}

    def create_party(self, leader, fleet_slug: str = "") -> str:
        pid = uuid.uuid4().hex[:10]
        oid = int(leader.id)
        parties = dict(self.db.parties or {})
        parties[pid] = {
            "leader_id": oid,
            "member_ids": [oid],
            "fleet_slug": str(fleet_slug or "").strip(),
        }
        self.db.parties = parties
        c2p = dict(self.db.char_to_party or {})
        c2p[str(oid)] = pid
        self.db.char_to_party = c2p
        return pid

    def leave_party(self, character) -> bool:
        c2p = dict(self.db.char_to_party or {})
        pid = c2p.get(str(int(character.id)))
        if not pid:
            return False
        parties = dict(self.db.parties or {})
        row = parties.get(str(pid))
        if not row:
            c2p.pop(str(int(character.id)), None)
            self.db.char_to_party = c2p
            return True
        if int(row["leader_id"]) == int(character.id):
            for mid in row.get("member_ids") or []:
                c2p.pop(str(int(mid)), None)
            parties.pop(str(pid), None)
            self.db.parties = parties
            self.db.char_to_party = c2p
            return True
        mids = [int(m) for m in row.get("member_ids") or [] if int(m) != int(character.id)]
        row["member_ids"] = mids
        parties[str(pid)] = row
        c2p.pop(str(int(character.id)), None)
        self.db.parties = parties
        self.db.char_to_party = c2p
        return True

    def party_id_for(self, character) -> str | None:
        return (dict(self.db.char_to_party or {})).get(str(int(character.id)))

    def party_row(self, party_id: str) -> dict | None:
        return dict((self.db.parties or {})).get(str(party_id))


def get_party_registry():
    reg = GLOBAL_SCRIPTS.get("party_registry")
    if reg:
        return reg
    raise RuntimeError("party_registry missing from GLOBAL_SCRIPTS")
