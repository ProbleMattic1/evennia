"""
Aggregated control-surface read model for the frontend 3-column UI.

Single endpoint: GET /ui/control-surface
Returns a ControlSurfaceState JSON payload containing every piece of information
the 3-column shell needs — character stats, alerts, missions, inventory, ships,
resources (mirrored as mines for compatibility), properties, processing summary, live market rates, and dynamic nav.

Most blocks compose helpers imported from views.py or world.*; production-site
rows use ``world.mining_site_metrics.owned_production_sites_for_dashboard``.
"""

import json
from collections import defaultdict

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from evennia import search_object

from world.inventory_taxonomy import empty_inventory_payload, serialize_inventory_by_bucket
from world.time import (
    FLORA_DELIVERY_PERIOD,
    MINING_DELIVERY_PERIOD,
    current_flora_delivery_slot_start_iso,
    current_mining_delivery_slot_start_iso,
    next_flora_delivery_boundary_iso,
    next_mining_delivery_boundary_iso,
    to_iso,
    utc_now,
)

from world.bootstrap_hub import HUB_ROOM_KEY as CORE_HUB_ROOM_KEY
from world.venue_resolve import hub_for_object, processing_plant_room_for_object, treasury_bank_id_for_object, venue_id_for_object

from .views import (
    _dashboard_inventory_item_for_obj,
    _dashboard_property_portfolio,
    _first_object,
    _group_alerts,
    _playable_characters,
    _resolve_character_for_web,
    _room_actions,
    _room_exits,
)

# v2: ``resources``, ``nav.resources``, ``production*`` aggregate keys (``mines`` / ``mining*`` retained).
SCHEMA_VERSION = 2


# ---------------------------------------------------------------------------
# Block serializers
# ---------------------------------------------------------------------------


def _serialize_character_block(char, credits):
    rpg = {}
    if hasattr(char, "get_rpg_dashboard_snapshot"):
        rpg = char.get_rpg_dashboard_snapshot() or {}
    return {
        "id": char.id,
        "key": char.key,
        "room": char.location.key if char.location else None,
        "roomId": char.location.id if char.location else None,
        "credits": credits,
        **rpg,
    }


def _serialize_inventory(char):
    return serialize_inventory_by_bucket(char, _dashboard_inventory_item_for_obj)


def _serialize_ships(char):
    autonomous_by_key = defaultdict(list)
    ships_other = []

    for entry in char.db.owned_vehicles or []:
        if hasattr(entry, "key"):
            obj = entry
        else:
            found = search_object(entry)
            obj = found[0] if found else None
        if not obj:
            continue
        loc = obj.location.key if obj.location else None
        pilot_key = None
        pilot = getattr(obj.db, "pilot", None)
        if pilot is not None:
            pilot_key = getattr(pilot, "key", str(pilot))
        summary = obj.get_vehicle_summary() if hasattr(obj, "get_vehicle_summary") else obj.key
        is_autonomous = obj.tags.has("autonomous_hauler", category="mining")
        row = {
            "id": obj.id,
            "key": obj.key,
            "location": loc,
            "pilot": pilot_key,
            "state": getattr(obj.db, "state", None),
            "summary": summary,
            "is_autonomous": is_autonomous,
        }
        if is_autonomous:
            autonomous_by_key[obj.key].append(row)
        else:
            ships_other.append(row)

    ships = []
    for ship_key in sorted(autonomous_by_key.keys()):
        rows_g = autonomous_by_key[ship_key]
        if len(rows_g) == 1:
            ships.append(rows_g[0])
        else:
            ships.append({
                "id": rows_g[0]["id"],
                "key": ship_key,
                "location": None,
                "pilot": rows_g[0]["pilot"],
                "state": rows_g[0]["state"],
                "summary": rows_g[0]["summary"],
                "is_autonomous": True,
                "count": len(rows_g),
                "stacked": True,
                "ids": [r["id"] for r in rows_g],
                "locations": [r["location"] for r in rows_g],
            })
    ships.extend(ships_other)
    return ships


