from __future__ import annotations

import uuid
from typing import Any

from evennia.utils import logger

from typeclasses.mission_seeds import get_mission_seeds_script
from world.mission_loader import (
    get_mission_template,
    matching_templates_for_interaction,
    matching_templates_for_room,
    matching_templates_for_seed,
)
from world.time import parse_iso, to_iso, utc_now

MISSION_ATTR_KEY = "_missions"
MISSION_ATTR_CATEGORY = "story"

MORAL_KEYS = ("good", "evil", "lawful", "chaotic")


def _blank_state() -> dict[str, Any]:
    return {
        "opportunities": [],
        "active": [],
        "completed": [],
        "cooldowns": {},
        "seenSources": [],
        "morality": {k: 0 for k in MORAL_KEYS},
    }


class MissionHandler:
    """
    Per-character mission state.

    World systems emit seeds into a global script. Individual characters track
    accepted missions, progression, history, and morality here.
    """

    def __init__(self, obj):
        self.obj = obj
        self._state = obj.attributes.get(
            MISSION_ATTR_KEY,
            category=MISSION_ATTR_CATEGORY,
            default=_blank_state(),
        )
        self._normalize()

    def _normalize(self) -> None:
        if not isinstance(self._state, dict):
            self._state = _blank_state()
        self._state.setdefault("opportunities", [])
        self._state.setdefault("active", [])
        self._state.setdefault("completed", [])
        self._state.setdefault("cooldowns", {})
        self._state.setdefault("seenSources", [])
        self._state.setdefault("morality", {})
        for key in MORAL_KEYS:
            self._state["morality"][key] = int(self._state["morality"].get(key) or 0)

        if not getattr(self.obj.db, "morality", None):
            self.obj.db.morality = dict(self._state["morality"])
        elif not any(int(self._state["morality"].get(key) or 0) for key in MORAL_KEYS):
            raw = dict(self.obj.db.morality or {})
            self._state["morality"] = {key: int(raw.get(key) or 0) for key in MORAL_KEYS}

    def _save(self) -> None:
        self.obj.attributes.add(MISSION_ATTR_KEY, self._state, category=MISSION_ATTR_CATEGORY)
        self.obj.db.morality = dict(self._state.get("morality") or {})

    @property
    def morality(self) -> dict[str, int]:
        return dict(self._state.get("morality") or {})

    def _should_mark_source_seen(self, source: dict[str, Any]) -> bool:
        kind = str(source.get("kind") or "").strip().lower()
        return kind in {"alert", "incident", "followup"}

    def _source_seen(self, source_key: str) -> bool:
        return source_key in set(self._state.get("seenSources") or [])

    def _mark_source_seen(self, source_key: str) -> None:
        if not source_key:
            return
        seen = list(self._state.get("seenSources") or [])
        if source_key not in seen:
            seen.append(source_key)
            self._state["seenSources"] = seen[-2000:]

    def _template_on_cooldown(self, template_id: str) -> bool:
        iso = (self._state.get("cooldowns") or {}).get(template_id)
        if not iso:
            return False
        tmpl = get_mission_template(template_id)
        if not tmpl:
            return False
        cooldown = int((tmpl.get("eligibility") or {}).get("cooldownSeconds") or 0)
        if cooldown <= 0:
            return False
        prev = parse_iso(iso)
        if not prev:
            return False
        return (utc_now() - prev).total_seconds() < cooldown

    def _has_active_template(self, template_id: str) -> bool:
        return any(m for m in self._state.get("active") or [] if m.get("templateId") == template_id)

    def _has_completed_template(self, template_id: str) -> bool:
        return any(m for m in self._state.get("completed") or [] if m.get("templateId") == template_id)

    def _find_active(self, mission_id: str) -> dict[str, Any] | None:
        for row in self._state.get("active") or []:
            if row.get("id") == mission_id:
                return row
        return None

    def _find_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        for row in self._state.get("opportunities") or []:
            if row.get("id") == opportunity_id:
                return row
        return None

    def _apply_morality(self, delta: dict[str, Any] | None) -> None:
        if not delta:
            return
        ledger = dict(self._state.get("morality") or {})
        for key in MORAL_KEYS:
            ledger[key] = int(ledger.get(key) or 0) + int(delta.get(key) or 0)
        self._state["morality"] = ledger

    def _apply_rewards(self, rewards: dict[str, Any] | None) -> None:
        if not rewards:
            return
        credits = int(rewards.get("credits") or 0)
        if credits <= 0:
            return
        try:
            from typeclasses.economy import get_economy

            econ = get_economy(create_missing=True)
            acct = econ.get_character_account(self.obj)
            econ.ensure_account(acct, opening_balance=int(self.obj.db.credits or 0))
            econ.deposit(acct, credits, memo="Mission reward")
            self.obj.db.credits = econ.get_character_balance(self.obj)
        except Exception as exc:
            logger.log_err(f"[missions] reward apply failed for {self.obj.key}: {exc}")

    def _eligible_for_template(self, tmpl: dict) -> bool:
        tid = tmpl["id"]
        elig = dict(tmpl.get("eligibility") or {})
        if self._template_on_cooldown(tid):
            return False
        if bool(elig.get("once")) and self._has_completed_template(tid):
            return False
        max_active = max(1, int(elig.get("maxActive") or 1))
        current_active = sum(
            1 for row in self._state.get("active") or [] if row.get("templateId") == tid
        )
        if current_active >= max_active:
            return False
        return True

    def _offer_template(self, tmpl: dict, *, source: dict[str, Any]) -> dict[str, Any] | None:
        if not tmpl or not self._eligible_for_template(tmpl):
            return None

        source_key = str(source.get("sourceKey") or "").strip()
        if source_key and self._should_mark_source_seen(source) and self._source_seen(source_key):
            return None

        tid = tmpl["id"]
        for row in self._state.get("opportunities") or []:
            if row.get("templateId") == tid and row.get("sourceKey") == source_key:
                if source_key and self._should_mark_source_seen(source):
                    self._mark_source_seen(source_key)
                return None

        if self._has_active_template(tid) and not source_key:
            return None

        opportunity = {
            "id": f"opp-{uuid.uuid4().hex[:12]}",
            "templateId": tid,
            "title": tmpl.get("title") or tid,
            "summary": tmpl.get("summary") or "",
            "storylineId": tmpl.get("storylineId") or "",
            "threadId": tmpl.get("threadId") or "",
            "giver": dict(tmpl.get("giver") or {}),
            "source": dict(source or {}),
            "sourceKey": source_key,
            "createdAt": to_iso(utc_now()),
        }
        ops = list(self._state.get("opportunities") or [])
        ops.append(opportunity)
        self._state["opportunities"] = ops[-100:]
        if source_key and self._should_mark_source_seen(source):
            self._mark_source_seen(source_key)
        self._save()
        return opportunity

    def sync_global_seeds(self) -> list[dict[str, Any]]:
        created = []
        script = get_mission_seeds_script(create_missing=True)
        if not script:
            return created
        for seed in script.live_rows(limit=200):
            for tmpl in matching_templates_for_seed(seed):
                row = self._offer_template(
                    tmpl,
                    source={
                        "kind": seed.get("kind"),
                        "seedId": seed.get("seedId"),
                        "sourceKey": seed.get("sourceKey"),
                        "payload": dict(seed.get("payload") or {}),
                    },
                )
                if row:
                    created.append(row)
        return created

    def sync_room(self, room) -> list[dict[str, Any]]:
        created = []
        if not room:
            return created
        for tmpl in matching_templates_for_room(room):
            row = self._offer_template(
                tmpl,
                source={
                    "kind": "room",
                    "roomKey": room.key,
                    "sourceKey": f"room:{room.key}:{tmpl['id']}",
                },
            )
            if row:
                created.append(row)
        self._progress_visit_room(room)
        return created

    def sync_interaction(self, interaction_key: str) -> list[dict[str, Any]]:
        created = []
        ikey = str(interaction_key or "").strip().lower()
        if not ikey:
            return created
        for tmpl in matching_templates_for_interaction(ikey):
            row = self._offer_template(
                tmpl,
                source={
                    "kind": "interaction",
                    "interactionKey": ikey,
                    "sourceKey": f"interaction:{ikey}:{tmpl['id']}",
                },
            )
            if row:
                created.append(row)
        self._progress_interaction(ikey)
        return created

    def accept(self, opportunity_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        opp = self._find_opportunity(opportunity_id)
        if not opp:
            return False, "Mission opportunity not found.", None

        tmpl = get_mission_template(opp.get("templateId") or "")
        if not tmpl:
            return False, "Mission template missing.", None

        mission = {
            "id": f"mis-{uuid.uuid4().hex[:12]}",
            "templateId": tmpl["id"],
            "title": tmpl.get("title") or tmpl["id"],
            "summary": tmpl.get("summary") or "",
            "storylineId": tmpl.get("storylineId") or "",
            "threadId": tmpl.get("threadId") or "",
            "giver": dict(tmpl.get("giver") or {}),
            "source": dict(opp.get("source") or {}),
            "sourceKey": opp.get("sourceKey") or "",
            "status": "active",
            "objectiveIndex": 0,
            "completedObjectiveIds": [],
            "choices": [],
            "createdAt": opp.get("createdAt") or to_iso(utc_now()),
            "acceptedAt": to_iso(utc_now()),
            "completedAt": None,
        }

        self._state["opportunities"] = [
            row
            for row in list(self._state.get("opportunities") or [])
            if row.get("id") != opportunity_id
        ]
        active = list(self._state.get("active") or [])
        active.append(mission)
        self._state["active"] = active[-50:]
        self._save()
        return True, f"Accepted mission: {mission['title']}.", mission

    def _current_objective(self, mission: dict, tmpl: dict) -> dict[str, Any] | None:
        idx = int(mission.get("objectiveIndex") or 0)
        objectives = list(tmpl.get("objectives") or [])
        if idx < 0 or idx >= len(objectives):
            return None
        return objectives[idx]

    def _set_objective_index_by_id(self, mission: dict, tmpl: dict, objective_id: str) -> bool:
        for idx, obj in enumerate(list(tmpl.get("objectives") or [])):
            if obj.get("id") == objective_id:
                mission["objectiveIndex"] = idx
                return True
        return False

    def _complete_objective_and_advance(
        self,
        mission: dict,
        tmpl: dict,
        objective: dict,
        *,
        choice: dict[str, Any] | None = None,
    ) -> None:
        done = list(mission.get("completedObjectiveIds") or [])
        if objective.get("id") not in done:
            done.append(objective["id"])
            mission["completedObjectiveIds"] = done

        if choice and choice.get("nextObjectiveId"):
            if self._set_objective_index_by_id(mission, tmpl, choice["nextObjectiveId"]):
                return

        mission["objectiveIndex"] = int(mission.get("objectiveIndex") or 0) + 1
        if mission["objectiveIndex"] >= len(list(tmpl.get("objectives") or [])) or bool(
            (choice or {}).get("completeMission")
        ):
            self._complete_mission(mission, tmpl, choice=choice)

    def _complete_mission(self, mission: dict, tmpl: dict, *, choice: dict[str, Any] | None = None) -> None:
        rewards = dict(tmpl.get("rewards") or {})
        rewards.update(dict((choice or {}).get("rewards") or {}))
        self._apply_rewards(rewards)

        mission["status"] = "completed"
        mission["completedAt"] = to_iso(utc_now())

        cooldowns = dict(self._state.get("cooldowns") or {})
        cooldowns[tmpl["id"]] = to_iso(utc_now())
        self._state["cooldowns"] = cooldowns

        self._state["active"] = [
            row for row in list(self._state.get("active") or []) if row.get("id") != mission.get("id")
        ]
        completed = list(self._state.get("completed") or [])
        completed.append(dict(mission))
        self._state["completed"] = completed[-200:]

        for followup_id in list((choice or {}).get("unlockTemplateIds") or []):
            next_tmpl = get_mission_template(followup_id)
            if next_tmpl:
                self._offer_template(
                    next_tmpl,
                    source={
                        "kind": "followup",
                        "sourceKey": f"followup:{mission['id']}:{followup_id}",
                    },
                )

    def _progress_visit_room(self, room) -> None:
        if not room:
            return
        room_key = str(room.key or "")
        changed = False
        for mission in list(self._state.get("active") or []):
            tmpl = get_mission_template(mission.get("templateId") or "")
            if not tmpl:
                continue
            objective = self._current_objective(mission, tmpl)
            if not objective or objective.get("kind") != "visit_room":
                continue
            if room_key in set(objective.get("roomKeysAny") or []):
                self._complete_objective_and_advance(mission, tmpl, objective)
                changed = True
        if changed:
            self._save()

    def _progress_interaction(self, interaction_key: str) -> None:
        changed = False
        for mission in list(self._state.get("active") or []):
            tmpl = get_mission_template(mission.get("templateId") or "")
            if not tmpl:
                continue
            objective = self._current_objective(mission, tmpl)
            if not objective or objective.get("kind") != "interaction":
                continue
            valid = {str(v).strip().lower() for v in list(objective.get("interactionKeysAny") or [])}
            if interaction_key in valid:
                self._complete_objective_and_advance(mission, tmpl, objective)
                changed = True
        if changed:
            self._save()

    def choose(self, mission_id: str, choice_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        mission = self._find_active(mission_id)
        if not mission:
            return False, "Active mission not found.", None

        tmpl = get_mission_template(mission.get("templateId") or "")
        if not tmpl:
            return False, "Mission template missing.", None

        objective = self._current_objective(mission, tmpl)
        if not objective or objective.get("kind") != "choice":
            return False, "This mission is not waiting on a decision.", None

        choice = None
        for row in list(objective.get("choices") or []):
            if row.get("id") == choice_id:
                choice = row
                break
        if not choice:
            return False, "Choice not found.", None

        choice_log = list(mission.get("choices") or [])
        choice_log.append(
            {
                "objectiveId": objective.get("id"),
                "choiceId": choice.get("id"),
                "chosenAt": to_iso(utc_now()),
                "outcome": choice.get("outcome") or "",
            }
        )
        mission["choices"] = choice_log
        self._apply_morality(dict(choice.get("morality") or {}))
        self._complete_objective_and_advance(mission, tmpl, objective, choice=choice)
        self._save()
        return True, choice.get("outcome") or "Decision recorded.", mission

    def serialize_for_web(self) -> dict[str, Any]:
        def active_payload(row):
            tmpl = get_mission_template(row.get("templateId") or "") or {}
            objective = self._current_objective(row, tmpl) if tmpl else None
            return {
                "id": row.get("id"),
                "templateId": row.get("templateId"),
                "title": row.get("title"),
                "summary": row.get("summary"),
                "storylineId": row.get("storylineId"),
                "threadId": row.get("threadId"),
                "status": row.get("status"),
                "createdAt": row.get("createdAt"),
                "acceptedAt": row.get("acceptedAt"),
                "completedAt": row.get("completedAt"),
                "currentObjective": {
                    "id": objective.get("id"),
                    "kind": objective.get("kind"),
                    "text": objective.get("text"),
                    "prompt": objective.get("prompt"),
                    "choices": objective.get("choices"),
                    "roomKeysAny": list(objective.get("roomKeysAny") or []),
                    "interactionKeysAny": list(objective.get("interactionKeysAny") or []),
                }
                if objective
                else None,
                "choices": list(row.get("choices") or []),
            }

        return {
            "morality": dict(self._state.get("morality") or {}),
            "opportunities": [dict(row) for row in list(self._state.get("opportunities") or [])[-20:]],
            "active": [active_payload(row) for row in list(self._state.get("active") or [])[-20:]],
            "completed": [dict(row) for row in list(self._state.get("completed") or [])[-30:]],
        }
