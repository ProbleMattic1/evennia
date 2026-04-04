"""
Per-venue throughput limits (hauler deliveries, refinery bay ingress).
"""

from __future__ import annotations

from world.venues import get_venue


def get_venue_logistics(venue_id: str) -> dict[str, float]:
    spec = get_venue(venue_id)
    raw = dict(spec.get("logistics") or {})
    return {
        "max_hauler_tons_per_tick": float(raw.get("max_hauler_tons_per_tick", 1e12)),
        "refinery_ingress_cap_tons": float(raw.get("refinery_ingress_cap_tons", 1e12)),
    }
