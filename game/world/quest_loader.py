from __future__ import annotations

from pathlib import Path
from typing import Any

from evennia.utils import logger

from world.json_bulk_loader import discover_chunk_paths, merge_validated_rows

_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_JSON = _DATA_DIR / "quest_templates.json"

_REQUIRED = frozenset({"id", "title", "summary", "questKind", "trigger", "objectives"})
_TRIGGER_KINDS = frozenset({"account_ready", "room", "interaction", "manual", "mission_complete"})

_OBJECTIVE_KINDS = frozenset({
    "visit_room",
    "interaction",
    "choice",
    "resolve_situation",
    "flag",
})

_registry: dict[str, Any] = {
    "version": 0,
    "templates": (),
    "by_id": {},
    "errors": (),
}


def _normalize_path_entry(raw: dict, obj_index: int, path_index: int, ref: str) -> tuple[dict | None, str | None]:
    via = str(raw.get("via") or "").strip().lower()
    if via not in {"interaction", "signal"}:
        return None, f"objective {obj_index} path {path_index}: bad via {via!r}"
    entry: dict[str, Any] = {
        "via": via,
        "completionKey": str(raw.get("completionKey") or "").strip() or f"path_{path_index}",
    }
    if via == "interaction":
        keys = [str(v).strip().lower() for v in list(raw.get("interactionKeysAny") or []) if str(v).strip()]
        if not keys:
            return None, f"objective {obj_index} path {path_index}: interactionKeysAny required"
        entry["interactionKeysAny"] = keys
    else:
        sig = str(raw.get("signal") or "").strip()
        if not sig:
            return None, f"objective {obj_index} path {path_index}: signal required"
        entry["signal"] = sig
        entry["match"] = dict(raw.get("match") or {})
    return entry, None


def _normalize_objective(raw: dict, obj_index: int, ref: str) -> tuple[dict | None, str | None]:
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in _OBJECTIVE_KINDS:
        return None, f"objective {obj_index}: unsupported kind {kind!r}"
    oid = str(raw.get("id") or "").strip()
    if not oid:
        return None, f"objective {obj_index}: missing id"
    obj: dict[str, Any] = {"id": oid, "kind": kind, "text": str(raw.get("text") or "")}

    if kind == "visit_room":
        obj["roomKeysAny"] = [str(v) for v in list(raw.get("roomKeysAny") or []) if str(v).strip()]
    elif kind == "interaction":
        obj["interactionKeysAny"] = [
            str(v).strip().lower() for v in list(raw.get("interactionKeysAny") or []) if str(v).strip()
        ]
    elif kind == "choice":
        obj["prompt"] = str(raw.get("prompt") or "")
        choices = []
        for ci, c in enumerate(list(raw.get("choices") or [])):
            if not isinstance(c, dict):
                return None, f"objective {obj_index} choice {ci} invalid"
            cid = str(c.get("id") or "").strip()
            if not cid:
                return None, f"objective {obj_index} choice {ci} missing id"
            choices.append({
                "id": cid,
                "label": str(c.get("label") or cid),
                "outcome": str(c.get("outcome") or ""),
                "nextObjectiveId": str(c.get("nextObjectiveId") or "").strip() or None,
                "completeQuest": bool(c.get("completeQuest", False)),
                "setFlags": dict(c.get("setFlags") or {}),
            })
        obj["choices"] = choices
    elif kind == "resolve_situation":
        paths = []
        for pi, p in enumerate(list(raw.get("paths") or [])):
            if not isinstance(p, dict):
                return None, f"objective {obj_index} path {pi} invalid"
            pe, err = _normalize_path_entry(p, obj_index, pi, ref)
            if err:
                return None, err
            assert pe is not None
            paths.append(pe)
        if len(paths) < 2:
            return None, f"objective {obj_index}: resolve_situation needs at least 2 paths (e.g. fight + avoid)"
        obj["paths"] = paths
    elif kind == "flag":
        obj["requireFlagsAll"] = [str(v) for v in list(raw.get("requireFlagsAll") or []) if str(v).strip()]

    return obj, None


