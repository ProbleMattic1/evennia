"""Staff-only JSON API: apply curated billboard presets to rooms (see world.billboard_library)."""

from __future__ import annotations

import json
from typing import Any

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from evennia import search_object

from world.billboard_library import (
    BillboardLibraryError,
    build_ui_ambient_from_selection,
    catalog_for_staff_api,
    get_billboard_library,
)
from world.room_ambient import resolve_room_ambient


def _room_for_billboard(room_key: str):
    found = search_object(room_key)
    room = found[0] if found else None
    if not room or not room.is_typeclass("typeclasses.rooms.Room", exact=False):
        return None
    return room


@require_GET
def staff_room_billboard(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)

    try:
        lib = get_billboard_library()
    except BillboardLibraryError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=500)
    except (OSError, json.JSONDecodeError) as e:
        return JsonResponse({"ok": False, "message": f"Billboard library load failed: {e}"}, status=500)

    out: dict[str, Any] = {
        "ok": True,
        "catalog": catalog_for_staff_api(lib),
    }

    q = (request.GET.get("roomKey") or "").strip()
    if q:
        if q not in lib["rooms"]:
            return JsonResponse({"ok": False, "message": f"roomKey not in billboard library allowlist: {q!r}."}, status=400)
        room = _room_for_billboard(q)
        if not room:
            return JsonResponse({"ok": False, "message": f"Room not found: {q!r}."}, status=404)
        out["roomKey"] = room.key
        out["ambient"] = resolve_room_ambient(room)
        sel = getattr(room.db, "billboard_selection", None)
        out["billboardSelection"] = sel if isinstance(sel, dict) else None

    return JsonResponse(out)


@csrf_exempt
@require_POST
def staff_room_billboard_apply(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "Invalid JSON body."}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"ok": False, "message": "Body must be a JSON object."}, status=400)

    room_key = body.get("roomKey")
    preset_id = body.get("presetId")
    style_id = body.get("styleId")
    slide_images = body.get("slideImages")

    if not isinstance(room_key, str) or not room_key.strip():
        return JsonResponse({"ok": False, "message": "roomKey must be a non-empty string."}, status=400)
    if not isinstance(preset_id, str) or not preset_id.strip():
        return JsonResponse({"ok": False, "message": "presetId must be a non-empty string."}, status=400)
    if not isinstance(style_id, str) or not style_id.strip():
        return JsonResponse({"ok": False, "message": "styleId must be a non-empty string."}, status=400)
    if slide_images is not None and not isinstance(slide_images, dict):
        return JsonResponse({"ok": False, "message": "slideImages must be an object or omitted."}, status=400)

    try:
        lib = get_billboard_library()
    except BillboardLibraryError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=500)
    except (OSError, json.JSONDecodeError) as e:
        return JsonResponse({"ok": False, "message": f"Billboard library load failed: {e}"}, status=500)

    rk = room_key.strip()
    if rk not in lib["rooms"]:
        return JsonResponse({"ok": False, "message": f"roomKey not in billboard library allowlist: {rk!r}."}, status=400)

    room = _room_for_billboard(rk)
    if not room:
        return JsonResponse({"ok": False, "message": f"Room not found: {rk!r}."}, status=404)

    norm_slide_images: dict[str, str | None] = {}
    if isinstance(slide_images, dict):
        for k, v in slide_images.items():
            if not isinstance(k, str) or not k.strip():
                return JsonResponse({"ok": False, "message": "slideImages keys must be non-empty strings."}, status=400)
            if v is None:
                norm_slide_images[k.strip()] = None
            elif isinstance(v, str):
                if not v.strip():
                    return JsonResponse(
                        {"ok": False, "message": f"slideImages[{k!r}] must be null or a non-empty filename."},
                        status=400,
                    )
                norm_slide_images[k.strip()] = v.strip()
            else:
                return JsonResponse({"ok": False, "message": f"slideImages[{k!r}] must be string or null."}, status=400)

    try:
        ui_ambient = build_ui_ambient_from_selection(
            lib,
            preset_id=preset_id.strip(),
            style_id=style_id.strip(),
            slide_images=norm_slide_images or None,
        )
    except BillboardLibraryError as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    room.db.ui_ambient = ui_ambient
    room.db.billboard_selection = {
        "presetId": preset_id.strip(),
        "styleId": style_id.strip(),
        "slideImages": dict(norm_slide_images),
    }

    return JsonResponse(
        {
            "ok": True,
            "roomKey": room.key,
            "ambient": resolve_room_ambient(room),
            "billboardSelection": room.db.billboard_selection,
        }
    )