def _serialize_resources(char):
    from world.mining_site_metrics import owned_production_sites_for_dashboard

    return owned_production_sites_for_dashboard(char)


def _personal_plant_ore_stored_value_cr(char):
    """
    Bid-valued ore sitting in this character's plant-assigned silo(s).

    Uses the processing plant room only (O(room contents)); avoids a global
    tag scan on every control-surface poll. Extend with more room keys if you
    add additional haul destinations.
    """
    from typeclasses.haulers import get_plant_player_storage
    from typeclasses.mining import get_commodity_bid

    room = processing_plant_room_for_object(char)
    if not room or not char:
        return 0
    storage = get_plant_player_storage(room, char)
    if not storage:
        return 0
    sloc = storage.location
    total = 0.0
    for k, tons in (storage.db.inventory or {}).items():
        total += float(tons) * get_commodity_bid(str(k), location=sloc)
    return int(round(total))


def _serialize_processing_summary(char):
    from typeclasses.haulers import get_plant_ore_receiving_bay
    from typeclasses.mining import COMMODITY_ASK_OVER_BID
    from typeclasses.refining import PROCESSING_FEE_RATE, RAW_SALE_FEE_RATE, REFINING_RECIPES

    room = processing_plant_room_for_object(char) if char else None
    if not room:
        return None

    receiving_bay = get_plant_ore_receiving_bay(room)
    refinery_obj = None
    for obj in room.contents:
        if refinery_obj is None and obj.is_typeclass(
            "typeclasses.refining.Refinery", exact=False
        ):
            refinery_obj = obj

    raw_used = 0.0
    raw_cap = 0.0
    if receiving_bay:
        raw_used = receiving_bay.total_mass() if hasattr(receiving_bay, "total_mass") else 0.0
        raw_cap = float(getattr(receiving_bay.db, "capacity_tons", 0) or 0)

    refinery_input_tons = 0.0
    refinery_output_value = 0
    miner_queue_ore_tons = 0.0
    miner_output_value_total = 0
    if refinery_obj:
        in_inv = refinery_obj.db.input_inventory or {}
        refinery_input_tons = round(sum(float(v) for v in in_inv.values()), 2)
        out_inv = refinery_obj.db.output_inventory or {}
        for key, units in out_inv.items():
            recipe = REFINING_RECIPES.get(key, {})
            refinery_output_value += int(units * recipe.get("base_value_cr", 0))
        miner_queue_ore_tons = refinery_obj.get_total_miner_ore_queued_tons()
        miner_output_value_total = refinery_obj.get_total_miner_output_value()

    my_ore_queued = None
    my_refined_output = None
    my_refined_output_value = None
    my_haulers = None

    if char and refinery_obj:
        owner_id = str(char.id)
        my_ore_queued = refinery_obj.get_miner_ore_queued_tons(owner_id)
        my_refined_output = refinery_obj.get_miner_output(owner_id)
        my_refined_output_value = refinery_obj.get_miner_output_value(owner_id)

        haulers = []
        for entry in (char.db.owned_vehicles or []):
            h = entry if hasattr(entry, "key") else None
            if h and h.tags.has("autonomous_hauler", category="mining"):
                haulers.append({
                    "id": h.id,
                    "key": h.key,
                    "deliveryMode": "ore_receiving_bay",
                })
        my_haulers = haulers

    return {
        "venueId": venue_id_for_object(char) if char else None,
        "plantName": room.key,
        "rawStorageUsed": raw_used,
        "rawStorageCapacity": raw_cap,
        "refineryInputTons": refinery_input_tons,
        "refineryOutputValue": refinery_output_value,
        "minerQueueOreTons": miner_queue_ore_tons,
        "minerOutputValueTotal": miner_output_value_total,
        "processingFeeRate": PROCESSING_FEE_RATE,
        "rawSaleFeeRate": RAW_SALE_FEE_RATE,
        "rawAskPremiumRate": float(COMMODITY_ASK_OVER_BID) - 1.0,
        "myOreQueued": my_ore_queued,
        "myRefinedOutput": my_refined_output,
        "myRefinedOutputValue": my_refined_output_value,
        "myHaulers": my_haulers,
    }


