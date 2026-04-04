"""
Tracks short-lived pocket rooms spawned from ``instance_prototypes.json``.
"""

from __future__ import annotations

import uuid

from evennia import create_object, search_object

from typeclasses.scripts import Script
from world.instance_prototypes import get_instance_template


class InstanceManager(Script):
    def at_script_creation(self):
        self.key = "instance_manager"
        self.desc = "Spawn and track holo/sim pocket rooms."
        self.persistent = True
        self.interval = 0
        if self.db.instances is None:
            self.db.instances = {}

    def enter_template(self, character, template_id: str):
        tpl = get_instance_template(template_id)
        iid = uuid.uuid4().hex[:12]
        room = create_object(
            "typeclasses.rooms.Room",
            key=f"{tpl['title']} [{iid}]",
        )
        room.db.desc = str(tpl.get("desc") or "")
        room.db.instance_template_id = template_id
        room.db.instance_id = iid
        prev = character.location
        character.move_to(room, quiet=True)
        inv = dict(self.db.instances or {})
        inv[iid] = {
            "template_id": template_id,
            "room_id": room.id,
            "owner_id": character.id,
            "return_room_id": prev.id if prev else None,
        }
        self.db.instances = inv
        character.db.active_instance_id = iid
        hint = tpl.get("return_anchor_hint") or "Use |wleaveinstance|n to exit."
        return room, hint

    def leave_instance(self, character):
        iid = getattr(character.db, "active_instance_id", None)
        if not iid:
            return False, "You are not in a pocket instance."
        inv = dict(self.db.instances or {})
        row = inv.pop(str(iid), None)
        self.db.instances = inv
        character.db.active_instance_id = None
        if not row:
            return False, "Instance record missing."
        ret_id = row.get("return_room_id")
        dest = None
        if ret_id:
            found = search_object(f"#{ret_id}")
            dest = found[0] if found else None
        if not dest:
            from world.bootstrap_hub import get_hub_room

            dest = get_hub_room()
        rid = row.get("room_id")
        if rid:
            found = search_object(f"#{rid}")
            if found:
                r = found[0]
                r.delete()
        if dest:
            character.move_to(dest, quiet=True)
        return True, f"Returned to {dest.key if dest else 'hub'}."
