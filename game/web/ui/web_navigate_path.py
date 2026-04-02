"""
Next.js path after web-mediated movement.

Maps destination rooms to concrete routes. No silent /play for bank, shops, or
other dedicated UIs. Unclassified keys raise WebNavigatePathError (caller returns 400).
"""

from __future__ import annotations

from urllib.parse import quote

from world.venues import VENUES, all_venue_ids, get_venue

from web.ui.room_nav_utils import is_mining_site_room


class WebNavigatePathError(ValueError):
    """Room key has no registered web route (registry gap)."""


def _build_dedicated_paths() -> dict[str, str]:
    m: dict[str, str] = {}
    for vid in all_venue_ids():
        spec = get_venue(vid)
        b = spec["bank"]["reserve_room_key"]
        m[b] = f"/bank?venue={vid}"

        r = spec["realty"]["office_key"]
        m[r] = f"/real-estate?venue={vid}"

        proc = spec["processing"]
        m[proc["plant_room_key"]] = f"/processing?venue={vid}"
        rk = proc.get("refinery_room_key")
        if rk:
            m[str(rk).strip()] = f"/refinery?venue={vid}"

        sy = spec["shipyard"]
        sk = sy["showroom_key"]
        m[sk] = f"/shop?room={quote(sk, safe='')}"

        for shop in spec["shops"]:
            rk2 = shop["room_key"]
            m[rk2] = f"/shop?room={quote(rk2, safe='')}"

        ind = spec.get("industrial") or {}
        bio = ind.get("resource_bio") or {}
        for col in ("flora_plant_keys", "fauna_plant_keys"):
            for pk in bio.get(col) or ():
                pk = str(pk).strip()
                if pk:
                    m[pk] = f"/processing?venue={vid}"
    return m


_DEDICATED = _build_dedicated_paths()


def allowed_processing_plant_keys_for_venue(venue_id: str) -> frozenset[str]:
    """Room keys that count as a processing plant floor for ``/ui/processing`` payload."""
    spec = get_venue(venue_id)
    keys: set[str] = {spec["processing"]["plant_room_key"]}
    bio = (spec.get("industrial") or {}).get("resource_bio") or {}
    for col in ("flora_plant_keys", "fauna_plant_keys"):
        for pk in bio.get(col) or ():
            pk = str(pk).strip()
            if pk:
                keys.add(pk)
    return frozenset(keys)


def _play_surface_room_key(k: str) -> bool:
    """Rooms that use the generic /play surface (aligned with locator_zones patterns)."""
    if k == "Frontier Transit Shell":
        return True
    if k == "Industrial Resource Colony Grid" or k.startswith("Industrial Resource Colony Pad "):
        return True
    if k == "Ashfall Industrial Grid" or k.startswith("Ashfall Industrial Pad "):
        return True
    if k in ("Industrial Resource Colony Flora Annex", "Industrial Resource Colony Fauna Annex"):
        return True
    if k.startswith("Industrial Resource Colony Flora Pad ") or k.startswith(
        "Industrial Resource Colony Fauna Pad "
    ):
        return True
    if (
        k == "Marcus Killstar Mining Annex"
        or k in ("Marcus Killstar Flora Annex", "Marcus Killstar Fauna Annex")
        or k.startswith("Marcus Killstar Pad ")
        or k.startswith("Marcus Killstar Flora Pad ")
        or k.startswith("Marcus Killstar Fauna Pad ")
    ):
        return True
    if k == "Low Meridian Orbit":
        return True

    for vid in all_venue_ids():
        v = get_venue(vid)
        if k == v["hub_key"]:
            return True
        arr = v.get("arrival_room_key")
        if arr and k == arr:
            return True
        if k == v["advertising"]["room_key"]:
            return True
        r = v["realty"]
        if k == r["archive_room_key"]:
            return True
        sy = v["shipyard"]
        if k == sy["delivery_key"]:
            return True
        ind = v.get("industrial") or {}
        if k == ind.get("staging_room_key"):
            return True
        rc = ind.get("resource_bio") or {}
        if rc:
            if k in (rc.get("flora_staging_room_key"), rc.get("fauna_staging_room_key")):
                return True
            fp = str(rc.get("flora_pad_prefix") or "")
            fap = str(rc.get("fauna_pad_prefix") or "")
            if fp and (k == fp or k.startswith(fp + " ")):
                return True
            if fap and (k == fap or k.startswith(fap + " ")):
                return True
        prefix = str(ind.get("pad_room_prefix") or "")
        if prefix and (k == prefix or k.startswith(prefix + " ")):
            return True

    return False


def web_navigate_path_for_room(room, *, viewer) -> str:
    """
    Next.js path (leading slash) for the UI that should show after moving to ``room``.

    Raises:
        WebNavigatePathError: Room is not a mining site, dedicated route, or play shell.
    """
    if room is None:
        raise WebNavigatePathError("No destination room.")

    is_site, _ = is_mining_site_room(room)
    if is_site:
        return "/play"

    k = getattr(room, "key", None) or ""
    if not k:
        raise WebNavigatePathError("Destination room has no key.")

    if k in _DEDICATED:
        return _DEDICATED[k]

    if _play_surface_room_key(k):
        return "/play"

    raise WebNavigatePathError(f"Unmapped web navigation for room {k!r}.")
