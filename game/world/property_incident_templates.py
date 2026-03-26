"""
Named property incidents (Phase 2): templates, queue trim, expiry, income multiplier.
"""

from __future__ import annotations

import random
import uuid
from datetime import timedelta

from world.time import parse_iso, to_iso

INCIDENT_QUEUE_MAX = 50
INCIDENT_INCOME_MULT_FLOOR = 0.75
INCIDENT_INCOME_MULT_CEIL = 1.25

_PROPERTY_INCIDENT_TEMPLATES = (
    {
        "id": "res_noise_complaint",
        "zones": ("residential",),
        "base_weight": 10,
        "severity": "warning",
        "title": "Noise complaint",
        "summary": "Neighbors filed a noise complaint with the parcel board.",
        "effects": {"kind": "staff_load", "staff_role": "security"},
        "broadcast": False,
    },
    {
        "id": "res_lease_renewal",
        "zones": ("residential",),
        "base_weight": 12,
        "severity": "info",
        "title": "Lease renewal interest",
        "summary": "Strong renewal interest yields a short-term rent tailwind.",
        "effects": {"kind": "income_mult", "income_mult": 1.05},
        "duration_hours": 48,
        "broadcast": False,
    },
    {
        "id": "res_water_pressure",
        "zones": ("residential",),
        "base_weight": 8,
        "severity": "warning",
        "title": "Water pressure fluctuation",
        "summary": "Building loop reports pressure fluctuation; repairs need scheduling.",
        "effects": {"kind": "flat_cost", "flat_cost_cr": 250},
        "broadcast": False,
    },
    {
        "id": "com_inspection_notice",
        "zones": ("commercial",),
        "base_weight": 9,
        "severity": "warning",
        "title": "Inspection notice",
        "summary": "District commercial inspectors posted a routine inspection window.",
        "effects": {"kind": "none"},
        "broadcast": True,
    },
    {
        "id": "com_supply_shortage",
        "zones": ("commercial",),
        "base_weight": 11,
        "severity": "info",
        "title": "Supply shortage",
        "summary": "A supplier missed a delivery slot; footfall spend dips briefly.",
        "effects": {"kind": "income_mult", "income_mult": 0.92},
        "duration_hours": 24,
        "broadcast": False,
    },
    {
        "id": "com_campaign_spike",
        "zones": ("commercial",),
        "base_weight": 11,
        "severity": "info",
        "title": "Traffic campaign spike",
        "summary": "A local promo cluster drove a short-lived traffic surge.",
        "effects": {"kind": "income_mult", "income_mult": 1.15},
        "duration_hours": 12,
        "broadcast": False,
    },
    {
        "id": "ind_line_jam",
        "zones": ("industrial",),
        "base_weight": 10,
        "severity": "warning",
        "title": "Line jam",
        "summary": "A conveyor jam slowed line output until crews clear the fault.",
        "effects": {"kind": "income_mult", "income_mult": 0.88},
        "broadcast": False,
    },
    {
        "id": "ind_permit_audit",
        "zones": ("industrial",),
        "base_weight": 5,
        "severity": "critical",
        "title": "Permit audit",
        "summary": "Regulators opened a permit audit; compliance fees apply on resolution.",
        "effects": {"kind": "flat_cost", "flat_cost_cr": 2000},
        "broadcast": True,
    },
    {
        "id": "ind_scrap_windfall",
        "zones": ("industrial",),
        "base_weight": 8,
        "severity": "info",
        "title": "Scrap windfall",
        "summary": "Reclamation crews recovered unexpected scrap value from the yard.",
        "effects": {"kind": "none"},
        "spawn_bonus_cr": 450,
        "broadcast": False,
    },
)


def incident_pressure(security_quality: int) -> float:
    """Match legacy roll probability: threshold/10000 with threshold = 500/(1+quality)."""
    q = max(0, int(security_quality or 0))
    return min(0.2, 500.0 / (10000.0 * (1 + q)))


