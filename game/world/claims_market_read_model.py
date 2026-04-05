"""
Aggregated claims-market rows for web UI. Built periodically by ClaimsMarketSnapshotScript
and refreshed synchronously after mutations so GET handlers avoid O(n) search_tag per request.
"""

from __future__ import annotations

from typing import Any

from evennia import search_object, search_script, search_tag


def _iso_script_eta(script_key: str) -> str | None:
    disc = search_script(script_key)
    if not disc:
        return None
    eta = disc[0].db.next_discovery_at
    if eta is None:
        return None
    return eta.isoformat()


def _hazard_label(hazard: float) -> str:
    if hazard <= 0.20:
        return "Low"
    if hazard <= 0.50:
        return "Medium"
    return "High"


def _append_primary_site_rows(
    site,
    claims: list[dict[str, Any]],
    survey_out: list[dict[str, Any]] | None,
    *,
    claims_market_row_extras,
    use_multi_rarity: bool,
):
    from typeclasses.claim_market import claims_market_site_kind
    from typeclasses.mining import _volume_tier

    if use_multi_rarity:
        from world.mining_site_metrics import _resource_rarity_tier_multi_catalog as _rarity_tier
    else:
        from typeclasses.mining import _resource_rarity_tier as _rarity_tier

    room = site.location
    room_key = room.key if room else "unknown"
    deposit = site.db.deposit or {}
    comp = deposit.get("composition", {})
    families = ", ".join(sorted(comp.keys())) if comp else "unknown"
    richness = float(deposit.get("richness", 0.0))
    hazard = float(site.db.hazard_level or 0.0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)

    volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
    resource_rarity_tier, resource_rarity_tier_cls = _rarity_tier(comp)
    hazard_label = _hazard_label(hazard)
    sk = claims_market_site_kind(site)
    row = {
        "siteKey": site.key,
        "roomKey": room_key,
        "resources": families,
        "richness": round(richness, 2),
        "volumeTier": volume_tier,
        "volumeTierCls": volume_tier_cls,
        "resourceRarityTier": resource_rarity_tier,
        "resourceRarityTierCls": resource_rarity_tier_cls,
        "hazardLevel": round(hazard, 2),
        "hazardLabel": hazard_label,
        "baseOutputTons": base_tons,
        "siteKind": sk,
    }
    row.update(claims_market_row_extras(site))
    row["playerListing"] = False
    claims.append(row)
    if survey_out is not None:
        survey_out.append(
            {
                "siteKey": site.key,
                "roomKey": room_key,
                "resources": families,
                "richness": richness,
                "volumeTier": volume_tier,
                "volumeTierCls": volume_tier_cls,
                "resourceRarityTier": resource_rarity_tier,
                "resourceRarityTierCls": resource_rarity_tier_cls,
                "hazardLevel": hazard,
                "siteKind": sk,
            }
        )


