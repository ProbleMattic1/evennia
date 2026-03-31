"""
SpaceEngagement: persistent Script managing one active starship dogfight.

Lifecycle:
  create_space_engagement(alpha_char, alpha_vehicle, bravo_config)
    → script.db.state   — full engagement state dict
    → script.db.character_sides  — {character_id: "alpha"|"bravo"}

The tick loop advances the engagement, runs NPC policies, broadcasts
narrative + structured snapshots to all participants.

Characters store their active engagement key in db.active_space_engagement_id
so combat commands can find this script quickly.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

from evennia import create_script, search_script
from evennia.utils import logger

from typeclasses.scripts import Script
from world.space_engagement_hooks import (
    apply_engagement_close_to_participants,
    apply_engagement_events_to_participants,
)
from world.space_combat_resolve import (
    RANGE_BANDS,
    RANGE_STANDOFF,
    apply_ew,
    apply_maneuver,
    apply_weapon,
    make_actor,
    make_state,
    npc_choose_action,
    tick,
)

ENGAGEMENT_TICK_INTERVAL = 4  # seconds; tune for telnet/web mix
MAX_TICKS = 120  # 8 minutes cap; prevents zombie engagements


def create_space_engagement(
    alpha_character,
    alpha_vehicle,
    bravo_config: dict[str, Any],
) -> "SpaceEngagement":
    """
    Convenience factory. bravo_config must have keys:
      vehicle_combat (dict) — the db.combat snapshot for the enemy ship
      ai_policy_id (str)    — "aggressive" | "defensive" | "balanced"
      label (str)           — display name for the enemy
    """
    eng_id = uuid.uuid4().hex[:10]
    script = create_script(
        "typeclasses.space_engagement.SpaceEngagement",
        key=f"space_engagement_{eng_id}",
    )
    alpha_combat = dict(alpha_vehicle.db.combat or {}) if alpha_vehicle else {}
    alpha_actor = make_actor(
        actor_id=f"alpha_{eng_id}",
        side="alpha",
        combat=alpha_combat,
        character_id=alpha_character.id,
        vehicle_id=alpha_vehicle.id if alpha_vehicle else None,
    )
    bravo_actor = make_actor(
        actor_id=f"bravo_{eng_id}",
        side="bravo",
        combat=dict(bravo_config.get("vehicle_combat") or {}),
        role="npc",
        ai_policy_id=str(bravo_config.get("ai_policy_id") or "balanced"),
    )
    state = make_state(
        [alpha_actor, bravo_actor],
        range_band=RANGE_STANDOFF,
    )
    script.db.state = state
    script.db.engagement_id = eng_id
    script.db.character_sides = {str(alpha_character.id): "alpha"}
    script.db.bravo_label = str(bravo_config.get("label") or "Hostile")
    script.db.bravo_profile_key = str(bravo_config.get("profile_key") or "").strip().lower()
    script.db.participants = [alpha_character]
    alpha_character.db.active_space_engagement_id = script.key
    script.start()
    return script


def get_engagement_for_character(character) -> "SpaceEngagement | None":
    eng_key = getattr(character.db, "active_space_engagement_id", None)
    if not eng_key:
        return None
    found = search_script(eng_key)
    return found[0] if found else None


class SpaceEngagement(Script):

    def at_script_creation(self):
        self.key = "space_engagement_new"
        self.desc = "Active starship engagement."
        self.persistent = True
        self.interval = ENGAGEMENT_TICK_INTERVAL
        self.start_delay = True
        self.repeats = MAX_TICKS

    # ------------------------------------------------------------------
    # Public API used by commands
    # ------------------------------------------------------------------

    def player_action(self, character, action_type: str, action_name: str) -> list[dict]:
        """
        Apply a player action; return the events list.
        Broadcasts results to all participants.
        """
        state = dict(self.db.state or {})
        if state.get("closed"):
            character.msg("|y[Space]|n This engagement has already ended.")
            return []

        actor_id = self._actor_id_for_character(character)
        if not actor_id:
            character.msg("|r[Space]|n You are not in this engagement.")
            return []

        r = random.Random(int(state.get("rng_seed") or 0) ^ state.get("tick", 0) ^ character.id)

        if action_type == "maneuver":
            new_state, events = apply_maneuver(state, actor_id, action_name, rng=r)
        elif action_type == "ew":
            new_state, events = apply_ew(state, actor_id, action_name, rng=r)
        elif action_type == "weapon":
            new_state, events = apply_weapon(state, actor_id, action_name, rng=r)
        else:
            character.msg(f"|r[Space]|n Unknown action type: {action_type}")
            return []

        self.db.state = new_state
        self._broadcast_events(events)
        apply_engagement_events_to_participants(
            list(self.db.participants or []), events, new_state
        )
        self._check_close(new_state)
        return events

    def status_lines(self) -> list[str]:
        """Formatted status for the `vstatus` command."""
        state = dict(self.db.state or {})
        actors = state.get("actors") or []
        _rb = state.get("range_band")
        band = RANGE_BANDS[int(_rb if _rb is not None else RANGE_STANDOFF)]
        closing = state.get("closing") or "neutral"
        aspect = state.get("aspect") or "neutral"
        tick_n = state.get("tick") or 0

        lines = [
            f"|w[Space Engagement]|n  Tick {tick_n}  |  Range: |c{band}|n  |  Closure: {closing}  |  Aspect: {aspect}",
            "",
        ]
        for actor in actors:
            if actor.get("eliminated"):
                tag = "|r[ELIMINATED]|n"
            else:
                tag = f"hull |g{actor['hull_pct']}%|n  shields |c{actor.get('shield_pct', 0)}%|n  heat |y{actor.get('heat', 0)}|n"
            label = self._actor_label(actor)
            tubes = len(actor.get("tube_timers") or [])
            lock = actor.get("lock_quality") or 0
            pdc = "|gPDC ON|n" if actor.get("pdc_posture") else "PDC off"
            lines.append(
                f"  {label:20s} {tag}  lock={lock}/3  tubes={tubes}  {pdc}"
            )
        return lines

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    def at_repeat(self):
        state = dict(self.db.state or {})
        if state.get("closed"):
            self.stop()
            return

        # NPC policies
        state, npc_events = self._run_npc_policies(state)
        self._broadcast_events(npc_events)
        apply_engagement_events_to_participants(
            list(self.db.participants or []), npc_events, state
        )

        # Global tick advance
        r = random.Random(int(state.get("rng_seed") or 0) ^ state.get("tick", 0))
        new_state, tick_events = tick(state, rng=r)
        self.db.state = new_state
        self._broadcast_events(tick_events)
        apply_engagement_events_to_participants(
            list(self.db.participants or []), tick_events, new_state
        )
        self._broadcast_snapshot(new_state)
        self._check_close(new_state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_npc_policies(self, state: dict) -> tuple[dict, list[dict]]:
        all_events: list[dict] = []
        for actor in state.get("actors") or []:
            if actor.get("eliminated") or actor.get("role") != "npc":
                continue
            r = random.Random(int(state.get("rng_seed") or 0) ^ state.get("tick", 0) ^ hash(actor["id"]))
            action_type, action_name = npc_choose_action(state, actor["id"], rng=r)
            if action_type == "maneuver":
                state, events = apply_maneuver(state, actor["id"], action_name, rng=r)
            elif action_type == "ew":
                state, events = apply_ew(state, actor["id"], action_name, rng=r)
            elif action_type == "weapon":
                state, events = apply_weapon(state, actor["id"], action_name, rng=r)
            else:
                events = []
            all_events.extend(events)
        return state, all_events

    def _check_close(self, state: dict) -> None:
        if state.get("closed"):
            self._broadcast_end(state)
            self._clear_participant_engagement_ids()
            self.stop()

    def _clear_participant_engagement_ids(self) -> None:
        for char in list(self.db.participants or []):
            try:
                if char and char.db.active_space_engagement_id == self.key:
                    char.db.active_space_engagement_id = None
            except Exception:
                pass

    def _actor_id_for_character(self, character) -> str | None:
        sides = dict(self.db.character_sides or {})
        if str(character.id) in sides:
            state = dict(self.db.state or {})
            for actor in state.get("actors") or []:
                if actor.get("character_id") == character.id:
                    return actor["id"]
        return None

    def _actor_label(self, actor: dict) -> str:
        if actor.get("role") == "npc":
            return str(self.db.bravo_label or "Hostile")
        sides = dict(self.db.character_sides or {})
        char_id = actor.get("character_id")
        if char_id:
            for char in list(self.db.participants or []):
                if char and char.id == char_id:
                    return char.key
        return actor.get("id") or "Unknown"

    def _broadcast_events(self, events: list[dict]) -> None:
        """Translate resolver events into narrative messages to all participants."""
        for ev in events:
            kind = ev.get("kind") or ""
            msg = self._event_to_text(ev)
            if msg:
                for char in list(self.db.participants or []):
                    if char:
                        char.msg(f"|w[Space]|n {msg}")

    def _broadcast_snapshot(self, state: dict) -> None:
        """Push the engagement snapshot via msg options for the web client."""
        snap = self._make_snapshot(state)
        for char in list(self.db.participants or []):
            if char and char.sessions.count():
                char.msg("", options={"space_engagement": snap})

    def _broadcast_end(self, state: dict) -> None:
        tags = state.get("mission_tags") or []
        victor_tag = next((t for t in tags if t.startswith("victor:")), None)
        victor = victor_tag.split(":")[1] if victor_tag else "unknown"
        msg = f"|wEngagement closed.|n Victor: |c{victor}|n"
        for char in list(self.db.participants or []):
            if char:
                char.msg(f"|w[Space]|n {msg}")
                # Advance engagement-type mission objectives
                try:
                    char.missions._progress_engagement(state)
                except Exception as exc:
                    logger.log_err(f"[space_engagement] mission progress error for {char.key}: {exc}")
        apply_engagement_close_to_participants(
            list(self.db.participants or []),
            state,
            bravo_profile_key=str(getattr(self.db, "bravo_profile_key", "") or ""),
        )

    def _event_to_text(self, ev: dict) -> str:
        kind = ev.get("kind") or ""
        actor_id = ev.get("actor_id") or ""
        target_id = ev.get("target_id") or ""
        state = dict(self.db.state or {})

        def label(aid):
            for a in state.get("actors") or []:
                if a.get("id") == aid:
                    return self._actor_label(a)
            return aid

        templates = {
            "maneuver": lambda e: (
                f"|c{label(e['actor_id'])}|n executes |y{e['maneuver']}|n. "
                f"Range now: |w{RANGE_BANDS[int(state.get('range_band') if state.get('range_band') is not None else 3)]}|n."
            ),
            "kinetic_hit": lambda e: (
                f"|c{label(e['actor_id'])}|n scores a kinetic hit on |r{label(e['target_id'])}|n — "
                f"hull |r{e['hull_pct']}%|n."
            ),
            "kinetic_miss": lambda e: (
                f"|c{label(e['actor_id'])}|n fires — shot goes wide."
            ),
            "missile_launched": lambda e: (
                f"|c{label(e['actor_id'])}|n launches — "
                f"|yFOX|n inbound, time-to-go |w{e['time_to_go']}|n ticks."
            ),
            "missile_hit": lambda e: (
                f"|rMissile impact on {label(e['target_id'])}|n — hull |r{e['hull_pct']}%|n."
            ),
            "missile_defeated": lambda e: (
                f"PDC intercept — missile |gdefeated|n before impact on {label(e['target_id'])}."
            ),
            "actor_eliminated": lambda e: (
                f"|r{label(e['actor_id'])} eliminated|n ({e['cause']})."
            ),
            "side_eliminated": lambda e: (
                f"|wEngagement over.|n Side |r{e['side']}|n eliminated. Victor: |g{e['victor']}|n."
            ),
            "lock_broken": lambda e: (
                f"|c{label(e['actor_id'])}|n breaks lock — emcon restored."
            ),
            "heat_warning": lambda e: (
                f"|y[HEAT WARNING]|n {label(e['actor_id'])} — reactor at |y{e['heat']}%|n."
            ),
            "heat_critical": lambda e: (
                f"|r[OVERLOAD]|n {label(e['actor_id'])} hull stress — hull |r{e['hull_pct']}%|n."
            ),
            "ew_ghost_success": lambda e: (
                f"|c{label(e['actor_id'])}|n ghosts — enemy lock degraded."
            ),
            "ew_ghost_failed": lambda e: (
                f"|c{label(e['actor_id'])}|n ghost attempt failed — still painted."
            ),
            "ew_seduction_success": lambda e: (
                f"Seduction feint by |c{label(e['actor_id'])}|n — enemy lock diverted."
            ),
            "ew_seduction_failed": lambda e: (
                f"Seduction by |c{label(e['actor_id'])}|n burned through — enemy lock holds."
            ),
            "ew_spike": lambda e: (
                f"|c{label(e['actor_id'])}|n spikes signature — enemy lock climbs."
            ),
            "aspect_change": lambda e: (
                f"|c{label(e['actor_id'])}|n jinks into |g{e['aspect']}|n aspect."
            ),
            "pdc_posture_toggle": lambda e: (
                f"|c{label(e['actor_id'])}|n PDC posture: |{'gON' if e['active'] else 'rOFF'}|n."
            ),
        }
        fn = templates.get(kind)
        if fn:
            try:
                return fn(ev)
            except Exception:
                return f"[{kind}]"
        if kind == "error":
            return f"|r[Error]|n {ev.get('msg')}"
        return ""

    def _make_snapshot(self, state: dict) -> dict:
        """Compact dict for web client consumption."""
        _rb = state.get("range_band")
        band = RANGE_BANDS[int(_rb if _rb is not None else RANGE_STANDOFF)]
        actors_out = []
        for actor in state.get("actors") or []:
            actors_out.append({
                "id": actor.get("id"),
                "label": self._actor_label(actor),
                "side": actor.get("side"),
                "hull_pct": actor.get("hull_pct"),
                "shield_pct": actor.get("shield_pct"),
                "heat": actor.get("heat"),
                "lock_quality": actor.get("lock_quality"),
                "pdc_posture": actor.get("pdc_posture"),
                "tube_count": len(actor.get("tube_timers") or []),
                "eliminated": actor.get("eliminated"),
            })
        return {
            "tick": state.get("tick"),
            "range_band": band,
            "closing": state.get("closing"),
            "aspect": state.get("aspect"),
            "closed": state.get("closed"),
            "actors": actors_out,
        }