def _serialize_market():
    from world.market_snapshot import serialize_resource_market

    return serialize_resource_market()


_KIOSK_HREF = {
    "bank": ("Bank", "/bank"),
    "processing": ("Processing", "/processing"),
    "processing plant": ("Processing", "/processing"),
    "broker": ("Real Estate", "/real-estate"),
    "realty": ("Real Estate", "/real-estate"),
    "real estate": ("Real Estate", "/real-estate"),
    "real estate office": ("Real Estate", "/real-estate"),
    "claims market": ("Claims Market", "/real-estate"),
    "claims-market": ("Claims Market", "/real-estate"),
}


def _serialize_nav(char, resources):
    from world.bootstrap_shops import all_item_shop_specs
    from world.venues import all_venue_ids, get_venue

    hub = hub_for_object(char) if char else _first_object(CORE_HUB_ROOM_KEY)
    vid = venue_id_for_object(char) if char else "nanomega_core"
    vqs = f"?venue={vid}"
    # Walkable exits for the player must come from their *current* room. The hub
    # room key is "NanoMegaPlex Promenade"; shops connect to it via a "promenade"
    # exit, but that exit lives only on the shop room — not on the hub object.
    # Using only hub exits here would hide the Promenade button when inside shops.
    room_for_exits = None
    if char and getattr(char, "location", None):
        room_for_exits = char.location
    elif hub:
        room_for_exits = hub

    all_exits = _room_exits(room_for_exits) if room_for_exits else []

    kiosk_from_exits = []
    exits = []
    for ex in all_exits:
        kl = ex["key"].lower()
        if kl in _KIOSK_HREF:
            label, href = _KIOSK_HREF[kl]
            if href in ("/bank", "/processing", "/real-estate"):
                href = f"{href}{vqs}"
            kiosk_from_exits.append({"key": ex["key"], "label": label, "href": href})
        else:
            exits.append(ex)

    # Services should always expose core utility destinations, independent of
    # current hub exit naming/mapping. Merge with exit-derived rows (prefer exit
    # labels), then emit in a stable order so web-only links (e.g. Economy) appear.
    required_services = [
        {"key": "bank", "label": "Bank", "href": f"/bank{vqs}"},
        {"key": "real-estate", "label": "Real Estate Agency", "href": f"/real-estate{vqs}"},
        {"key": "processing", "label": "Processing Plant", "href": f"/processing{vqs}"},
        {"key": "locator", "label": "Universal Locator", "href": "/locator"},
        {"key": "economy", "label": "Economy", "href": "/economy"},
    ]
    by_href = {k["href"]: k for k in kiosk_from_exits}
    for svc in required_services:
        if svc["href"] not in by_href:
            by_href[svc["href"]] = svc
    required_hrefs = {s["href"] for s in required_services}
    kiosks = [by_href[s["href"]] for s in required_services]
    for k in kiosk_from_exits:
        if k["href"] not in required_hrefs:
            kiosks.append(k)

    shops = [
        {"roomKey": s["room_key"], "label": s["vendor_name"], "venueId": s["venue_id"]}
        for s in all_item_shop_specs()
    ]
    for v in all_venue_ids():
        sy = get_venue(v)["shipyard"]
        shops.append(
            {
                "roomKey": sy["showroom_key"],
                "label": sy["vendor_name"],
                "venueId": v,
            }
        )

    claims_nav = []
    properties_nav = []
    if char:
        from typeclasses.mining import (
            _resource_rarity_tier,
            _volume_tier,
            estimated_site_value_per_cycle_cr,
        )

        for obj in char.contents:
            if getattr(obj, "destination", None):
                continue
            if getattr(obj.db, "is_template", False):
                continue
            if obj.tags.has("mining_claim", category="mining"):
                claim_row = {"label": obj.key, "href": f"/claims/{obj.id}"}
                site = getattr(obj.db, "site_ref", None)
                if site and hasattr(site, "db"):
                    deposit = site.db.deposit or {}
                    comp = deposit.get("composition") or {}
                    richness = float(deposit.get("richness", 0) or 0)
                    base_tons = float(deposit.get("base_output_tons", 0) or 0)
                    volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
                    rarity_tier, rarity_tier_cls = _resource_rarity_tier(comp)
                    claim_row["volumeTier"] = volume_tier
                    claim_row["volumeTierCls"] = volume_tier_cls
                    claim_row["resourceRarityTier"] = rarity_tier
                    claim_row["resourceRarityTierCls"] = rarity_tier_cls
                    claim_row["estimatedValuePerCycle"] = estimated_site_value_per_cycle_cr(site)
                claims_nav.append(claim_row)
            if obj.tags.has("property_claim", category="realty"):
                properties_nav.append({"label": obj.key, "href": f"/properties/{obj.id}"})

    resources_nav = [
        {
            "key": m["key"],
            "label": m["key"],
            "href": f"/claims/{m['id']}",
            "active": m["active"],
            "kind": m.get("kind") or m.get("siteKind"),
        }
        for m in resources
    ]

    return {
        "venueId": vid,
        "hubRoomKey": hub.key if hub else CORE_HUB_ROOM_KEY,
        "exits": exits,
        "kiosks": kiosks,
        "shops": shops,
        "claims": claims_nav,
        "properties": properties_nav,
        "resources": resources_nav,
        "mines": resources_nav,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

_EMPTY_ALERTS = {"critical": [], "warning": [], "info": []}
_EMPTY_MISSIONS = {
    "morality": {"good": 0, "evil": 0, "lawful": 0, "chaotic": 0},
    "opportunities": [],
    "active": [],
    "completed": [],
}
_EMPTY_NAV = {
    "hubRoomKey": "",
    "exits": [],
    "kiosks": [],
    "shops": [],
    "claims": [],
    "properties": [],
    "resources": [],
    "mines": [],
}
_EMPTY_INVENTORY = empty_inventory_payload()


@require_GET
def control_surface_state(request):
    """
    GET /ui/control-surface

    Aggregated read model for the 3-column control surface shell.
    Always returns 200; unauthenticated / no-character cases return sparse
    payloads so the shell degrades gracefully.
    """
    from typeclasses.economy import get_economy
    from typeclasses.system_alerts import get_system_alerts_script

    econ = get_economy(create_missing=True)
    treasury_balance = None
    tbid = treasury_bank_id_for_object(None)
    treasury_balance = econ.get_balance(econ.get_treasury_account(tbid))
    miner_payout_last_cr, miner_payout_total_cr = econ.get_miner_payout_totals_for_web()

    market = _serialize_market()

    clock_payload = {
        "miningDeliveryPeriodSeconds": int(MINING_DELIVERY_PERIOD),
        "floraDeliveryPeriodSeconds": int(FLORA_DELIVERY_PERIOD),
        "serverTimeIso": to_iso(utc_now()) or "",
        "miningSlotStartIso": current_mining_delivery_slot_start_iso(),
        "floraSlotStartIso": current_flora_delivery_slot_start_iso(),
        "miningNextCycleAt": next_mining_delivery_boundary_iso(),
        "floraNextCycleAt": next_flora_delivery_boundary_iso(),
    }

    base_sparse = {
        "schemaVersion": SCHEMA_VERSION,
        "authenticated": False,
        "character": None,
        "credits": None,
        "inventory": _EMPTY_INVENTORY,
        "ships": [],
        "resources": [],
        "mines": [],
        "miningAccrualValuePerCycle": 0,
        "floraAccrualValuePerCycle": 0,
        "productionEstimatedValuePerCycle": 0,
        "productionTotalStoredValue": 0,
        "miningEstimatedValuePerCycle": 0,
        "miningTotalStoredValue": 0,
        "miningPersonalStoredValue": 0,
        "properties": [],
        "propertyReferenceListValueTotalCr": 0,
        "processing": None,
        "market": market,
        "alerts": [],
        "groupedAlerts": _EMPTY_ALERTS,
        "missions": _EMPTY_MISSIONS,
        "nav": _EMPTY_NAV,
        "roomExits": [],
        "treasuryBalance": treasury_balance,
        "message": None,
        "minerPayoutLastCycleCr": miner_payout_last_cr,
        "minerPayoutTotalCr": miner_payout_total_cr,
        **clock_payload,
    }

    if not request.user.is_authenticated:
        return JsonResponse(base_sparse)

    alerts = []
    grouped_alerts = _EMPTY_ALERTS
    script = get_system_alerts_script(create_missing=True)
    if script:
        raw_alerts = script.get_visible_for_account(request.user.id, limit=200)
        alerts = [dict(a) for a in raw_alerts]
        grouped_alerts = _group_alerts(alerts)

    char, msg = _resolve_character_for_web(request.user)
    if char is None:
        playable = _playable_characters(request.user)
        picker = [{"id": c.id, "key": c.key} for c in playable]
        return JsonResponse({
            **base_sparse,
            "authenticated": True,
            "alerts": alerts,
            "groupedAlerts": grouped_alerts,
            "message": msg,
            "playableCharacters": picker,
        })

    credits = econ.get_character_balance(char)

    tbid = treasury_bank_id_for_object(char)
    treasury_balance = econ.get_balance(econ.get_treasury_account(tbid))

    char.missions.sync_global_seeds()
    if char.location:
        char.missions.sync_room(char.location)
    missions = char.missions.serialize_for_web()

    character_block = _serialize_character_block(char, credits)
    inventory = _serialize_inventory(char)
    ships = _serialize_ships(char)
    resources, mining_value_per_cycle, mining_total_stored = _serialize_resources(char)
    mining_accrual_cycle = sum(
        int(r.get("accrualValuePerCycle") or 0)
        for r in resources
        if r.get("siteKind") != "flora"
    )
    flora_accrual_cycle = sum(
        int(r.get("accrualValuePerCycle") or 0)
        for r in resources
        if r.get("siteKind") == "flora"
    )
    mining_personal_stored = _personal_plant_ore_stored_value_cr(char)
    properties, property_ref_total = _dashboard_property_portfolio(char)
    processing = _serialize_processing_summary(char)
    nav = _serialize_nav(char, resources)
    room_exits = _room_exits(char.location) if getattr(char, "location", None) else []

    return JsonResponse({
        "schemaVersion": SCHEMA_VERSION,
        "authenticated": True,
        "character": character_block,
        "credits": credits,
        "inventory": inventory,
        "ships": ships,
        "resources": resources,
        "mines": resources,
        "miningAccrualValuePerCycle": mining_accrual_cycle,
        "floraAccrualValuePerCycle": flora_accrual_cycle,
        "productionEstimatedValuePerCycle": mining_value_per_cycle,
        "productionTotalStoredValue": mining_total_stored,
        "miningEstimatedValuePerCycle": mining_value_per_cycle,
        "miningTotalStoredValue": mining_total_stored,
        "miningPersonalStoredValue": mining_personal_stored,
        "properties": properties,
        "propertyReferenceListValueTotalCr": property_ref_total,
        "processing": processing,
        "market": market,
        "alerts": alerts,
        "groupedAlerts": grouped_alerts,
        "missions": missions,
        "nav": nav,
        "roomExits": room_exits,
        "treasuryBalance": treasury_balance,
        "message": None,
        "minerPayoutLastCycleCr": miner_payout_last_cr,
        "minerPayoutTotalCr": miner_payout_total_cr,
        **clock_payload,
    })
