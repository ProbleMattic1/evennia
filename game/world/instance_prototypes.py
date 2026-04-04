"""Load ``instance_prototypes.json``."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "instance_prototypes.json"


@lru_cache(maxsize=1)
def load_instance_prototypes() -> dict:
    raw = json.loads(_PATH.read_text(encoding="utf-8"))
    if int(raw.get("schema_version") or 0) != 1:
        raise ValueError("instance_prototypes.json: bad schema_version")
    return dict(raw.get("templates") or {})


def clear_instance_prototype_cache() -> None:
    load_instance_prototypes.cache_clear()


def get_instance_template(template_id: str) -> dict:
    tpl = load_instance_prototypes().get(str(template_id))
    if not tpl:
        raise ValueError(f"Unknown instance template: {template_id!r}")
    return dict(tpl)
