"""
Mining camp (6 probed sites) and mining base (4 camps) — production multipliers.
"""

from __future__ import annotations

import uuid
from typing import Any

from evennia.objects.models import ObjectDB

from world.venue_resolve import venue_id_for_object

CAMP_OUTPUT_MULT = 1.1
BASE_OUTPUT_MULT = 1.21


def probe_complete(site) -> bool:
    return int(getattr(site.db, "survey_level", 0) or 0) >= 3


def cluster_multiplier_for_site(site) -> float:
    cid = getattr(site.db, "cluster_id", None) or ""
    if not isinstance(cid, str):
        return 1.0
    if cid.startswith("base:"):
        return BASE_OUTPUT_MULT
    if cid.startswith("camp:"):
        return CAMP_OUTPUT_MULT
    return 1.0


def _get_mining_site_by_id(site_id: int):
    try:
        o = ObjectDB.objects.get(id=int(site_id))
    except ObjectDB.DoesNotExist as exc:
        raise ValueError(f"No object with id {site_id}.") from exc
    if not o.tags.has("mining_site", category="mining"):
        raise ValueError(f"Object #{site_id} is not a mining site.")
    return o


def _cluster_free(site) -> bool:
    cid = getattr(site.db, "cluster_id", None)
    return not cid


def try_form_camp(owner, site_ids: list[int]) -> tuple[bool, str]:
    """Form a camp from six owned, probed sites in the same district/venue."""
    from typeclasses.mining_cluster_registry import get_mining_cluster_registry

    if len(site_ids) != 6:
        return False, "A mining camp requires exactly six site ids."
    if len(set(site_ids)) != 6:
        return False, "Site ids must be distinct."

    sites: list[Any] = []
    for sid in site_ids:
        try:
            sites.append(_get_mining_site_by_id(sid))
        except ValueError as exc:
            return False, str(exc)

    for s in sites:
        if s.db.owner != owner:
            return False, f"{s.key} is not owned by you."
        if not probe_complete(s):
            return False, f"{s.key} must reach full survey (level 3) first."
        if not _cluster_free(s):
            return False, f"{s.key} is already in a cluster."
        if not getattr(s.db, "mining_district_key", None):
            return False, f"{s.key} has no district key (world migration pending?)."

    dk = str(sites[0].db.mining_district_key)
    vid = venue_id_for_object(sites[0]) or "nanomega_core"
    for s in sites[1:]:
        if str(s.db.mining_district_key) != dk:
            return False, "All sites must share the same mining district."
        if venue_id_for_object(s) != vid:
            return False, "All sites must be in the same venue."

    camp_id = f"camp:{uuid.uuid4()}"
    reg = get_mining_cluster_registry()
    clusters = dict(reg.db.clusters or {})
    clusters[camp_id] = {
        "kind": "camp",
        "owner_id": owner.id,
        "district_key": dk,
        "venue_id": vid,
        "site_ids": [s.id for s in sites],
        "merged_into": None,
    }
    reg.db.clusters = clusters

    for s in sites:
        s.db.cluster_id = camp_id

    return True, f"Mining camp formed: |w{camp_id}|n ({len(sites)} sites). Output +10%."


def try_form_base(owner, camp_cluster_ids: list[str]) -> tuple[bool, str]:
    """Merge four camps into one mining base (+21% output vs unclustered)."""
    from typeclasses.mining_cluster_registry import get_mining_cluster_registry

    if len(camp_cluster_ids) != 4:
        return False, "A mining base requires exactly four camp cluster ids."
    if len(set(camp_cluster_ids)) != 4:
        return False, "Camp ids must be distinct."

    reg = get_mining_cluster_registry()
    clusters = dict(reg.db.clusters or {})

    camp_records = []
    all_site_ids: list[int] = []
    dk = None
    vid = None

    for cid in camp_cluster_ids:
        if not isinstance(cid, str) or not cid.startswith("camp:"):
            return False, f"Invalid camp id {cid!r} (expected camp:…)."
        rec = clusters.get(cid)
        if not rec or rec.get("kind") != "camp":
            return False, f"Unknown camp {cid!r}."
        if rec.get("merged_into"):
            return False, f"Camp {cid} was already merged into a base."
        if int(rec.get("owner_id", 0)) != owner.id:
            return False, f"Camp {cid} is not yours."
        sids = rec.get("site_ids") or []
        if len(sids) != 6:
            return False, f"Camp {cid} has invalid site list."
        c_dk = rec.get("district_key")
        c_vid = rec.get("venue_id")
        if dk is None:
            dk, vid = c_dk, c_vid
        elif c_dk != dk or c_vid != vid:
            return False, "All camps must share the same district and venue."
        camp_records.append((cid, rec))
        all_site_ids.extend(int(x) for x in sids)

    if len(set(all_site_ids)) != 24:
        return False, "Camps overlap on sites; cannot merge."

    base_id = f"base:{uuid.uuid4()}"
    for cid, rec in camp_records:
        rec = dict(rec)
        rec["merged_into"] = base_id
        clusters[cid] = rec

    clusters[base_id] = {
        "kind": "base",
        "owner_id": owner.id,
        "district_key": dk,
        "venue_id": vid,
        "camp_ids": list(camp_cluster_ids),
        "site_ids": all_site_ids,
    }
    reg.db.clusters = clusters

    for sid in all_site_ids:
        s = _get_mining_site_by_id(sid)
        s.db.cluster_id = base_id

    return True, f"Mining base formed: |w{base_id}|n (24 sites). Output +21%."
