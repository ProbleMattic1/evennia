"""
Web nav grouping for exits — single source of truth for section labels and ordering.

Evennia: store overrides on the Exit (db.nav_section, db.nav_order) when bootstrap
cannot infer a section. Defaults derive from destination.db.venue_id and room keys.
"""

from __future__ import annotations

NAV_SECTION_CATEGORY = "nav_section"

# Canonical section keys → display label (stable API for the web UI).
SECTION_LABELS: dict[str, str] = {
    "plex_services": "Station & services",
    "nanomega_industrial": "Nanomega industrial",
    "nanomega_bio": "Nanomega resource colony",
    "frontier_industrial": "Frontier industrial",
    "frontier_bio": "Frontier resource colony",
    "killstar": "Killstar",
    "transit": "Transit",
    "other": "Other",
}

# Global ordering of sections in the destinations panel (lower first).
SECTION_ORDER: dict[str, int] = {
    "transit": 0,
    "plex_services": 10,
    "killstar": 20,
    "nanomega_industrial": 30,
    "nanomega_bio": 35,
    "frontier_industrial": 40,
    "frontier_bio": 45,
    "other": 99,
}


def _infer_section_key(exit_obj) -> str:
    """Default section from exit tags, destination venue, and room key hints."""
    tags = getattr(exit_obj, "tags", None)
    if tags:
        nav_tags = tags.get(category=NAV_SECTION_CATEGORY, return_list=True)
        if nav_tags:
            return str(nav_tags[0])

    dest = getattr(exit_obj, "destination", None)
    if not dest:
        return "other"

    override = getattr(exit_obj.db, "nav_section", None)
    if override:
        return str(override).strip().lower()

    dk = dest.key or ""
    dl = dk.lower()

    # Marcus / Killstar stack (rooms may omit venue_id)
    if "killstar" in dl or "marcus killstar" in dl:
        return "killstar"

    vid = getattr(dest.db, "venue_id", None)
    if not vid:
        return "other"

    vid = str(vid)

    if vid == "nanomega_core":
        if "industrial" in dl or "resource colony" in dl:
            if "flora" in dl or "fauna" in dl:
                return "nanomega_bio"
            return "nanomega_industrial"
        return "plex_services"

    if vid == "frontier_outpost":
        if "industrial" in dl or "resource colony" in dl:
            if "flora" in dl or "fauna" in dl:
                return "frontier_bio"
            return "frontier_industrial"
        return "plex_services"

    # New venues: add a branch here or set db.nav_section / tags on the exit.
    return "other"


def nav_fields_for_exit(exit_obj) -> tuple[str, str, int, int]:
    """
    Returns (section_key, section_label, section_order, row_order).

    row_order: per-exit ordering within the section (db.nav_order or 0).
    """
    key = _infer_section_key(exit_obj)
    if key not in SECTION_LABELS:
        key = "other"
    label = SECTION_LABELS[key]
    sec_ord = SECTION_ORDER.get(key, SECTION_ORDER["other"])
    row_ord = int(getattr(exit_obj.db, "nav_order", None) or 0)
    return key, label, sec_ord, row_ord
