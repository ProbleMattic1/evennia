from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evennia.utils import logger

_DEFAULT_JSON = Path(__file__).resolve().parent / "data" / "mission_templates.json"

_REQUIRED_TEMPLATE_KEYS = frozenset(
    {"id", "title", "summary", "missionKind", "trigger", "objectives"}
)
_ALLOWED_TRIGGER_KINDS = frozenset({"alert", "incident", "room", "interaction"})
_ALLOWED_OBJECTIVE_KINDS = frozenset({"visit_room", "interaction", "choice"})

_registry: dict[str, Any] = {
    "version": 0,
    "templates": (),
    "by_id": {},
    "errors": (),
}


def _normalize_template(raw: dict, index: int) -> tuple[dict | None, str | None]:
    missing = _REQUIRED_TEMPLATE_KEYS - raw.keys()
    if missing:
        return None, f"row {index}: missing keys {sorted(missing)}"

    tid = str(raw.get("id") or "").strip()
    if not tid:
        return None, f"row {index}: empty id"

    trigger = dict(raw.get("trigger") or {})
    trigger_kind = str(trigger.get("kind") or "").strip().lower()
    if trigger_kind not in _ALLOWED_TRIGGER_KINDS:
        return None, f"row {index}: unsupported trigger kind {trigger_kind!r}"

    objectives = []
    for obj_index, obj in enumerate(list(raw.get("objectives") or [])):
        if not isinstance(obj, dict):
            return None, f"row {index}: objective {obj_index} is not an object"
        kind = str(obj.get("kind") or "").strip().lower()
        if kind not in _ALLOWED_OBJECTIVE_KINDS:
            return None, f"row {index}: objective {obj_index} kind {kind!r} unsupported"
        oid = str(obj.get("id") or "").strip()
        if not oid:
            return None, f"row {index}: objective {obj_index} missing id"

        new_obj = {
            "id": oid,
            "kind": kind,
            "text": str(obj.get("text") or ""),
        }
        if kind == "visit_room":
            new_obj["roomKeysAny"] = [
                str(v) for v in list(obj.get("roomKeysAny") or []) if str(v).strip()
            ]
        elif kind == "interaction":
            new_obj["interactionKeysAny"] = [
                str(v) for v in list(obj.get("interactionKeysAny") or []) if str(v).strip()
            ]
        elif kind == "choice":
            choices = []
            for choice_index, choice in enumerate(list(obj.get("choices") or [])):
                if not isinstance(choice, dict):
                    return None, f"row {index}: objective {obj_index} choice {choice_index} invalid"
                cid = str(choice.get("id") or "").strip()
                if not cid:
                    return None, f"row {index}: objective {obj_index} choice {choice_index} missing id"
                choices.append(
                    {
                        "id": cid,
                        "label": str(choice.get("label") or cid),
                        "outcome": str(choice.get("outcome") or ""),
                        "morality": dict(choice.get("morality") or {}),
                        "rewards": dict(choice.get("rewards") or {}),
                        "nextObjectiveId": str(choice.get("nextObjectiveId") or "").strip() or None,
                        "unlockTemplateIds": [
                            str(v)
                            for v in list(choice.get("unlockTemplateIds") or [])
                            if str(v).strip()
                        ],
                        "completeMission": bool(choice.get("completeMission", False)),
                    }
                )
            new_obj["prompt"] = str(obj.get("prompt") or "")
            new_obj["choices"] = choices
        objectives.append(new_obj)

    row = {
        "id": tid,
        "title": str(raw.get("title") or tid),
        "summary": str(raw.get("summary") or ""),
        "missionKind": str(raw.get("missionKind") or "mission"),
        "threadId": str(raw.get("threadId") or ""),
        "storylineId": str(raw.get("storylineId") or ""),
        "giver": dict(raw.get("giver") or {}),
        "trigger": {
            "kind": trigger_kind,
            "seedIdsAny": [str(v) for v in list(trigger.get("seedIdsAny") or []) if str(v).strip()],
            "roomKeysAny": [str(v) for v in list(trigger.get("roomKeysAny") or []) if str(v).strip()],
            "interactionKeysAny": [
                str(v) for v in list(trigger.get("interactionKeysAny") or []) if str(v).strip()
            ],
        },
        "eligibility": {
            "cooldownSeconds": int((raw.get("eligibility") or {}).get("cooldownSeconds") or 0),
            "maxActive": int((raw.get("eligibility") or {}).get("maxActive") or 1),
            "once": bool((raw.get("eligibility") or {}).get("once", False)),
        },
        "rewards": dict(raw.get("rewards") or {}),
        "objectives": objectives,
    }
    return row, None


def load_mission_templates(path: Path | None = None) -> int:
    global _registry
    path = path or _DEFAULT_JSON

    if not path.is_file():
        _registry = {"version": 0, "templates": (), "by_id": {}, "errors": (f"file missing: {path}",)}
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _registry = {"version": 0, "templates": (), "by_id": {}, "errors": (f"parse error: {exc}",)}
        return 0

    if not isinstance(data, list):
        _registry = {"version": 0, "templates": (), "by_id": {}, "errors": ("root must be a list",)}
        return 0

    templates = []
    errors = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            errors.append(f"row {i}: not an object")
            continue
        row, err = _normalize_template(raw, i)
        if err:
            errors.append(err)
            continue
        templates.append(row)

    version = int(_registry.get("version") or 0) + 1
    _registry = {
        "version": version,
        "templates": tuple(templates),
        "by_id": {row["id"]: row for row in templates},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[missions] registry v{version} templates={len(templates)} errors={len(errors)}"
    )
    return version


def _ensure_loaded() -> None:
    if not _registry.get("templates") and not _registry.get("errors"):
        load_mission_templates()


def all_mission_templates() -> tuple[dict, ...]:
    _ensure_loaded()
    return tuple(_registry.get("templates") or ())


def get_mission_template(template_id: str) -> dict | None:
    _ensure_loaded()
    return (_registry.get("by_id") or {}).get(str(template_id or "").strip())


def mission_registry_errors() -> tuple[str, ...]:
    _ensure_loaded()
    return tuple(_registry.get("errors") or ())


def matching_templates_for_seed(seed: dict) -> list[dict]:
    _ensure_loaded()
    seed_kind = str(seed.get("kind") or "").strip().lower()
    seed_id = str(seed.get("seedId") or "").strip()
    out = []
    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != seed_kind:
            continue
        if seed_id and seed_id in set(trig.get("seedIdsAny") or []):
            out.append(tmpl)
    return out


def matching_templates_for_room(room) -> list[dict]:
    _ensure_loaded()
    room_key = str(getattr(room, "key", "") or "").strip()
    out = []
    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != "room":
            continue
        if room_key and room_key in set(trig.get("roomKeysAny") or []):
            out.append(tmpl)
    return out


def matching_templates_for_interaction(interaction_key: str) -> list[dict]:
    _ensure_loaded()
    ikey = str(interaction_key or "").strip().lower()
    out = []
    for tmpl in all_mission_templates():
        trig = tmpl.get("trigger") or {}
        if trig.get("kind") != "interaction":
            continue
        keys = {str(v).strip().lower() for v in list(trig.get("interactionKeysAny") or [])}
        if ikey in keys:
            out.append(tmpl)
    return out
