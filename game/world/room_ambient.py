"""
Room UI ambient: theme, banner slides, marquee, chips, optional visual takeover for web clients.

Merge rule: venue ``ui_ambient`` (from VENUES[venue_id]) is the base; ``room.db.ui_ambient``
(JSON dict) overrides by top-level key (shallow merge). Lists replaced entirely when overridden.

``visualTakeover`` merges deeply per subsection (``top``, ``sidebar``, ``tokens``) so a room can
override only one rail without discarding the venue default for the other.

``venue_id`` is taken from ``room.db.venue_id`` or ``venue_id_for_object(room)``.
"""

from __future__ import annotations

from typing import Any

from world.venues import VENUES, get_venue, venue_id_for_object

# Keys accepted by ``frontend/aurnom/components/location-banner-graphics.tsx``.
_AMBIENT_GRAPHIC_KEYS = frozenset({"promenade", "industrial", "refinery", "asteroid", "bazaar"})
_FIT_MODES = frozenset({"cover", "contain"})
_SIDEBAR_POSITIONS = frozenset({"left", "right"})


def normalize_visual_takeover_payload(raw: Any) -> dict[str, Any] | None:
    """
    Normalize a ``visualTakeover`` object (e.g. from JSON or billboard presets).

    Accepts the same shape as stored under ``ui_ambient.visualTakeover`` / venue defaults.
    """
    if not isinstance(raw, dict):
        return None
    merged_sub = _merge_visual_takeover_subsections({}, raw)
    return _normalize_visual_takeover(merged_sub)


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

    mc = merged.get("marqueeClass")
    if mc not in ("normal", "slow", "fast", None):
        merged["marqueeClass"] = None
    elif mc is None:
        merged["marqueeClass"] = None
    else:
        merged["marqueeClass"] = str(mc)

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

    base_vt = base.get("visualTakeover") if isinstance(base.get("visualTakeover"), dict) else {}
    room_ambient = override if isinstance(override, dict) else {}
    ovr_vt = room_ambient.get("visualTakeover") if isinstance(room_ambient.get("visualTakeover"), dict) else {}
    merged_vt_raw = _merge_visual_takeover_subsections(base_vt, ovr_vt)
    merged["visualTakeover"] = _normalize_visual_takeover(merged_vt_raw)

    return merged


def _default_ambient_shell() -> dict[str, Any]:
    return {
        "themeId": "default",
        "marqueeClass": None,
        "label": None,
        "tagline": None,
        "bannerSlides": [],
        "marqueeLines": [],
        "chips": [],
        "layoutHints": None,
        "visualTakeover": None,
    }


def _safe_billboard_basename(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or "/" in s or "\\" in s or ".." in s:
        return None
    return s


def _merge_visual_takeover_subsections(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("top", "sidebar", "tokens"):
        bd = base.get(key) if isinstance(base.get(key), dict) else {}
        od = override.get(key) if isinstance(override.get(key), dict) else {}
        merged = {**bd, **od}
        if merged:
            out[key] = merged
    return out


def _normalize_graphic_key(raw: Any) -> str | None:
    if raw is None or raw is False:
        return None
    s = str(raw).strip()
    if not s or s not in _AMBIENT_GRAPHIC_KEYS:
        return None
    return s


def _normalize_visual_takeover(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    top = _normalize_takeover_panel(raw.get("top"), panel="top")
    sidebar = _normalize_takeover_panel(raw.get("sidebar"), panel="sidebar")
    tokens = _normalize_takeover_tokens(raw.get("tokens"))
    if top is None and sidebar is None and tokens is None:
        return None
    out: dict[str, Any] = {}
    if top is not None:
        out["top"] = top
    if sidebar is not None:
        out["sidebar"] = sidebar
    if tokens is not None:
        out["tokens"] = tokens
    return out or None


def _normalize_takeover_panel(raw: Any, *, panel: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    image_key = _safe_billboard_basename(raw.get("imageKey"))
    graphic_key = _normalize_graphic_key(raw.get("graphicKey"))
    alt = raw.get("alt")
    alt_out = str(alt).strip() if alt is not None and str(alt).strip() else None

    fit_raw = raw.get("fit")
    fit = str(fit_raw).strip() if fit_raw is not None else "cover"
    if fit not in _FIT_MODES:
        fit = "cover"

    min_h = raw.get("minHeightPx")
    min_height_px: int | None
    try:
        min_height_px = int(min_h) if min_h is not None else (140 if panel == "top" else None)
    except (TypeError, ValueError):
        min_height_px = 140 if panel == "top" else None
    if panel == "top":
        if min_height_px is None:
            min_height_px = 140
        min_height_px = max(48, min(min_height_px, 480))
    else:
        if min_height_px is not None:
            min_height_px = max(48, min(min_height_px, 900))

    overlay = raw.get("overlayGradient")
    overlay_gradient = bool(overlay) if overlay is not None else True

    pos_raw = raw.get("position")
    position = str(pos_raw).strip().lower() if pos_raw is not None else "left"
    if position not in _SIDEBAR_POSITIONS:
        position = "left"

    out: dict[str, Any] = {"fit": fit, "overlayGradient": overlay_gradient}
    if image_key is not None:
        out["imageKey"] = image_key
    if graphic_key is not None:
        out["graphicKey"] = graphic_key
    if alt_out is not None:
        out["alt"] = alt_out
    if panel == "top":
        out["minHeightPx"] = min_height_px
    else:
        out["position"] = position
        if min_height_px is not None:
            out["minHeightPx"] = min_height_px

    has_visual = image_key is not None or graphic_key is not None
    if not has_visual:
        return None
    return out


def _normalize_takeover_tokens(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            continue
        key = k.strip()
        if not key.replace("_", "").isalnum():
            continue
        if v is None:
            continue
        out[key] = str(v)
    return out or None


def _slide_json(x: Any) -> dict[str, Any]:
    if not isinstance(x, dict):
        return {"id": "slide", "title": None, "body": None, "graphicKey": None, "imageKey": None}
    ik = x.get("imageKey")
    image_key = str(ik).strip() if ik is not None and str(ik).strip() else None
    return {
        "id": str(x.get("id") or "slide"),
        "title": (str(x["title"]) if x.get("title") is not None else None),
        "body": (str(x["body"]) if x.get("body") is not None else None),
        "graphicKey": (str(x["graphicKey"]) if x.get("graphicKey") else None),
        "imageKey": image_key,
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
