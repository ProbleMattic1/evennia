from __future__ import annotations

import uuid
from typing import Any

from evennia.utils import logger

from world.quest_loader import get_quest_template, matching_quest_templates_for_interaction, matching_quest_templates_for_room
from world.time import to_iso, utc_now

QUEST_ATTR_KEY = "_quests"
QUEST_ATTR_CATEGORY = "storyline"


def _blank_state() -> dict[str, Any]:
    return {
        "flags": {},
        "opportunities": [],
        "active": [],
        "completed": [],
        "failed": [],
    }


def _payload_matches(match: dict, payload: dict) -> bool:
    for k, v in (match or {}).items():
        if payload.get(k) != v:
            return False
    return True


class QuestHandler:
    def __init__(self, obj):
        self.obj = obj
        self._state = obj.attributes.get(
            QUEST_ATTR_KEY,
            category=QUEST_ATTR_CATEGORY,
            default=_blank_state(),
        )
        self._normalize()

    def _normalize(self) -> None:
        if not isinstance(self._state, dict):
            self._state = _blank_state()
        self._state.setdefault("flags", {})
        self._state.setdefault("opportunities", [])
        self._state.setdefault("active", [])
        self._state.setdefault("completed", [])
        self._state.setdefault("failed", [])

    def _save(self) -> None:
        self.obj.attributes.add(QUEST_ATTR_KEY, self._state, category=QUEST_ATTR_CATEGORY)

    def get_flag(self, key: str, default=None):
        return (self._state.get("flags") or {}).get(key, default)

    def set_flags(self, delta: dict[str, Any] | None) -> None:
        if not delta:
            return
        flags = dict(self._state.get("flags") or {})
        flags.update(delta)
        self._state["flags"] = flags
        self._save()

    def _apply_rewards(self, rewards: dict[str, Any] | None) -> None:
        """
        Supported ``rewards`` keys: ``credits`` (economy deposit), ``xp`` (``Character.grant_xp``).
        """
        if not rewards:
            return
        credits = int(rewards.get("credits") or 0)
        if credits > 0:
            try:
                from typeclasses.economy import get_economy

                econ = get_economy(create_missing=True)
                acct = econ.get_character_account(self.obj)
                econ.ensure_account(acct, opening_balance=int(self.obj.db.credits or 0))
                econ.deposit(acct, credits, memo="Quest reward")
                self.obj.db.credits = econ.get_character_balance(self.obj)
            except Exception as exc:
                logger.log_err(f"[quests] credit reward apply failed for {self.obj.key}: {exc}")
        try:
            from world.progression import apply_reward_xp

            apply_reward_xp(self.obj, rewards, reason="quest reward")
        except Exception as exc:
            logger.log_err(f"[quests] XP reward apply failed for {self.obj.key}: {exc}")

    def _prereqs_ok(self, tmpl: dict) -> bool:
        pre = tmpl.get("prerequisites") or {}
        for qid in list(pre.get("completedQuestIdsAny") or []):
            if not any(
                r.get("templateId") == qid for r in (self._state.get("completed") or [])
            ):
                return False
        for fk in list(pre.get("flagsAll") or []):
            if not self.get_flag(fk):
                return False
        return True

    def _has_active_template(self, tid: str) -> bool:
        return any(q.get("templateId") == tid for q in self._state.get("active") or [])

    def _has_completed_template(self, tid: str) -> bool:
        return any(q.get("templateId") == tid for q in self._state.get("completed") or [])

    def _eligible(self, tmpl: dict) -> bool:
        tid = tmpl["id"]
        elig = tmpl.get("eligibility") or {}
        if bool(elig.get("once", True)) and self._has_completed_template(tid):
            return False
        max_active = max(1, int(elig.get("maxActive") or 1))
        n = sum(1 for q in self._state.get("active") or [] if q.get("templateId") == tid)
        return n < max_active

    def offer_from_template(self, tmpl: dict, *, source: dict[str, Any]) -> dict | None:
        if not tmpl or not self._prereqs_ok(tmpl) or not self._eligible(tmpl):
            return None
        source_key = str(source.get("sourceKey") or "").strip()
        tid = tmpl["id"]
        for row in self._state.get("opportunities") or []:
            if row.get("templateId") == tid and row.get("sourceKey") == source_key:
                return None
        if self._has_active_template(tid) and not source_key:
            return None
        row = {
            "id": f"qopp-{uuid.uuid4().hex[:12]}",
            "templateId": tmpl["id"],
            "title": tmpl.get("title") or tmpl["id"],
            "summary": tmpl.get("summary") or "",
            "storylineId": tmpl.get("storylineId") or "",
            "source": dict(source or {}),
            "sourceKey": source_key,
            "createdAt": to_iso(utc_now()),
        }
        ops = list(self._state.get("opportunities") or [])
        ops.append(row)
        self._state["opportunities"] = ops[-50:]
        self._save()
        return row

    def sync_room(self, room) -> None:
        """Advance visit/flag objectives without re-offering room-triggered quests."""
        if not room:
            return
        self._progress_visit_room(room)
        self._progress_flag_objectives()

    def on_room_enter(self, room) -> None:
        if not room:
            return
        for tmpl in matching_quest_templates_for_room(room):
            if (tmpl.get("trigger") or {}).get("kind") == "room":
                self.offer_from_template(
                    tmpl,
                    source={
                        "kind": "room",
                        "roomKey": room.key,
                        "sourceKey": f"room:{room.key}:{tmpl['id']}",
                    },
                )
        self.sync_room(room)

    def on_event(self, event_name: str, payload: dict[str, Any]) -> None:
        self._progress_resolve_situation_signal(event_name, payload)
        self._progress_flag_objectives()

    def on_interaction(self, interaction_key: str) -> None:
        ikey = str(interaction_key or "").strip().lower()
        if not ikey:
            return
        for tmpl in matching_quest_templates_for_interaction(ikey):
            self.offer_from_template(
                tmpl,
                source={
                    "kind": "interaction",
                    "interactionKey": ikey,
                    "sourceKey": f"interaction:{ikey}:{tmpl['id']}",
                },
            )
        self._progress_interaction(ikey)
        self._progress_flag_objectives()

    def accept(self, opportunity_id: str) -> tuple[bool, str, dict | None]:
        opp = next((o for o in self._state.get("opportunities") or [] if o.get("id") == opportunity_id), None)
        if not opp:
            return False, "Quest opportunity not found.", None
        tmpl = get_quest_template(opp.get("templateId") or "")
        if not tmpl:
            return False, "Quest template missing.", None
        inst = {
            "id": f"quest-{uuid.uuid4().hex[:12]}",
            "templateId": tmpl["id"],
            "templateVersion": int(tmpl.get("version") or 1),
            "title": tmpl.get("title") or tmpl["id"],
            "summary": tmpl.get("summary") or "",
            "storylineId": tmpl.get("storylineId") or "",
            "threadId": tmpl.get("threadId") or "",
            "status": "active",
            "objectiveIndex": 0,
            "completedObjectiveIds": [],
            "resolutionLog": [],
            "choices": [],
            "acceptedAt": to_iso(utc_now()),
            "completedAt": None,
        }
        self._state["opportunities"] = [o for o in self._state.get("opportunities") or [] if o.get("id") != opportunity_id]
        act = list(self._state.get("active") or [])
        act.append(inst)
        self._state["active"] = act[-30:]
        self._save()
        return True, f"Accepted quest: {inst['title']}.", inst

    def _current_objective(self, quest: dict, tmpl: dict) -> dict | None:
        idx = int(quest.get("objectiveIndex") or 0)
        objs = list(tmpl.get("objectives") or [])
        if idx < 0 or idx >= len(objs):
            return None
        return objs[idx]

    def _set_objective_index_by_id(self, quest: dict, tmpl: dict, oid: str) -> bool:
        for i, o in enumerate(tmpl.get("objectives") or []):
            if o.get("id") == oid:
                quest["objectiveIndex"] = i
                return True
        return False

    def _complete_objective(
        self,
        quest: dict,
        tmpl: dict,
        objective: dict,
        *,
        completion_key: str | None = None,
        choice: dict | None = None,
    ) -> None:
        done = list(quest.get("completedObjectiveIds") or [])
        oid = objective.get("id")
        first_time = oid not in done
        if oid not in done:
            done.append(oid)
            quest["completedObjectiveIds"] = done
        log = list(quest.get("resolutionLog") or [])
        log.append({"objectiveId": oid, "completionKey": completion_key or "", "at": to_iso(utc_now())})
        quest["resolutionLog"] = log[-500:]

        if first_time:
            merged_rw: dict[str, Any] = {}
            merged_rw.update(dict(objective.get("rewards") or {}))
            if choice:
                merged_rw.update(dict(choice.get("rewards") or {}))
            if merged_rw:
                self._apply_rewards(merged_rw)

        if choice and choice.get("nextObjectiveId"):
            if self._set_objective_index_by_id(quest, tmpl, choice["nextObjectiveId"]):
                return

        quest["objectiveIndex"] = int(quest.get("objectiveIndex") or 0) + 1
        if quest["objectiveIndex"] >= len(list(tmpl.get("objectives") or [])) or (choice or {}).get("completeQuest"):
            self._complete_quest(quest, tmpl)

    def _complete_quest(self, quest: dict, tmpl: dict) -> None:
        self._apply_rewards(dict(tmpl.get("rewards") or {}))

        quest["status"] = "completed"
        quest["completedAt"] = to_iso(utc_now())
        self._state["active"] = [q for q in self._state.get("active") or [] if q.get("id") != quest.get("id")]
        comp = list(self._state.get("completed") or [])
        comp.append(dict(quest))
        self._state["completed"] = comp[-200:]
        for nxt in list(tmpl.get("unlockQuestIds") or []):
            t2 = get_quest_template(nxt)
            if t2:
                self.offer_from_template(
                    t2,
                    source={
                        "kind": "unlock",
                        "fromQuest": tmpl["id"],
                        "sourceKey": f"unlock:{tmpl['id']}:{nxt}",
                    },
                )
        self._save()
        from world.achievement_hooks import track_quest_completed

        track_quest_completed(self.obj)

    def _progress_visit_room(self, room) -> None:
        key = str(room.key or "")
        changed = False
        for quest in list(self._state.get("active") or []):
            tmpl = get_quest_template(quest.get("templateId") or "")
            if not tmpl:
                continue
            obj = self._current_objective(quest, tmpl)
            if not obj or obj.get("kind") != "visit_room":
                continue
            if key in set(obj.get("roomKeysAny") or []):
                self._complete_objective(quest, tmpl, obj, completion_key="visit")
                changed = True
        if changed:
            self._save()

    def _progress_interaction(self, ikey: str) -> None:
        changed = False
        for quest in list(self._state.get("active") or []):
            tmpl = get_quest_template(quest.get("templateId") or "")
            if not tmpl:
                continue
            obj = self._current_objective(quest, tmpl)
            if not obj:
                continue
            if obj.get("kind") == "interaction":
                valid = {str(v).strip().lower() for v in list(obj.get("interactionKeysAny") or [])}
                if ikey in valid:
                    self._complete_objective(quest, tmpl, obj, completion_key="interaction")
                    changed = True
            elif obj.get("kind") == "resolve_situation":
                for path in list(obj.get("paths") or []):
                    if path.get("via") != "interaction":
                        continue
                    valid = set(path.get("interactionKeysAny") or [])
                    if ikey in valid:
                        self._complete_objective(
                            quest, tmpl, obj, completion_key=path.get("completionKey")
                        )
                        changed = True
                        break
        if changed:
            self._save()

    def _progress_resolve_situation_signal(self, event_name: str, payload: dict) -> None:
        changed = False
        for quest in list(self._state.get("active") or []):
            tmpl = get_quest_template(quest.get("templateId") or "")
            if not tmpl:
                continue
            obj = self._current_objective(quest, tmpl)
            if not obj or obj.get("kind") != "resolve_situation":
                continue
            for path in list(obj.get("paths") or []):
                if path.get("via") != "signal":
                    continue
                if path.get("signal") != event_name:
                    continue
                if _payload_matches(path.get("match") or {}, payload):
                    self._complete_objective(
                        quest, tmpl, obj, completion_key=path.get("completionKey")
                    )
                    changed = True
                    break
        if changed:
            self._save()

    def _progress_flag_objectives(self) -> None:
        changed = False
        for quest in list(self._state.get("active") or []):
            tmpl = get_quest_template(quest.get("templateId") or "")
            if not tmpl:
                continue
            obj = self._current_objective(quest, tmpl)
            if not obj or obj.get("kind") != "flag":
                continue
            req = list(obj.get("requireFlagsAll") or [])
            if req and all(self.get_flag(fk) for fk in req):
                self._complete_objective(quest, tmpl, obj, completion_key="flags")
                changed = True
        if changed:
            self._save()

    def choose(self, quest_id: str, choice_id: str) -> tuple[bool, str, dict | None]:
        quest = next((q for q in self._state.get("active") or [] if q.get("id") == quest_id), None)
        if not quest:
            return False, "Active quest not found.", None
        tmpl = get_quest_template(quest.get("templateId") or "")
        if not tmpl:
            return False, "Quest template missing.", None
        obj = self._current_objective(quest, tmpl)
        if not obj or obj.get("kind") != "choice":
            return False, "This quest is not waiting on a decision.", None
        choice = next((c for c in obj.get("choices") or [] if c.get("id") == choice_id), None)
        if not choice:
            return False, "Choice not found.", None
        self.set_flags(choice.get("setFlags"))
        chlog = list(quest.get("choices") or [])
        chlog.append({"objectiveId": obj.get("id"), "choiceId": choice_id, "at": to_iso(utc_now())})
        quest["choices"] = chlog
        self._complete_objective(quest, tmpl, obj, completion_key=f"choice:{choice_id}", choice=choice)
        self._progress_flag_objectives()
        self._save()
        return True, choice.get("outcome") or "Decision recorded.", quest

    def serialize_for_web(self) -> dict[str, Any]:
        def active_payload(row):
            tmpl = get_quest_template(row.get("templateId") or "") or {}
            obj = self._current_objective(row, tmpl) if tmpl else None
            return {
                "id": row.get("id"),
                "templateId": row.get("templateId"),
                "title": row.get("title"),
                "summary": row.get("summary"),
                "storylineId": row.get("storylineId"),
                "status": row.get("status"),
                "currentObjective": obj,
                "resolutionLog": list(row.get("resolutionLog") or [])[-20:],
                "choices": list(row.get("choices") or []),
            }

        return {
            "flags": dict(self._state.get("flags") or {}),
            "opportunities": [dict(x) for x in list(self._state.get("opportunities") or [])[-20:]],
            "active": [active_payload(x) for x in list(self._state.get("active") or [])[-20:]],
            "completed": [dict(x) for x in list(self._state.get("completed") or [])[-30:]],
        }