def _normalize_row(raw: dict, ref: str) -> tuple[dict | None, str | None]:
    missing = _REQUIRED - raw.keys()
    if missing:
        return None, f"missing keys {sorted(missing)}"
    qid = str(raw.get("id") or "").strip()
    if not qid:
        return None, "empty id"
    trig = dict(raw.get("trigger") or {})
    tk = str(trig.get("kind") or "").strip().lower()
    if tk not in _TRIGGER_KINDS:
        return None, f"unsupported trigger kind {tk!r}"

    objectives = []
    for oi, o in enumerate(list(raw.get("objectives") or [])):
        if not isinstance(o, dict):
            return None, f"objective {oi} not an object"
        ob, err = _normalize_objective(o, oi, ref)
        if err:
            return None, err
        assert ob is not None
        objectives.append(ob)

    row = {
        "id": qid,
        "title": str(raw.get("title") or qid),
        "summary": str(raw.get("summary") or ""),
        "questKind": str(raw.get("questKind") or "main"),
        "storylineId": str(raw.get("storylineId") or ""),
        "threadId": str(raw.get("threadId") or ""),
        "version": int(raw.get("version") or 1),
        "trigger": {
            "kind": tk,
            "roomKeysAny": [str(v) for v in list(trig.get("roomKeysAny") or []) if str(v).strip()],
            "interactionKeysAny": [
                str(v).strip().lower() for v in list(trig.get("interactionKeysAny") or []) if str(v).strip()
            ],
        },
        "prerequisites": {
            "completedQuestIdsAny": [
                str(v) for v in list((raw.get("prerequisites") or {}).get("completedQuestIdsAny") or [])
                if str(v).strip()
            ],
            "flagsAll": [str(v) for v in list((raw.get("prerequisites") or {}).get("flagsAll") or []) if str(v).strip()],
        },
        "eligibility": {
            "once": bool((raw.get("eligibility") or {}).get("once", True)),
            "maxActive": int((raw.get("eligibility") or {}).get("maxActive") or 1),
        },
        "rewards": dict(raw.get("rewards") or {}),
        "objectives": objectives,
        "unlockQuestIds": [str(v) for v in list(raw.get("unlockQuestIds") or []) if str(v).strip()],
    }
    return row, None


def quest_source_paths(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    return discover_chunk_paths(
        data_dir=_DATA_DIR,
        chunk_subdir="quests.d",
        legacy_file=_DEFAULT_JSON,
    )


def load_quest_templates(path: Path | None = None) -> int:
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

    paths = quest_source_paths(path)
    templates, errors = merge_validated_rows(paths, validate_row=_normalize_row)
    version = int(_registry.get("version") or 0) + 1
    _registry = {
        "version": version,
        "templates": tuple(templates),
        "by_id": {row["id"]: row for row in templates},
        "errors": tuple(errors),
    }
    logger.log_info(
        f"[quests] registry v{version} files={len(paths)} templates={len(templates)} errors={len(errors)}"
    )
    return version


def _ensure_loaded() -> None:
    if not _registry.get("templates") and not _registry.get("errors"):
        load_quest_templates()


def quest_registry_errors() -> tuple[str, ...]:
    _ensure_loaded()
    return tuple(_registry.get("errors") or ())


def get_quest_template(template_id: str) -> dict | None:
    _ensure_loaded()
    return (_registry.get("by_id") or {}).get(str(template_id or "").strip())


def all_quest_templates() -> tuple[dict, ...]:
    _ensure_loaded()
    return tuple(_registry.get("templates") or ())


def matching_quest_templates_for_room(room) -> list[dict]:
    _ensure_loaded()
    key = str(getattr(room, "key", "") or "").strip()
    out = []
    for tmpl in all_quest_templates():
        t = tmpl.get("trigger") or {}
        if t.get("kind") != "room":
            continue
        if key and key in set(t.get("roomKeysAny") or []):
            out.append(tmpl)
    return out


def matching_quest_templates_for_interaction(interaction_key: str) -> list[dict]:
    _ensure_loaded()
    ikey = str(interaction_key or "").strip().lower()
    out = []
    for tmpl in all_quest_templates():
        t = tmpl.get("trigger") or {}
        if t.get("kind") != "interaction":
            continue
        if ikey in {str(v).strip().lower() for v in list(t.get("interactionKeysAny") or [])}:
            out.append(tmpl)
    return out
