"""World simulation helpers: instances and parties."""

from commands.command import Command


class CmdEnterInstance(Command):
    key = "enterinstance"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        tid = (self.args or "").strip()
        if not tid:
            self.msg("Usage: enterinstance <template_id>")
            return
        from typeclasses.instance_manager import InstanceManager
        from evennia import GLOBAL_SCRIPTS

        mgr = GLOBAL_SCRIPTS.get("instance_manager")
        if not mgr or not isinstance(mgr, InstanceManager):
            self.msg("Instance manager unavailable.")
            return
        try:
            _room, hint = mgr.enter_template(self.caller, tid)
        except ValueError as exc:
            self.msg(str(exc))
            return
        self.msg(f"You enter a pocket volume. {hint}")


class CmdLeaveInstance(Command):
    key = "leaveinstance"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from typeclasses.instance_manager import InstanceManager
        from evennia import GLOBAL_SCRIPTS

        mgr = GLOBAL_SCRIPTS.get("instance_manager")
        if not mgr or not isinstance(mgr, InstanceManager):
            self.msg("Instance manager unavailable.")
            return
        ok, msg = mgr.leave_instance(self.caller)
        self.msg(msg)


class CmdPartyForm(Command):
    key = "partyform"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from typeclasses.party_registry import get_party_registry
        from world.challenges.challenge_signals import emit

        reg = get_party_registry()
        if reg.party_id_for(self.caller):
            self.msg("You are already in a party. Use partyleave first.")
            return
        pid = reg.create_party(self.caller)
        emit(self.caller, "party_formed", {"party_id": pid})
        self.msg(f"Party formed. id={pid}")


class CmdPartyLeave(Command):
    key = "partyleave"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from typeclasses.party_registry import get_party_registry

        reg = get_party_registry()
        if reg.leave_party(self.caller):
            self.msg("You leave the party (disbanded if you were leader).")
        else:
            self.msg("You are not in a party.")


class CmdPartyStatus(Command):
    key = "partystatus"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        from typeclasses.party_registry import get_party_registry

        reg = get_party_registry()
        pid = reg.party_id_for(self.caller)
        if not pid:
            self.msg("No party.")
            return
        row = reg.party_row(pid)
        self.msg(f"Party {pid}: leader={row.get('leader_id')} members={row.get('member_ids')}")
