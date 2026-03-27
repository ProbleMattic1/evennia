"""
Aggregated control-surface read model for the frontend 3-column UI.

Single endpoint: GET /ui/control-surface
Returns a ControlSurfaceState JSON payload containing every piece of information
the 3-column shell needs — character stats, alerts, missions, inventory, ships,
mines, properties, processing summary, live market rates, and dynamic nav.

All data is assembled from existing private helpers in views.py so there is no
logic duplication; this file is a pure composition layer.
"""

import json
from collections import defaultdict

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from evennia import search_object

from world.inventory_taxonomy import empty_inventory_payload, serialize_inventory_by_bucket

from .views import (
    BANK_ROOM_KEY,
    PROCESSING_PLANT_ROOM_KEY,
    _dashboard_inventory_item_for_obj,
    _dashboard_property_portfolio,
    _first_object,
    _group_alerts,
    _playable_characters,
    _resolve_character_for_web,
    _room_actions,
    _room_exits,
)

SCHEMA_VERSION = 1


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


def _serialize_mines(char):
    from typeclasses.mining import (
        MODE_OUTPUT_MODIFIERS,
        POWER_OUTPUT_MODIFIERS,
        WEAR_OUTPUT_PENALTY,
        _resource_rarity_tier,
        _volume_tier,
        get_commodity_bid,
    )

    mines = []
    mining_value_per_cycle = 0.0
    mining_total_stored = 0.0

    for site in char.db.owned_sites or []:
        if not site or not getattr(site, "db", None):
            continue
        installed = [r for r in (site.db.rigs or []) if r]
        operational = [r for r in installed if r.db.is_operational]
        active_rig = min(operational, key=lambda r: r.db.wear) if operational else None

        storage = site.db.linked_storage
        deposit = site.db.deposit or {}
        richness = float(deposit.get("richness", 0))
        raw_comp = deposit.get("composition") or {}
        comp = {str(k): float(v) for k, v in raw_comp.items()}

        raw_inv = storage.db.inventory if storage else {}
        inv = {str(k): float(v) for k, v in raw_inv.items()}
        cap = float(storage.db.capacity_tons) if storage else 500.0
        used = sum(inv.values()) if inv else 0

        sloc = site.location
        for k, tons in inv.items():
            mining_total_stored += tons * get_commodity_bid(k, location=sloc)

        base_tons = float(deposit.get("base_output_tons", 0))
        estimated_value = 0.0
        estimated_tons = 0.0

        if site.is_active and active_rig:
            rig_rating = float(active_rig.db.rig_rating)
            wear_mod = 1.0 - (float(active_rig.db.wear) * WEAR_OUTPUT_PENALTY)
            total = (
                base_tons
                * richness
                * rig_rating
                * MODE_OUTPUT_MODIFIERS[active_rig.db.mode]
                * POWER_OUTPUT_MODIFIERS[active_rig.db.power_level]
                * wear_mod
            )
            estimated_tons = total
            for k, frac in raw_comp.items():
                val = total * float(frac) * get_commodity_bid(k, location=sloc)
                estimated_value += val
                mining_value_per_cycle += val
        else:
            estimated_tons = base_tons * richness
            for k, frac in raw_comp.items():
                estimated_value += estimated_tons * float(frac) * get_commodity_bid(k, location=sloc)

        volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
        rarity_tier, rarity_tier_cls = _resource_rarity_tier(raw_comp)

        mines.append({
            "id": site.id,
            "key": site.key,
            "location": sloc.key if sloc else None,
            "active": site.is_active,
            "richness": richness,
            "volumeTier": volume_tier,
            "volumeTierCls": volume_tier_cls,
            "resourceRarityTier": rarity_tier,
            "resourceRarityTierCls": rarity_tier_cls,
            "baseOutputTons": base_tons,
            "estimatedOutputTons": round(estimated_tons, 1),
            "estimatedValuePerCycle": int(round(estimated_value)),
            "composition": comp,
            "nextCycleAt": site.db.next_cycle_at,
            "rig": active_rig.key if active_rig else None,
            "rigWear": int(active_rig.db.wear * 100) if active_rig else None,
            "rigOperational": active_rig.db.is_operational if active_rig else False,
            "storageUsed": round(used, 1),
            "storageCapacity": cap,
            "inventory": inv,
            "licenseLevel": int(site.db.license_level),
            "taxRate": float(site.db.tax_rate),
            "hazardLevel": float(site.db.hazard_level),
        })

    return mines, int(round(mining_value_per_cycle)), int(round(mining_total_stored))