def _build_effects_dict(tmpl: dict, now) -> dict:
    effects = dict(tmpl["effects"])
    kind = effects.get("kind")
    if kind == "income_mult":
        dh = tmpl.get("duration_hours")
        if dh is not None:
            effects["expires_at_iso"] = to_iso(now + timedelta(hours=float(dh)))
    return effects


def build_incident_record(holding, now, tmpl: dict) -> dict:
    zone = (holding.db.zone or "residential").lower()
    ev_id = f"evt_{holding.id}_{uuid.uuid4().hex[:16]}"
    return {
        "id": ev_id,
        "template_id": tmpl["id"],
        "severity": tmpl["severity"],
        "title": tmpl["title"],
        "summary": tmpl["summary"],
        "created_at_iso": to_iso(now),
        "due_at_iso": None,
        "resolved": False,
        "resolved_at_iso": None,
        "zone": zone,
        "effects": _build_effects_dict(tmpl, now),
    }


def pick_incident(holding, now) -> tuple[dict, int] | None:
    """
    Roll incident_pressure vs security quality; if triggered, pick a weighted template.
    Returns (incident_dict, spawn_bonus_cr) or None.
    """
    staff = (holding.db.staff or {}).get("roles", {})
    sec = staff.get("security", {})
    quality = int(sec.get("quality") or 0)
    if random.random() >= incident_pressure(quality):
        return None
    zone = (holding.db.zone or "residential").lower()
    eligible = [t for t in _PROPERTY_INCIDENT_TEMPLATES if zone in t["zones"]]
    if not eligible:
        return None
    weights = [int(t["base_weight"]) for t in eligible]
    tmpl = random.choices(eligible, weights=weights, k=1)[0]
    record = build_incident_record(holding, now, tmpl)
    bonus = int(tmpl.get("spawn_bonus_cr") or 0)
    return record, bonus


def trim_property_event_queue(q: list) -> list:
    """Cap at INCIDENT_QUEUE_MAX: drop oldest resolved first, then oldest overall."""
    q = [dict(e) for e in (q or [])]
    while len(q) > INCIDENT_QUEUE_MAX:
        resolved = [e for e in q if e.get("resolved")]
        if resolved:
            resolved.sort(key=lambda e: str(e.get("created_at_iso") or e.get("due_at_iso") or ""))
            victim = resolved[0]
            q.remove(victim)
        else:
            q.sort(key=lambda e: str(e.get("created_at_iso") or e.get("due_at_iso") or ""))
            q.pop(0)
    return q


def expire_property_incidents(holding, now) -> None:
    """Auto-resolve incidents whose income_mult effect has passed expires_at_iso."""
    q = list(holding.db.event_queue or [])
    changed = False
    for e in q:
        if e.get("resolved"):
            continue
        eff = e.get("effects") or {}
        if eff.get("kind") != "income_mult":
            continue
        exp_iso = eff.get("expires_at_iso")
        if not exp_iso:
            continue
        dt = parse_iso(exp_iso)
        if dt and now >= dt:
            e["resolved"] = True
            e["resolved_at_iso"] = to_iso(now)
            changed = True
    if changed:
        holding.db.event_queue = q


def active_incident_income_multiplier(holding, now) -> float:
    """
    Multiply stacking income_mult from unresolved, unexpired incidents.
    Clamped to [INCIDENT_INCOME_MULT_FLOOR, INCIDENT_INCOME_MULT_CEIL].
    """
    mult = 1.0
    for e in list(holding.db.event_queue or []):
        if e.get("resolved"):
            continue
        eff = e.get("effects") or {}
        if eff.get("kind") != "income_mult":
            continue
        m = float(eff.get("income_mult") or 1.0)
        exp_iso = eff.get("expires_at_iso")
        if exp_iso:
            dt = parse_iso(exp_iso)
            if dt and now >= dt:
                continue
        mult *= m
    return max(
        INCIDENT_INCOME_MULT_FLOOR,
        min(INCIDENT_INCOME_MULT_CEIL, mult),
    )


def template_by_id(template_id: str) -> dict | None:
    tid = (template_id or "").strip()
    for t in _PROPERTY_INCIDENT_TEMPLATES:
        if t["id"] == tid:
            return t
    return None
