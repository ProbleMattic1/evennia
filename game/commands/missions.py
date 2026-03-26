from commands.command import Command


class CmdMissions(Command):
    """
    Review mission opportunities and active missions.

    Usage:
      missions
    """

    key = "missions"
    aliases = ["quests", "story"]
    locks = "cmd:all()"
    help_category = "Story"

    def func(self):
        caller = self.caller
        caller.missions.sync_global_seeds()
        if caller.location:
            caller.missions.sync_room(caller.location)

        data = caller.missions.serialize_for_web()
        ledger = data.get("morality") or {}

        lines = [
            "|wMission Board|n",
            f"Morality: good={ledger.get('good', 0)} evil={ledger.get('evil', 0)} "
            f"lawful={ledger.get('lawful', 0)} chaotic={ledger.get('chaotic', 0)}",
            "",
        ]

        opportunities = list(data.get("opportunities") or [])
        active = list(data.get("active") or [])

        if opportunities:
            lines.append("|wOpportunities|n")
            for row in opportunities[-10:]:
                lines.append(f"  {row['id']}: {row['title']} - {row.get('summary') or ''}")
            lines.append("")
        else:
            lines.append("No open mission opportunities.")
            lines.append("")

        if active:
            lines.append("|wActive Missions|n")
            for row in active[-10:]:
                current = row.get("currentObjective") or {}
                text = current.get("prompt") or current.get("text") or "No current objective."
                lines.append(f"  {row['id']}: {row['title']}")
                lines.append(f"    {text}")
                if current.get("kind") == "choice":
                    for choice in list(current.get("choices") or []):
                        lines.append(f"    - {choice['id']}: {choice['label']}")
        else:
            lines.append("No active missions.")

        caller.msg("\n".join(lines))


class CmdMissionAccept(Command):
    """
    Accept a mission opportunity.

    Usage:
      acceptmission <opportunity_id>
    """

    key = "acceptmission"
    aliases = ["missionaccept"]
    locks = "cmd:all()"
    help_category = "Story"

    def func(self):
        oid = (self.args or "").strip()
        if not oid:
            self.caller.msg("Usage: acceptmission <opportunity_id>")
            return
        ok, msg, _mission = self.caller.missions.accept(oid)
        self.caller.msg(msg)


class CmdMissionChoose(Command):
    """
    Make a story decision for the current mission step.

    Usage:
      missionchoose <mission_id> = <choice_id>
    """

    key = "missionchoose"
    aliases = ["choosemission", "questchoose"]
    locks = "cmd:all()"
    help_category = "Story"

    def parse(self):
        lhs, rhs = self.args.split("=", 1) if "=" in self.args else (self.args, "")
        self.mission_id = lhs.strip()
        self.choice_id = rhs.strip()

    def func(self):
        if not self.mission_id or not self.choice_id:
            self.caller.msg("Usage: missionchoose <mission_id> = <choice_id>")
            return
        ok, msg, _mission = self.caller.missions.choose(self.mission_id, self.choice_id)
        self.caller.msg(msg)
