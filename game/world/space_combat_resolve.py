"""
Pure combat resolver for space engagements — no Evennia imports.

All functions take plain dicts and return (new_state, events_list).
Events are dicts with a required 'kind' key; callers dispatch them.

Range bands (ascending distance):
  merge (0) → knife (1) → medium (2) → standoff (3)

Closing direction: "in" | "out" | "neutral"
Aspect:           "advantage" | "neutral" | "disadvantage"

Actor dict keys:
  id, side ("alpha"|"bravo"), role, hull_pct (0–100), shield_pct (0–100),
  heat (0–100), emcon (0–3: cold/quiet/normal/hot), lock_quality (0–3),
  tube_timers (list of int ticks remaining), ai_policy_id (str|None),
  combat (dict snapshot from vehicle db.combat)
"""

from __future__ import annotations

import copy
import random
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANGE_BANDS = ("merge", "knife", "medium", "standoff")
RANGE_MERGE, RANGE_KNIFE, RANGE_MEDIUM, RANGE_STANDOFF = range(4)

HEAT_OVERLOAD = 85
HEAT_CRITICAL = 95

MANEUVERS = frozenset({"burn_in", "burn_out", "plane_change", "cold_coast", "jink"})
EW_ACTIONS = frozenset({"spike", "ghost", "seduction"})
WEAPON_ACTIONS = frozenset({"kinetic_squeeze", "fox_missile", "pdc_posture"})

_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def make_actor(
    actor_id: str,
    side: str,
    combat: dict,
    *,
    role: str = "fighter",
    character_id: int | None = None,
    vehicle_id: int | None = None,
    ai_policy_id: str | None = None,
) -> dict[str, Any]:
    """Build a fresh actor snapshot from a vehicle db.combat dict."""
    hp = max(1, int(combat.get("hp") or 100))
    shields = max(0, int(combat.get("shields") or 0))
    return {
        "id": actor_id,
        "side": side,
        "role": role,
        "character_id": character_id,
        "vehicle_id": vehicle_id,
        "hull_pct": 100,
        "shield_pct": 100 if shields > 0 else 0,
        "hp_max": hp,
        "shield_max": shields,
        "heat": 0,
        "emcon": 2,
        "lock_quality": 0,
        "tube_timers": [],
        "pdc_posture": False,
        "ai_policy_id": ai_policy_id,
        "combat": dict(combat),
        "eliminated": False,
    }


def make_state(
    actors: list[dict],
    *,
    rng_seed: int | None = None,
    range_band: int = RANGE_STANDOFF,
    closing: str = "neutral",
    aspect: str = "neutral",
) -> dict[str, Any]:
    """Initialise a fresh engagement state."""
    seed = rng_seed if rng_seed is not None else random.getrandbits(32)
    return {
        "schema_version": _SCHEMA_VERSION,
        "tick": 0,
        "closed": False,
        "range_band": range_band,
        "closing": closing,
        "aspect": aspect,
        "actors": [dict(a) for a in actors],
        "rng_seed": seed,
        "rng_log": [],
        "event_log": [],
        "mission_tags": [],
    }


def _log_roll(state: dict, tick: int, action: str, roll: float, context: str = "") -> None:
    state["rng_log"] = (state.get("rng_log") or [])[-49:]
    state["rng_log"].append({"tick": tick, "action": action, "roll": round(roll, 4), "ctx": context})


def _find_actor(state: dict, actor_id: str) -> dict | None:
    for a in state.get("actors") or []:
        if a.get("id") == actor_id:
            return a
    return None


def _active_actors(state: dict) -> list[dict]:
    return [a for a in (state.get("actors") or []) if not a.get("eliminated")]


def _side_actors(state: dict, side: str) -> list[dict]:
    return [a for a in _active_actors(state) if a.get("side") == side]


# ---------------------------------------------------------------------------
# Core tick
# ---------------------------------------------------------------------------