def build_claims_market_snapshot_payload() -> dict[str, Any]:
    """
    Full scan of listable resource sites + property listings + claim listings rows.
    Returns JSON-serializable dict: claims, nextDiscoveryAt, nextDiscoveryByKind,
    mineClaims, floraClaims, faunaClaims.
    """
    from typeclasses.claim_listings import get_claim_listings_rows
    from typeclasses.claim_market import (
        _existing_deed_for_site,
        _find_owned_resource_site_by_id,
        _get_property_listings_script,
        claims_market_site_kind,
        claims_market_row_extras,
        site_is_claims_market_listable,
    )
    from typeclasses.mining import _resource_rarity_tier, _volume_tier

    mining_sites = list(search_tag("mining_site", category="mining"))
    flora_sites = list(search_tag("flora_site", category="flora"))
    fauna_sites = list(search_tag("fauna_site", category="fauna"))

    seen_ids: set[int] = set()
    listable: list = []
    for s in mining_sites + flora_sites + fauna_sites:
        sid = getattr(s, "id", None)
        if sid is None or sid in seen_ids:
            continue
        if not site_is_claims_market_listable(s):
            continue
        seen_ids.add(sid)
        listable.append(s)

    claims: list[dict[str, Any]] = []
    mine_survey: list[dict[str, Any]] = []
    flora_survey: list[dict[str, Any]] = []
    fauna_survey: list[dict[str, Any]] = []

    for site in listable:
        use_multi = bool(
            site.tags.has("flora_site", category="flora")
            or site.tags.has("fauna_site", category="fauna")
        )
        sk = claims_market_site_kind(site)
        survey = mine_survey if sk == "mining" else flora_survey if sk == "flora" else fauna_survey
        _append_primary_site_rows(
            site,
            claims,
            survey,
            claims_market_row_extras=claims_market_row_extras,
            use_multi_rarity=use_multi,
        )

    all_sites_by_id: dict[int, Any] = {}
    for s in mining_sites + flora_sites + fauna_sites:
        if s.id is not None:
            all_sites_by_id[s.id] = s

    script = _get_property_listings_script()
    if script:
        for ent in list(script.db.listings or []):
            sid = ent.get("site_id")
            site = None
            if sid is not None:
                site = all_sites_by_id.get(sid)
                if site is None:
                    try:
                        site = _find_owned_resource_site_by_id(int(sid))
                    except (TypeError, ValueError):
                        site = None
            if not site:
                continue
            if getattr(site.db, "is_claimed", False):
                continue
            if _existing_deed_for_site(site):
                continue
            seller_key = "?"
            seller_id = ent.get("seller_id")
            if seller_id:
                found = search_object("#" + str(seller_id))
                if found:
                    seller_key = found[0].key
            room = site.location
            room_key = room.key if room else "unknown"
            deposit = site.db.deposit or {}
            comp = deposit.get("composition", {})
            families = ", ".join(sorted(comp.keys())) if comp else "unknown"
            richness = float(deposit.get("richness", 0.0))
            hazard = float(site.db.hazard_level or 0.0)
            base_tons = float(deposit.get("base_output_tons", 0) or 0)
            use_multi = bool(
                site.tags.has("flora_site", category="flora")
                or site.tags.has("fauna_site", category="fauna")
            )
            if use_multi:
                from world.mining_site_metrics import _resource_rarity_tier_multi_catalog as _rt
            else:
                _rt = _resource_rarity_tier
            volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
            resource_rarity_tier, resource_rarity_tier_cls = _rt(comp)
            sk = claims_market_site_kind(site)
            claims.append(
                {
                    "siteKey": site.key,
                    "roomKey": room_key,
                    "resources": families,
                    "richness": round(richness, 2),
                    "volumeTier": volume_tier,
                    "volumeTierCls": volume_tier_cls,
                    "resourceRarityTier": resource_rarity_tier,
                    "resourceRarityTierCls": resource_rarity_tier_cls,
                    "hazardLevel": round(hazard, 2),
                    "hazardLabel": _hazard_label(hazard),
                    "baseOutputTons": base_tons,
                    "listingPriceCr": int(ent.get("price", 0) or 0),
                    "purchasable": True,
                    "playerListing": True,
                    "sellerKey": seller_key,
                    "siteKind": sk,
                    "listingKind": "property",
                }
            )

    for row in get_claim_listings_rows():
        claims.append(row)

    next_mining = _iso_script_eta("site_discovery_engine")
    next_flora = _iso_script_eta("flora_site_discovery_engine")
    next_fauna = _iso_script_eta("fauna_site_discovery_engine")

    return {
        "claims": claims,
        "nextDiscoveryAt": next_mining,
        "nextDiscoveryByKind": {
            "mining": next_mining,
            "flora": next_flora,
            "fauna": next_fauna,
        },
        "mineClaims": mine_survey,
        "floraClaims": flora_survey,
        "faunaClaims": fauna_survey,
    }


def refresh_claims_market_snapshot() -> dict[str, Any]:
    """Rebuild snapshot and persist on the global script (if present)."""
    payload = build_claims_market_snapshot_payload()
    found = search_script("claims_market_snapshot")
    if found:
        found[0].db.snapshot = payload
    return payload


def get_claims_market_snapshot() -> dict[str, Any]:
    """Return cached snapshot, or build synchronously if missing or empty."""
    found = search_script("claims_market_snapshot")
    if found:
        snap = found[0].db.snapshot
        if isinstance(snap, dict) and "claims" in snap:
            return snap
    return refresh_claims_market_snapshot()


def invalidate_claims_market_snapshot() -> None:
    """Call after mutations that change listable sites or listings."""
    refresh_claims_market_snapshot()
