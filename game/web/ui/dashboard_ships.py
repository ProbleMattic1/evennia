"""Shared dashboard ship rows for web JSON. Kept free of control_surface/views cycles."""


def _slugify_vehicle_class(specs):
    specs = specs or {}
    slug = (specs.get("vehicle_type_slug") or "").strip()
    if slug:
        return slug
    raw = (specs.get("vehicle_type") or "").strip().lower()
    if not raw:
        return "unknown"
    out = []
    for ch in raw:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in (" ", "-", "_") and (not out or out[-1] != "-"):
            out.append("-")
    s = "".join(out).strip("-")
    return s or "unknown"


def _pretty_vehicle_type_label(raw_type):
    """
    Catalog CSV uses snake_case keys (light_freighter, medium_transport) or short
    lowercase tokens (courier). Turn those into UI labels without clobbering
    values that already look like display text.
    """
    t = (raw_type or "").strip()
    if not t:
        return None
    if "_" in t or t.islower():
        return t.replace("_", " ").replace("-", " ").title()
    return t


def _label_for_vehicle_class(specs, class_slug):
    specs = specs or {}
    raw_type = (specs.get("vehicle_type") or "").strip()
    pretty = _pretty_vehicle_type_label(raw_type)
    if pretty:
        return pretty
    if class_slug and class_slug != "unknown":
        return class_slug.replace("-", " ").title()
    return "Other"


def _infer_dashboard_class_from_vehicle(obj):
    """
    Catalog rows set db.specs; NPC/bio-deployed haulers often do not. Use the same
    autonomous_hauler tag categories as typeclasses.haulers and deploy scripts.
    """
    if not hasattr(obj, "tags"):
        return None, None
    if obj.tags.has("autonomous_hauler", category="fauna"):
        return "fauna-hauler", "Fauna Hauler"
    if obj.tags.has("autonomous_hauler", category="flora"):
        return "flora-hauler", "Flora Hauler"
    if obj.tags.has("autonomous_hauler", category="mining"):
        return "hauler", "Hauler"
    if getattr(obj.db, "vehicle_kind", None) == "hauler":
        return "hauler", "Hauler"
    return None, None


def dashboard_ship_row(obj):
    """
    One JSON row per owned vehicle for dashboard / control-surface APIs.
    """
    loc = obj.location.key if obj.location else None
    pilot_key = None
    pilot = getattr(obj.db, "pilot", None)
    if pilot is not None:
        pilot_key = getattr(pilot, "key", str(pilot))

    summary = obj.get_vehicle_summary() if hasattr(obj, "get_vehicle_summary") else obj.key

    is_autonomous = False
    if hasattr(obj, "tags"):
        is_autonomous = (
            obj.tags.has("autonomous_hauler", category="mining")
            or obj.tags.has("autonomous_hauler", category="flora")
            or obj.tags.has("autonomous_hauler", category="fauna")
        )

    specs = getattr(obj.db, "specs", None) or {}
    class_slug = _slugify_vehicle_class(specs)
    class_label = _label_for_vehicle_class(specs, class_slug)
    if class_slug == "unknown":
        inf_slug, inf_label = _infer_dashboard_class_from_vehicle(obj)
        if inf_slug:
            class_slug, class_label = inf_slug, inf_label

    return {
        "id": obj.id,
        "key": obj.key,
        "location": loc,
        "pilot": pilot_key,
        "state": getattr(obj.db, "state", None),
        "summary": summary,
        "is_autonomous": is_autonomous,
        "vehicleClassSlug": class_slug,
        "vehicleClassLabel": class_label,
    }