def tick(state: dict, rng: random.Random | None = None) -> tuple[dict, list[dict]]:
    """
    Advance one game tick.

    Returns (updated_state, events).
    Events drive mission hooks, messaging, and web snapshots.
    """
    s = copy.deepcopy(state)
    s["tick"] = int(s.get("tick") or 0) + 1
    events: list[dict] = []
    r = rng or random.Random(int(s["rng_seed"]) ^ s["tick"])

    # Advance missile timers
    for actor in s["actors"]:
        if actor.get("eliminated"):
            continue
        new_timers = []
        for timer in list(actor.get("tube_timers") or []):
            remaining = int(timer) - 1
            if remaining <= 0:
                roll = r.random()
                _log_roll(s, s["tick"], "missile_impact", roll, actor["id"])
                events.extend(_resolve_missile_impact(s, actor, roll))
            else:
                new_timers.append(remaining)
        actor["tube_timers"] = new_timers

    # Passive heat bleed
    for actor in s["actors"]:
        if actor.get("eliminated"):
            continue
        bleed = 5 if int(actor.get("emcon") or 2) >= 3 else 3
        actor["heat"] = max(0, int(actor.get("heat") or 0) - bleed)

    # Lock quality decay (sensors degrade without active painting)
    for actor in s["actors"]:
        if actor.get("eliminated") or actor.get("lock_quality", 0) <= 0:
            continue
        actor["lock_quality"] = max(0, int(actor["lock_quality"]) - 1)

    # Check victory / collapse conditions
    events.extend(_check_conditions(s))

    if _is_over(s):
        s["closed"] = True

    return s, events


def _resolve_missile_impact(state: dict, launcher: dict, roll: float) -> list[dict]:
    """Resolve a missile reaching its target."""
    events: list[dict] = []
    targets = _side_actors(state, "bravo" if launcher.get("side") == "alpha" else "alpha")
    if not targets:
        return events
    target = targets[0]

    pdc_chance = 0.45 if target.get("pdc_posture") else 0.15
    sensors = int((target.get("combat") or {}).get("sensors") or 5)
    pdc_chance += min(0.3, sensors * 0.02)

    if roll < pdc_chance:
        events.append({"kind": "missile_defeated", "target_id": target["id"], "roll": roll})
        return events

    armor = int((target.get("combat") or {}).get("armor") or 0)
    base_damage_pct = max(5, 25 - armor)
    shield_absorb = min(int(target.get("shield_pct") or 0), base_damage_pct)
    hull_damage_pct = max(0, base_damage_pct - shield_absorb)

    target["shield_pct"] = max(0, int(target["shield_pct"]) - shield_absorb)
    target["hull_pct"] = max(0, int(target["hull_pct"]) - hull_damage_pct)

    events.append({
        "kind": "missile_hit",
        "target_id": target["id"],
        "hull_damage": hull_damage_pct,
        "shield_damage": shield_absorb,
        "hull_pct": target["hull_pct"],
    })

    if target["hull_pct"] <= 0:
        target["eliminated"] = True
        events.append({"kind": "actor_eliminated", "actor_id": target["id"], "cause": "missile"})

    return events


def _check_conditions(state: dict) -> list[dict]:
    events: list[dict] = []
    for side in ("alpha", "bravo"):
        if not _side_actors(state, side):
            opposite = "bravo" if side == "alpha" else "alpha"
            events.append({"kind": "side_eliminated", "side": side, "victor": opposite})
            state["mission_tags"] = list(state.get("mission_tags") or []) + [
                f"victor:{opposite}", "engagement_over"
            ]
    return events


def _is_over(state: dict) -> bool:
    return not _side_actors(state, "alpha") or not _side_actors(state, "bravo")


# ---------------------------------------------------------------------------
# Player / NPC action resolvers
# ---------------------------------------------------------------------------