def _serialize_processing_summary(char):
    from typeclasses.mining import COMMODITY_ASK_OVER_BID
    from typeclasses.refining import PROCESSING_FEE_RATE, RAW_SALE_FEE_RATE, REFINING_RECIPES

    room = _first_object(PROCESSING_PLANT_ROOM_KEY)
    if not room:
        return None

    receiving_bay = None
    refinery_obj = None
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining") and not receiving_bay:
            kl = obj.key.lower()
            if "receiving" in kl or "bay" in kl:
                receiving_bay = obj
        if obj.tags.has("refinery", category="mining") and not refinery_obj:
            refinery_obj = obj

    raw_used = 0.0
    raw_cap = 0.0
    if receiving_bay:
        raw_used = receiving_bay.total_mass() if hasattr(receiving_bay, "total_mass") else 0.0
        raw_cap = float(getattr(receiving_bay.db, "capacity_tons", 0) or 0)

    refinery_input_tons = 0.0
    refinery_output_value = 0
    if refinery_obj:
        in_inv = refinery_obj.db.input_inventory or {}
        refinery_input_tons = round(sum(float(v) for v in in_inv.values()), 2)
        out_inv = refinery_obj.db.output_inventory or {}
        for key, units in out_inv.items():
            recipe = REFINING_RECIPES.get(key, {})
            refinery_output_value += int(units * recipe.get("base_value_cr", 0))

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
                    "deliveryMode": h.db.hauler_delivery_mode or "sell",
                })
        my_haulers = haulers

    return {
        "plantName": PROCESSING_PLANT_ROOM_KEY,
        "rawStorageUsed": raw_used,
        "rawStorageCapacity": raw_cap,
        "refineryInputTons": refinery_input_tons,
        "refineryOutputValue": refinery_output_value,
        "processingFeeRate": PROCESSING_FEE_RATE,
        "rawSaleFeeRate": RAW_SALE_FEE_RATE,
        "rawAskPremiumRate": float(COMMODITY_ASK_OVER_BID) - 1.0,
        "myOreQueued": my_ore_queued,
        "myRefinedOutput": my_refined_output,
        "myRefinedOutputValue": my_refined_output_value,
        "myHaulers": my_haulers,
    }


def _serialize_market():
    from typeclasses.mining import RESOURCE_CATALOG, get_commodity_ask, get_commodity_bid

    commodities = []
    for rk, info in RESOURCE_CATALOG.items():
        commodities.append({
            "key": rk,
            "name": info["name"],
            "category": info["category"],
            "basePriceCrPerTon": info["base_price_cr_per_ton"],
            "sellPriceCrPerTon": get_commodity_bid(rk),
            "buyPriceCrPerTon": get_commodity_ask(rk),
            "desc": info["desc"],
        })
    return commodities


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


def _serialize_nav(char, mines):
    from world.bootstrap_hub import HUB_ROOM_KEY
    from world.bootstrap_shops import SHOPS

    hub = _first_object(HUB_ROOM_KEY)
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

    kiosks = []
    exits = []
    for ex in all_exits:
        kl = ex["key"].lower()
        if kl in _KIOSK_HREF:
            label, href = _KIOSK_HREF[kl]
            kiosks.append({"key": ex["key"], "label": label, "href": href})
        else:
            exits.append(ex)

    # Services should always expose core utility destinations, independent of
    # current hub exit naming/mapping.
    required_services = [
        {"key": "bank", "label": "Bank", "href": "/bank"},
        {"key": "processing", "label": "Processing Plant", "href": "/processing"},
        {"key": "real-estate", "label": "Real Estate Agency", "href": "/real-estate"},
    ]
    kiosk_hrefs = {k.get("href") for k in kiosks}
    for service in required_services:
        if service["href"] not in kiosk_hrefs:
            kiosks.append(service)

    shops = [{"roomKey": s["room_key"], "label": s["vendor_name"]} for s in SHOPS]
    shops.append({"roomKey": "Meridian Civil Shipyard", "label": "Shipyard"})

    claims_nav = []
    properties_nav = []
    if char:
        for obj in char.contents:
            if getattr(obj, "destination", None):
                continue
            if getattr(obj.db, "is_template", False):
                continue
            if obj.tags.has("mining_claim", category="mining"):
                claims_nav.append({"label": obj.key, "href": f"/claims/{obj.id}"})
            if obj.tags.has("property_claim", category="realty"):
                properties_nav.append({"label": obj.key, "href": f"/properties/{obj.id}"})

    mines_nav = [
        {"label": m["key"], "href": f"/claims/{m['id']}", "active": m["active"]}
        for m in mines
    ]

    return {
        "hubRoomKey": hub.key if hub else HUB_ROOM_KEY,
        "exits": exits,
        "kiosks": kiosks,
        "shops": shops,
        "claims": claims_nav,
        "properties": properties_nav,
        "mines": mines_nav,
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
    bank_room = _first_object(BANK_ROOM_KEY)
    if bank_room:
        treasury_balance = econ.get_balance("treasury:alpha-prime")

    market = _serialize_market()

    base_sparse = {
        "schemaVersion": SCHEMA_VERSION,
        "authenticated": False,
        "character": None,
        "credits": None,
        "inventory": _EMPTY_INVENTORY,
        "ships": [],
        "mines": [],
        "miningEstimatedValuePerCycle": 0,
        "miningTotalStoredValue": 0,
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

    char.missions.sync_global_seeds()
    if char.location:
        char.missions.sync_room(char.location)
    missions = char.missions.serialize_for_web()

    character_block = _serialize_character_block(char, credits)
    inventory = _serialize_inventory(char)
    ships = _serialize_ships(char)
    mines, mining_value_per_cycle, mining_total_stored = _serialize_mines(char)
    properties, property_ref_total = _dashboard_property_portfolio(char)
    processing = _serialize_processing_summary(char)
    nav = _serialize_nav(char, mines)
    room_exits = _room_exits(char.location) if getattr(char, "location", None) else []

    return JsonResponse({
        "schemaVersion": SCHEMA_VERSION,
        "authenticated": True,
        "character": character_block,
        "credits": credits,
        "inventory": inventory,
        "ships": ships,
        "mines": mines,
        "miningEstimatedValuePerCycle": mining_value_per_cycle,
        "miningTotalStoredValue": mining_total_stored,
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
    })
