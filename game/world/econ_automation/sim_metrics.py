"""
Aggregated simulation metrics for economy automation and world telemetry.

Returns plain dicts (JSON-serializable) and 0..1 normalized pressures for decide_rebalance.
"""

from __future__ import annotations

from typing import Any

# States from CommodityDemandEngine.STATE_BANDS — high bands tighten prices.
HIGH_STRESS_STATES = frozenset({"tight", "shortage", "emergency"})

# Normalization caps (document tuning here; rebalance policy stays conservative).
_LOGISTICS_DUE_CAP = 40.0
_PROPERTY_HOLDINGS_CAP = 150.0
_COMMODITY_MEAN_MULT_BASE = 1.0
_COMMODITY_MEAN_MULT_SPAN = 0.40


def _commodity_rows(engine) -> dict[str, dict]:
    if not engine:
        return {}
    try:
        engine._ensure_commodity_rows()
        st = engine.state
        return dict(st.get("commodities") or {})
    except Exception:
        return {}


def raw_commodity_demand_metrics(engine=None) -> dict[str, Any]:
    """
    Snapshot from CommodityDemandEngine.state commodities table.
    If engine is None or fails, returns available=False.
    """
    if engine is None:
        return {"available": False, "reason": "no_engine"}
    rows = _commodity_rows(engine)
    if not rows:
        return {"available": False, "reason": "empty_commodities"}

    mults: list[float] = []
    high = 0
    by_state: dict[str, int] = {}
    top: list[tuple[str, float, str]] = []

    for key, row in rows.items():
        m = float(row.get("price_multiplier") or 1.0)
        mults.append(m)
        st = str(row.get("state") or "normal")
        by_state[st] = by_state.get(st, 0) + 1
        if st in HIGH_STRESS_STATES:
            high += 1
        top.append((str(key), m, st))

    top.sort(key=lambda t: t[1], reverse=True)
    mean_mult = sum(mults) / max(1, len(mults))
    frac_high = high / max(1, len(rows))

    return {
        "available": True,
        "commodityCount": len(rows),
        "meanPriceMultiplier": round(mean_mult, 4),
        "highStressFraction": round(frac_high, 4),
        "stateCounts": by_state,
        "topStress": [{"key": k, "priceMultiplier": round(m, 4), "state": s} for k, m, s in top[:8]],
    }


def raw_hauler_logistics_metrics() -> dict[str, Any]:
    """Dispatch table: due haulers and total registered rows."""
    try:
        from django.utils import timezone

        from world.models import HaulerDispatchRow

        now = timezone.now()
        due = HaulerDispatchRow.objects.filter(next_run__lte=now).count()
        total = HaulerDispatchRow.objects.count()
        return {
            "available": True,
            "dueCount": due,
            "dispatchRowCount": total,
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def raw_property_operation_metrics(registry=None) -> dict[str, Any]:
    """Active property holdings count from global registry script."""
    if registry is None:
        try:
            from typeclasses.property_operation_registry import get_property_operation_registry

            registry = get_property_operation_registry(create_missing=False)
        except Exception as exc:
            return {"available": False, "reason": str(exc)}
    if registry is None:
        return {"available": False, "reason": "no_registry"}
    try:
        ids = list(registry.db.active_holding_ids or [])
        return {"available": True, "activeHoldingCount": len(ids)}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def normalize_commodity_pressure(raw: dict[str, Any]) -> float:
    """
    Map commodity stress to 0..1 for automation.
    Combines high-stress row fraction with elevation of mean multiplier above baseline.
    """
    if not raw.get("available"):
        return 0.0
    frac = float(raw.get("highStressFraction") or 0.0)
    mean_m = float(raw.get("meanPriceMultiplier") or 1.0)
    mean_component = max(0.0, min(1.0, (mean_m - _COMMODITY_MEAN_MULT_BASE) / _COMMODITY_MEAN_MULT_SPAN))
    # Weight: half from band concentration, half from average tightness.
    return max(0.0, min(1.0, 0.5 * frac + 0.5 * mean_component))


def normalize_logistics_pressure(raw: dict[str, Any]) -> float:
    if not raw.get("available"):
        return 0.0
    due = int(raw.get("dueCount") or 0)
    return max(0.0, min(1.0, due / _LOGISTICS_DUE_CAP))


def normalize_property_pressure(raw: dict[str, Any]) -> float:
    if not raw.get("available"):
        return 0.0
    n = int(raw.get("activeHoldingCount") or 0)
    return max(0.0, min(1.0, n / _PROPERTY_HOLDINGS_CAP))


def collect_sim_metrics_snapshot(
    *,
    commodity_engine=None,
    property_registry=None,
) -> dict[str, Any]:
    """
    Full raw snapshot for telemetry / rebalance history.

    If commodity_engine is None, loads via get_commodity_demand_engine(create_missing=False).
    """
    if commodity_engine is None:
        try:
            from typeclasses.commodity_demand import get_commodity_demand_engine

            commodity_engine = get_commodity_demand_engine(create_missing=False)
        except Exception:
            commodity_engine = None

    comm = raw_commodity_demand_metrics(commodity_engine)
    haul = raw_hauler_logistics_metrics()
    prop = raw_property_operation_metrics(property_registry)

    return {
        "commodityDemand": comm,
        "logistics": haul,
        "propertyOps": prop,
        "normalized": {
            "commodityPressure": normalize_commodity_pressure(comm),
            "logisticsPressure": normalize_logistics_pressure(haul),
            "propertyPressure": normalize_property_pressure(prop),
        },
    }


def normalized_pressures_for_automation(
    *,
    commodity_engine=None,
    property_registry=None,
) -> tuple[float, float, float, dict[str, Any]]:
    """
    Returns (commodity_pressure, logistics_pressure, property_pressure, raw_snapshot)
    each in 0..1 for decide_rebalance.
    """
    snap = collect_sim_metrics_snapshot(
        commodity_engine=commodity_engine,
        property_registry=property_registry,
    )
    n = snap["normalized"]
    return (
        float(n["commodityPressure"]),
        float(n["logisticsPressure"]),
        float(n["propertyPressure"]),
        snap,
    )


def suggested_ambient_ids_for_commodity_stress(raw_commodity: dict[str, Any]) -> list[str]:
    """
    Optional bridge: template ids to bias ambient news when commodities are tight.
    Caller merges into eligible pool; does not replace random selection.
    """
    if not raw_commodity.get("available"):
        return []
    mean_m = float(raw_commodity.get("meanPriceMultiplier") or 1.0)
    frac = float(raw_commodity.get("highStressFraction") or 0.0)
    out: list[str] = []
    if mean_m >= 1.12 or frac >= 0.15:
        out.append("refinery_backlog")
    if mean_m >= 1.08 or frac >= 0.10:
        out.append("market_listing_flurry")
    return out