def apply_maneuver(
    state: dict,
    actor_id: str,
    maneuver: str,
    rng: random.Random | None = None,
) -> tuple[dict, list[dict]]:
    """
    Apply a maneuver command and return (new_state, events).

    burn_in    — close range, spike heat and signature
    burn_out   — open range, spike heat
    plane_change — break lock on self, moderate heat
    cold_coast — minimal signature, cannot attack this tick
    jink       — evade: raise aspect advantage, raise heat
    """
    s = copy.deepcopy(state)
    events: list[dict] = []
    r = rng or random.Random(int(s["rng_seed"]) ^ s["tick"])
    actor = _find_actor(s, actor_id)
    if not actor or actor.get("eliminated"):
        return s, [{"kind": "error", "msg": f"actor {actor_id!r} not found or eliminated"}]
    if maneuver not in MANEUVERS:
        return s, [{"kind": "error", "msg": f"unknown maneuver {maneuver!r}"}]

    agility = int((actor.get("combat") or {}).get("agility") or 5)
    _rb = s.get("range_band")
    band = int(_rb if _rb is not None else RANGE_STANDOFF)

    if maneuver == "burn_in":
        if band > RANGE_MERGE:
            s["range_band"] = band - 1
            s["closing"] = "in"
        actor["heat"] = min(100, int(actor.get("heat") or 0) + 18)
        actor["emcon"] = 3
        events.append({"kind": "maneuver", "actor_id": actor_id, "maneuver": maneuver,
                        "range_band": s["range_band"]})

    elif maneuver == "burn_out":
        if band < RANGE_STANDOFF:
            s["range_band"] = band + 1
            s["closing"] = "out"
        actor["heat"] = min(100, int(actor.get("heat") or 0) + 18)
        actor["emcon"] = 3
        events.append({"kind": "maneuver", "actor_id": actor_id, "maneuver": maneuver,
                        "range_band": s["range_band"]})

    elif maneuver == "plane_change":
        roll = r.random()
        _log_roll(s, s["tick"], "plane_change", roll, actor_id)
        if roll < (0.3 + agility * 0.04):
            actor["lock_quality"] = 0
            events.append({"kind": "lock_broken", "actor_id": actor_id})
        actor["heat"] = min(100, int(actor.get("heat") or 0) + 10)
        events.append({"kind": "maneuver", "actor_id": actor_id, "maneuver": maneuver})

    elif maneuver == "cold_coast":
        actor["heat"] = max(0, int(actor.get("heat") or 0) - 15)
        actor["emcon"] = 0
        actor["_cold_coast_this_tick"] = True
        events.append({"kind": "maneuver", "actor_id": actor_id, "maneuver": maneuver})

    elif maneuver == "jink":
        roll = r.random()
        _log_roll(s, s["tick"], "jink", roll, actor_id)
        if roll < (0.4 + agility * 0.05):
            s["aspect"] = "advantage"
            events.append({"kind": "aspect_change", "aspect": "advantage", "actor_id": actor_id})
        actor["heat"] = min(100, int(actor.get("heat") or 0) + 8)
        events.append({"kind": "maneuver", "actor_id": actor_id, "maneuver": maneuver})

    # Overload warning
    if int(actor.get("heat") or 0) >= HEAT_OVERLOAD:
        events.append({"kind": "heat_warning", "actor_id": actor_id, "heat": actor["heat"]})
    if int(actor.get("heat") or 0) >= HEAT_CRITICAL:
        actor["hull_pct"] = max(0, int(actor.get("hull_pct") or 100) - 10)
        events.append({"kind": "heat_critical", "actor_id": actor_id,
                        "hull_pct": actor["hull_pct"]})
        if actor["hull_pct"] <= 0:
            actor["eliminated"] = True
            events.append({"kind": "actor_eliminated", "actor_id": actor_id, "cause": "overload"})

    return s, events


