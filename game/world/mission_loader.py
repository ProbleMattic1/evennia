from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows
from world.mission_place_roles import known_place_role_ids, merge_visit_room_keys

_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_JSON = _DATA_DIR / "mission_templates.json"

_REQUIRED_TEMPLATE_KEYS = frozenset(
    {"id", "title", "summary", "missionKind", "trigger", "objectives"}
)
_ALLOWED_TRIGGER_KINDS = frozenset({"alert", "incident", "room", "interaction", "crime", "battlespace"})
_ALLOWED_OBJECTIVE_KINDS = frozenset({"visit_room", "interaction", "choice", "engagement"})

_registry: dict[str, Any] = {
    "version": 0,
    "templates": (),
    "by_id": {},
    "errors": (),
}


def _normalize_mission_row(raw: dict, _ref: str) -> tuple[dict | None, str | None]:
    missing = _REQUIRED_TEMPLATE_KEYS - raw.keys()
    if missing:
        return None, f"missing keys {sorted(missing)}"

    tid = str(raw.get("id") or "").strip()
    if not tid:
        return None, "empty id"

    trigger = dict(raw.get("trigger") or {})
    trigger_kind = str(trigger.get("kind") or "").strip().lower()
    if trigger_kind not in _ALLOWED_TRIGGER_KINDS:
        return None, f"unsupported trigger kind {trigger_kind!r}"

    objectives = []
    for obj_index, obj in enumerate(list(raw.get("objectives") or [])):
        if not isinstance(obj, dict):
            return None, f"objective {obj_index} is not an object"
        kind = str(obj.get("kind") or "").strip().lower()
        if kind not in _ALLOWED_OBJECTIVE_KINDS:
            return None, f"objective {obj_index} kind {kind!r} unsupported"
        oid = str(obj.get("id") or "").strip()
        if not oid:
            return None, f"objective {obj_index} missing id"

        new_obj = {
            "id": oid,
            "kind": kind,
            "text": str(obj.get("text") or ""),
        }
        if kind == "visit_room":
            explicit = [str(v) for v in list(obj.get("roomKeysAny") or []) if str(v).strip()]
            role_ids = [str(v) for v in list(obj.get("roomTagsAny") or []) if str(v).strip()]
            unknown = [r for r in role_ids if r not in known_place_role_ids()]
            if unknown:
                return None, f"objective {obj_index} unknown roomTagsAny: {unknown!r}"
            merged = merge_visit_room_keys(explicit_keys=explicit, role_ids=role_ids)
            if not merged:
                return None, f"objective {obj_index} visit_room needs roomKeysAny or roomTagsAny"
            new_obj["roomKeysAny"] = merged
        elif kind == "interaction":
            new_obj["interactionKeysAny"] = [
                str(v) for v in list(obj.get("interactionKeysAny") or []) if str(v).strip()
            ]
        elif kind == "choice":
            choices = []
            for choice_index, choice in enumerate(list(obj.get("choices") or [])):
                if not isinstance(choice, dict):
                    return None, f"objective {obj_index} choice {choice_index} invalid"
                cid = str(choice.get("id") or "").strip()
                if not cid:
                    return None, (
                        f"objective {obj_index} choice {choice_index} missing id"
                    )
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
        elif kind == "engagement":
            new_obj["missionTagsAny"] = [
                str(v) for v in list(obj.get("missionTagsAny") or []) if str(v).strip()
            ]
            new_obj["rewards"] = dict(obj.get("rewards") or {})
        objectives.append(new_obj)

    trig_rk = [str(v) for v in list(trigger.get("roomKeysAny") or []) if str(v).strip()]
    trig_rt = [str(v) for v in list(trigger.get("roomTagsAny") or []) if str(v).strip()]
    unknown_trig = [r for r in trig_rt if r not in known_place_role_ids()]
    if unknown_trig:
        return None, f"trigger unknown roomTagsAny: {unknown_trig!r}"
    trig_merged = merge_visit_room_keys(explicit_keys=trig_rk, role_ids=trig_rt)
    if trigger_kind == "room" and not trig_merged:
        return None, "room trigger requires roomKeysAny or roomTagsAny"

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
            "roomKeysAny": trig_merged,
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


def mission_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="missions.d",
        legacy_file=_DEFAULT_JSON,
    )


def load_mission_templates(path: Path | None = None) -> int:
    global _registry
    explicit = path
    if explicit is not None and not explicit.is_file():
        _registry = {
            "version": 0,
            "templates": (),
            "by_id": {},
            "errors": (f"file missing: {explicit}",),
        }
        return 0

    paths = mission_source_paths(path)
    templates, errors = merge_validated_rows(paths, validate_row=_normalize_mission_row)
    version = int(_registry.get("version") or 0) + 1
    _registry = {
        "version": version,
        "templates": tuple(templates),
        "by_id": {row["id"]: row for row in templates},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[missions] registry v{version} files={len(paths)} "
        f"templates={len(templates)} errors={len(errors)}"
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
