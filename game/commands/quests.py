from commands.command import Command


class CmdQuests(Command):
    """
    Review main storyline quest opportunities and active quests.

    Usage:
      storyquests
    """

    key = "storyquests"
    aliases = ["mainquests"]
    locks = "cmd:all()"
    help_category = "Story"

    def func(self):
        c = self.caller
        if c.location:
            c.quests.on_room_enter(c.location)
        data = c.quests.serialize_for_web()

        lines = ["|wMain quests|n", ""]

        opportunities = list(data.get("opportunities") or [])
        active = list(data.get("active") or [])

        if opportunities:
            lines.append("|wOpportunities|n")
            for row in opportunities[-10:]:
                lines.append(f"  {row['id']}: {row['title']} - {row.get('summary') or ''}")
            lines.append("")
        else:
            lines.append("No open quest opportunities.")
            lines.append("")

        if active:
            lines.append("|wActive quests|n")
            for row in active[-10:]:
                current = row.get("currentObjective") or {}
                text = current.get("prompt") or current.get("text") or "No current objective."
                lines.append(f"  {row['id']}: {row['title']}")
                lines.append(f"    {text}")
                if current.get("kind") == "choice":
                    for choice in list(current.get("choices") or []):
                        lines.append(f"    - {choice['id']}: {choice['label']}")
        else:
            lines.append("No active quests.")

        c.msg("\n".join(lines))


class CmdQuestAccept(Command):
    """
    Accept a main quest opportunity.

    Usage:
      questaccept <opportunity_id>
    """

    key = "questaccept"
    locks = "cmd:all()"
    help_category = "Story"

    def func(self):
        oid = (self.args or "").strip()
        if not oid:
            self.caller.msg("Usage: questaccept <opportunity_id>")
            return
        ok, msg, _quest = self.caller.quests.accept(oid)
        self.caller.msg(msg)


class CmdQuestChoose(Command):
    """
    Make a story decision for the current main quest step.

    Usage:
      mainquestchoose <quest_id> = <choice_id>
    """

    key = "mainquestchoose"
    aliases = ["storychoose"]
    locks = "cmd:all()"
    help_category = "Story"

    def parse(self):
        lhs, rhs = self.args.split("=", 1) if "=" in self.args else (self.args, "")
        self.quest_id = lhs.strip()
        self.choice_id = rhs.strip()

    def func(self):
        if not self.quest_id or not self.choice_id:
            self.caller.msg("Usage: mainquestchoose <quest_id> = <choice_id>")
            return
        ok, msg, _quest = self.caller.quests.choose(self.quest_id, self.choice_id)
        self.caller.msg(msg)