def apply_ew(
    state: dict,
    actor_id: str,
    action: str,
    rng: random.Random | None = None,
) -> tuple[dict, list[dict]]:
    """
    Apply an EW action and return (new_state, events).

    spike      — force enemy lock_quality up (they have a firing window on you)
    ghost      — attempt to break an enemy lock (stealth + sensors contest)
    seduction  — decoy feint: spoof enemy lock off the real target
    """
    s = copy.deepcopy(state)
    events: list[dict] = []
    r = rng or random.Random(int(s["rng_seed"]) ^ s["tick"] ^ 7)
    actor = _find_actor(s, actor_id)
    if not actor or actor.get("eliminated"):
        return s, [{"kind": "error", "msg": f"actor {actor_id!r} not found or eliminated"}]
    if action not in EW_ACTIONS:
        return s, [{"kind": "error", "msg": f"unknown EW action {action!r}"}]

    stealth = int((actor.get("combat") or {}).get("stealth") or 5)
    sensors = int((actor.get("combat") or {}).get("sensors") or 5)
    opponent_side = "bravo" if actor.get("side") == "alpha" else "alpha"
    opponents = _side_actors(s, opponent_side)

    if action == "spike":
        # Reveal yourself hard: enemy lock climbs
        actor["emcon"] = 3
        for opp in opponents:
            opp["lock_quality"] = min(3, int(opp.get("lock_quality") or 0) + 2)
        events.append({"kind": "ew_spike", "actor_id": actor_id})

    elif action == "ghost":
        roll = r.random()
        _log_roll(s, s["tick"], "ghost", roll, actor_id)
        success_chance = 0.3 + stealth * 0.04
        if roll < success_chance:
            for opp in opponents:
                opp["lock_quality"] = max(0, int(opp.get("lock_quality") or 0) - 2)
            actor["emcon"] = max(0, int(actor.get("emcon") or 2) - 1)
            events.append({"kind": "ew_ghost_success", "actor_id": actor_id, "roll": roll})
        else:
            events.append({"kind": "ew_ghost_failed", "actor_id": actor_id, "roll": roll})

    elif action == "seduction":
        roll = r.random()
        _log_roll(s, s["tick"], "seduction", roll, actor_id)
        contest = 0.25 + stealth * 0.03 - sum(
            int(o.get("combat", {}).get("sensors") or 5) * 0.01 for o in opponents
        )
        if roll < max(0.05, contest):
            for opp in opponents:
                opp["lock_quality"] = max(0, int(opp.get("lock_quality") or 0) - 1)
            events.append({"kind": "ew_seduction_success", "actor_id": actor_id, "roll": roll})
        else:
            events.append({"kind": "ew_seduction_failed", "actor_id": actor_id, "roll": roll})

    return s, events


