"""
Room UI ambient: theme, banner slides, marquee, chips for web clients.

Merge rule: venue ``ui_ambient`` (from VENUES[venue_id]) is the base; ``room.db.ui_ambient``
(JSON dict) overrides by top-level key (shallow merge). Lists replaced entirely when overridden.

``venue_id`` is taken from ``room.db.venue_id`` or ``venue_id_for_object(room)``.
"""

from __future__ import annotations

from typing import Any

from world.venues import VENUES, get_venue, venue_id_for_object


def resolve_room_venue_id(room) -> str | None:
    if not room:
        return None
    vid = getattr(room.db, "venue_id", None)
    if vid:
        return str(vid)
    return venue_id_for_object(room)


def resolve_room_ambient(room) -> dict[str, Any]:
    """
    Return a JSON-serializable ambient dict for the given room (or empty-location defaults).
    """
    if not room:
        return _default_ambient_shell()

    vid = resolve_room_venue_id(room)

    base: dict[str, Any] = {}
    if vid and vid in VENUES:
        raw = get_venue(vid).get("ui_ambient")
        if isinstance(raw, dict):
            base = dict(raw)

    override = getattr(room.db, "ui_ambient", None)
    merged: dict[str, Any] = {**base, **override} if isinstance(override, dict) else dict(base)

    # Normalize lists / optional keys
    if not merged.get("themeId"):
        merged["themeId"] = "default"
    else:
        merged["themeId"] = str(merged["themeId"])

    for key in ("label", "tagline"):
        if key not in merged:
            merged[key] = None
        elif merged[key] is not None:
            merged[key] = str(merged[key])

    for key in ("bannerSlides", "marqueeLines", "chips"):
        val = merged.get(key)
        if not isinstance(val, list):
            merged[key] = []
        else:
            merged[key] = [_slide_json(x) if key == "bannerSlides" else _chip_json(x) if key == "chips" else _line_json(x) for x in val]

    hints = merged.get("layoutHints")
    if hints is not None and not isinstance(hints, dict):
        merged["layoutHints"] = None
    elif isinstance(hints, dict):
        merged["layoutHints"] = dict(hints)

    return merged


def _default_ambient_shell() -> dict[str, Any]:
    return {
        "themeId": "default",
        "label": None,
        "tagline": None,
        "bannerSlides": [],
        "marqueeLines": [],
        "chips": [],
        "layoutHints": None,
    }


def _slide_json(x: Any) -> dict[str, Any]:
    if not isinstance(x, dict):
        return {"id": "slide", "title": None, "body": None, "graphicKey": None}
    return {
        "id": str(x.get("id") or "slide"),
        "title": (str(x["title"]) if x.get("title") is not None else None),
        "body": (str(x["body"]) if x.get("body") is not None else None),
        "graphicKey": (str(x["graphicKey"]) if x.get("graphicKey") else None),
    }


def _chip_json(x: Any) -> dict[str, Any]:
    if not isinstance(x, dict):
        return {"id": "chip", "text": ""}
    return {
        "id": str(x.get("id") or "chip"),
        "text": str(x.get("text") or ""),
    }


def _line_json(x: Any) -> str:
    if x is None:
        return ""
    return str(x)
