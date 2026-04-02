"""
Curated billboard presets and staff apply logic.

Source of truth: ``billboard_library.json`` (rooms allowlist, image filenames, styles, presets).
Staff UI may only POST enumerated IDs validated against this file.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

_LIBRARY_PATH = Path(__file__).resolve().parent / "billboard_library.json"

_SLIDE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
_STYLE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
_PRESET_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")


class BillboardLibraryError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise BillboardLibraryError(msg)


def load_billboard_library() -> dict[str, Any]:
    raw = _LIBRARY_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    _require(isinstance(data, dict), "billboard_library.json must be a JSON object.")
    rooms = data.get("rooms")
    images = data.get("images")
    styles = data.get("styles")
    presets = data.get("presets")
    _require(isinstance(rooms, list), "rooms must be a list.")
    _require(isinstance(images, list), "images must be a list.")
    _require(isinstance(styles, list), "styles must be a list.")
    _require(isinstance(presets, list), "presets must be a list.")
    for r in rooms:
        _require(isinstance(r, str) and r.strip(), "Each room entry must be a non-empty string.")
    image_list: list[str] = []
    seen_img: set[str] = set()
    for img in images:
        _require(isinstance(img, str) and img.strip(), "Each images entry must be a non-empty string.")
        _require("/" not in img and "\\" not in img and ".." not in img, f"Invalid image key: {img!r}")
        _require(img not in seen_img, f"Duplicate image entry: {img!r}")
        seen_img.add(img)
        image_list.append(img)
    image_set = set(image_list)
    style_by_id: dict[str, dict[str, Any]] = {}
    for st in styles:
        _require(isinstance(st, dict), "Each style must be an object.")
        sid = st.get("id")
        _require(isinstance(sid, str) and _STYLE_ID_RE.match(sid), f"Invalid style id: {sid!r}")
        _require(sid not in style_by_id, f"Duplicate style id: {sid}")
        tid = st.get("themeId")
        _require(isinstance(tid, str) and tid.strip(), "style.themeId must be a non-empty string.")
        mc = st.get("marqueeClass", "normal")
        _require(mc in ("normal", "slow", "fast"), f"Invalid marqueeClass on style {sid!r}")
        style_by_id[sid] = {"id": sid, "themeId": tid.strip(), "marqueeClass": mc}
    preset_by_id: dict[str, dict[str, Any]] = {}
    for pr in presets:
        _require(isinstance(pr, dict), "Each preset must be an object.")
        pid = pr.get("id")
        _require(isinstance(pid, str) and _PRESET_ID_RE.match(pid), f"Invalid preset id: {pid!r}")
        _require(pid not in preset_by_id, f"Duplicate preset id: {pid}")
        slides = pr.get("bannerSlides")
        _require(isinstance(slides, list) and len(slides) > 0, f"preset {pid}: bannerSlides must be a non-empty list.")
        norm_slides: list[dict[str, Any]] = []
        seen_slide_ids: set[str] = set()
        for s in slides:
            _require(isinstance(s, dict), f"preset {pid}: each slide must be an object.")
            slid = s.get("id")
            _require(isinstance(slid, str) and _SLIDE_ID_RE.match(slid), f"preset {pid}: invalid slide id {slid!r}")
            _require(slid not in seen_slide_ids, f"preset {pid}: duplicate slide id {slid!r}")
            seen_slide_ids.add(slid)
            title = s.get("title")
            body = s.get("body")
            gk = s.get("graphicKey")
            ik = s.get("imageKey")
            _require(title is None or isinstance(title, str), f"preset {pid} slide {slid}: title must be string or null.")
            _require(body is None or isinstance(body, str), f"preset {pid} slide {slid}: body must be string or null.")
            _require(gk is None or isinstance(gk, str), f"preset {pid} slide {slid}: graphicKey must be string or null.")
            _require(ik is None or isinstance(ik, str), f"preset {pid} slide {slid}: imageKey must be string or null.")
            if isinstance(ik, str) and ik.strip():
                _require(ik in image_set, f"preset {pid} slide {slid}: imageKey {ik!r} not in library images list.")
                image_key_out: str | None = ik
            else:
                image_key_out = None
            gk_out = gk.strip() if isinstance(gk, str) and gk.strip() else None
            norm_slides.append(
                {
                    "id": slid,
                    "title": title if isinstance(title, str) else None,
                    "body": body if isinstance(body, str) else None,
                    "graphicKey": gk_out,
                    "imageKey": image_key_out,
                }
            )
        mlines = pr.get("marqueeLines")
        _require(isinstance(mlines, list), f"preset {pid}: marqueeLines must be a list.")
        norm_lines: list[str] = []
        for line in mlines:
            _require(isinstance(line, str), f"preset {pid}: marquee line must be a string.")
            norm_lines.append(line)
        chips = pr.get("chips")
        _require(isinstance(chips, list), f"preset {pid}: chips must be a list.")
        norm_chips: list[dict[str, Any]] = []
        for c in chips:
            _require(isinstance(c, dict), f"preset {pid}: each chip must be an object.")
            cid = c.get("id")
            ctext = c.get("text")
            _require(isinstance(cid, str) and cid.strip(), f"preset {pid}: chip id invalid.")
            _require(isinstance(ctext, str), f"preset {pid}: chip text must be a string.")
            norm_chips.append({"id": cid.strip(), "text": ctext})
        lbl = pr.get("label")
        tg = pr.get("tagline")
        _require(lbl is None or isinstance(lbl, str), f"preset {pid}: label must be string or null.")
        _require(tg is None or isinstance(tg, str), f"preset {pid}: tagline must be string or null.")
        preset_by_id[pid] = {
            "id": pid,
            "label": lbl if isinstance(lbl, str) else None,
            "tagline": tg if isinstance(tg, str) else None,
            "bannerSlides": norm_slides,
            "marqueeLines": norm_lines,
            "chips": norm_chips,
        }
    return {
        "rooms": [str(r).strip() for r in rooms],
        "images": image_list,
        "styles": list(style_by_id.values()),
        "presets": list(preset_by_id.values()),
        "_preset_by_id": preset_by_id,
        "_style_by_id": style_by_id,
        "_image_set": image_set,
    }


def catalog_for_staff_api(lib: dict[str, Any]) -> dict[str, Any]:
    """Strip internal indexes for JSON responses."""
    return {
        "rooms": lib["rooms"],
        "images": lib["images"],
        "styles": lib["styles"],
        "presets": [
            {
                "id": p["id"],
                "label": p["label"],
                "tagline": p["tagline"],
                "bannerSlides": p["bannerSlides"],
                "marqueeLines": p["marqueeLines"],
                "chips": p["chips"],
            }
            for p in lib["presets"]
        ],
    }


def build_ui_ambient_from_selection(
    lib: dict[str, Any],
    *,
    preset_id: str,
    style_id: str,
    slide_images: dict[str, str | None] | None,
) -> dict[str, Any]:
    """
    Produce a ``room.db.ui_ambient`` dict (merged fields only).
    """
    pid = preset_id.strip()
    sid = style_id.strip()
    preset = lib["_preset_by_id"].get(pid)
    style = lib["_style_by_id"].get(sid)
    if preset is None:
        raise BillboardLibraryError(f"Unknown presetId: {preset_id!r}.")
    if style is None:
        raise BillboardLibraryError(f"Unknown styleId: {style_id!r}.")
    slides = copy.deepcopy(preset["bannerSlides"])
    image_set: set[str] = lib["_image_set"]
    overlays = slide_images or {}
    slide_ids = {s["id"] for s in slides}
    for k, v in overlays.items():
        if k not in slide_ids:
            raise BillboardLibraryError(f"slideImages key {k!r} is not a slide id in preset {pid!r}.")
        if v is None:
            for s in slides:
                if s["id"] == k:
                    s["imageKey"] = None
            continue
        if not isinstance(v, str) or not v.strip():
            raise BillboardLibraryError(f"slideImages[{k!r}] must be a non-empty string or null.")
        if v not in image_set:
            raise BillboardLibraryError(f"slideImages[{k!r}] must be a library image; got {v!r}.")
        for s in slides:
            if s["id"] == k:
                s["imageKey"] = v
    return {
        "themeId": style["themeId"],
        "marqueeClass": style["marqueeClass"],
        "label": preset["label"],
        "tagline": preset["tagline"],
        "bannerSlides": slides,
        "marqueeLines": copy.deepcopy(preset["marqueeLines"]),
        "chips": copy.deepcopy(preset["chips"]),
    }


_LIB_CACHE: dict[str, Any] | None = None


def get_billboard_library() -> dict[str, Any]:
    global _LIB_CACHE
    if _LIB_CACHE is None:
        _LIB_CACHE = load_billboard_library()
    return _LIB_CACHE


def reload_billboard_library_for_tests() -> dict[str, Any]:
    """Test helper: drop cache and reload from disk."""
    global _LIB_CACHE
    _LIB_CACHE = None
    return get_billboard_library()