def apply_weapon(
    state: dict,
    actor_id: str,
    action: str,
    rng: random.Random | None = None,
) -> tuple[dict, list[dict]]:
    """
    Apply a weapon action and return (new_state, events).

    kinetic_squeeze  — direct fire at current range; hit chance depends on lock + band
    fox_missile      — launch a missile (adds a timer to actor's tube_timers)
    pdc_posture      — toggle point-defence readiness (costs emcon, reduces tube capacity)
    """
    s = copy.deepcopy(state)
    events: list[dict] = []
    r = rng or random.Random(int(s["rng_seed"]) ^ s["tick"] ^ 13)
    actor = _find_actor(s, actor_id)
    if not actor or actor.get("eliminated"):
        return s, [{"kind": "error", "msg": f"actor {actor_id!r} not found or eliminated"}]
    if action not in WEAPON_ACTIONS:
        return s, [{"kind": "error", "msg": f"unknown weapon action {action!r}"}]

    combat = actor.get("combat") or {}
    opponent_side = "bravo" if actor.get("side") == "alpha" else "alpha"
    opponents = _side_actors(s, opponent_side)
    if not opponents:
        return s, [{"kind": "error", "msg": "no opponents remaining"}]
    target = opponents[0]

    if action == "kinetic_squeeze":
        _rb = s.get("range_band")
        band = int(_rb if _rb is not None else RANGE_STANDOFF)
        lock = int(actor.get("lock_quality") or 0)
        aspect_mod = {"advantage": 0.15, "neutral": 0.0, "disadvantage": -0.15}.get(
            s.get("aspect") or "neutral", 0.0
        )
        base_chance = max(0.05, 0.55 - band * 0.1 + lock * 0.08 + aspect_mod)
        roll = r.random()
        _log_roll(s, s["tick"], "kinetic", roll, actor_id)
        if roll < base_chance:
            armor = int((target.get("combat") or {}).get("armor") or 0)
            damage_pct = max(3, 15 - armor)
            shield_absorb = min(int(target.get("shield_pct") or 0), damage_pct)
            hull_damage = max(0, damage_pct - shield_absorb)
            target["shield_pct"] = max(0, int(target["shield_pct"]) - shield_absorb)
            target["hull_pct"] = max(0, int(target["hull_pct"]) - hull_damage)
            events.append({
                "kind": "kinetic_hit",
                "actor_id": actor_id,
                "target_id": target["id"],
                "hull_damage": hull_damage,
                "shield_damage": shield_absorb,
                "hull_pct": target["hull_pct"],
                "roll": roll,
            })
            if target["hull_pct"] <= 0:
                target["eliminated"] = True
                events.append({"kind": "actor_eliminated", "actor_id": target["id"],
                                "cause": "kinetic"})
        else:
            events.append({"kind": "kinetic_miss", "actor_id": actor_id,
                            "target_id": target["id"], "roll": roll})

    elif action == "fox_missile":
        hardpoints = int(combat.get("hardpoints") or 2)
        active_tubes = len(actor.get("tube_timers") or [])
        if active_tubes >= hardpoints:
            return s, [{"kind": "error", "msg": "all hardpoints committed"}]
        _rb = s.get("range_band")
        band = int(_rb if _rb is not None else RANGE_STANDOFF)
        # Time-to-go depends on range band: closer = sooner
        ttg = max(1, 4 - band)
        actor["tube_timers"] = list(actor.get("tube_timers") or []) + [ttg]
        actor["heat"] = min(100, int(actor.get("heat") or 0) + 12)
        events.append({
            "kind": "missile_launched",
            "actor_id": actor_id,
            "target_id": target["id"],
            "time_to_go": ttg,
        })

    elif action == "pdc_posture":
        currently_on = bool(actor.get("pdc_posture"))
        actor["pdc_posture"] = not currently_on
        actor["emcon"] = 3 if not currently_on else 2
        events.append({"kind": "pdc_posture_toggle", "actor_id": actor_id,
                        "active": not currently_on})

    return s, events


# ---------------------------------------------------------------------------
# NPC AI (simple policy stub — extend per encounter template)
# ---------------------------------------------------------------------------

def npc_choose_action(
    state: dict,
    actor_id: str,
    rng: random.Random | None = None,
) -> tuple[str, str]:
    """
    Return (action_type, action_name) for an NPC actor.
    action_type is "maneuver" | "ew" | "weapon".
    """
    r = rng or random.Random()
    actor = _find_actor(state, actor_id)
    if not actor:
        return "maneuver", "cold_coast"

    _rb = state.get("range_band")
    band = int(_rb if _rb is not None else RANGE_STANDOFF)
    heat = int(actor.get("heat") or 0)
    hull_pct = int(actor.get("hull_pct") or 100)
    lock = int(actor.get("lock_quality") or 0)
    policy = str(actor.get("ai_policy_id") or "balanced")

    # Heat management takes priority
    if heat >= HEAT_OVERLOAD:
        return "maneuver", "cold_coast"

    # Critically damaged: attempt to disengage
    if hull_pct < 20:
        return "maneuver", "burn_out"

    if policy == "aggressive":
        if band > RANGE_KNIFE:
            return "maneuver", "burn_in"
        if lock >= 2:
            roll = r.random()
            return ("weapon", "fox_missile") if roll < 0.5 else ("weapon", "kinetic_squeeze")
        return "ew", "spike"

    elif policy == "defensive":
        if band < RANGE_MEDIUM:
            return "maneuver", "burn_out"
        return "maneuver", "jink"

    else:  # balanced
        if band > RANGE_MEDIUM:
            return "maneuver", "burn_in"
        if lock >= 1:
            return "weapon", "kinetic_squeeze"
        roll = r.random()
        return ("ew", "ghost") if roll < 0.4 else ("maneuver", "jink")
