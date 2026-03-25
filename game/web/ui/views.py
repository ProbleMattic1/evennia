import json
from collections import defaultdict
from urllib.parse import quote

from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from evennia import search_object
from evennia.utils import utils

from world.bootstrap_hub import HUB_ROOM_KEY

DEFAULT_PLAY_ROOM = HUB_ROOM_KEY


def _is_ship_catalog_vendor(obj):
    if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
        return False
    return getattr(obj.db, "catalog_mode", None) == "ships"


def _is_items_catalog_vendor(obj):
    if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
        return False
    return getattr(obj.db, "catalog_mode", None) != "ships"
BANK_ROOM_KEY = "Alpha Prime Central Reserve"
SHIPYARD_ROOM_KEY = "Meridian Civil Shipyard"
PROCESSING_PLANT_ROOM_KEY = "Aurnom Ore Processing Plant"


def _first_object(key):
    found = search_object(key)
    return found[0] if found else None


def _group_alerts(rows):
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    rows = sorted(
        [dict(r) for r in rows],
        key=lambda r: (
            sev_order.get(str(r.get("severity")), 9),
            str(r.get("createdAt") or ""),
        ),
        reverse=False,
    )
    return {
        "critical": [r for r in rows if r.get("severity") == "critical"],
        "warning": [r for r in rows if r.get("severity") == "warning"],
        "info": [r for r in rows if r.get("severity") == "info"],
    }


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise Http404("Invalid JSON body.")


def _get_vendor_in_room(room, *, ships_mode):
    for obj in room.contents:
        if ships_mode and _is_ship_catalog_vendor(obj):
            return obj
        if not ships_mode and _is_items_catalog_vendor(obj):
            return obj
    return None


def _get_any_vendor_in_room(room):
    """Return items vendor if present, else ships vendor, else None."""
    vendor = _get_vendor_in_room(room, ships_mode=False)
    if vendor:
        return vendor
    return _get_vendor_in_room(room, ships_mode=True)


def _template_stock(vendor):
    return [obj for obj in vendor.get_catalog_items() if getattr(obj.db, "is_template", False)]


def _find_template(stock, *, template_id=None, name=None):
    if template_id:
        for obj in stock:
            catalog = getattr(obj.db, "catalog", None) or {}
            vehicle_id = catalog.get("vehicle_id")
            if str(vehicle_id) == str(template_id) or str(obj.id) == str(template_id):
                return obj

    if name:
        needle = name.strip().lower()
        for obj in stock:
            if needle and needle in obj.key.lower():
                return obj

    return None


def _ship_price(template):
    economy = getattr(template.db, "economy", None) or {}
    return economy.get("total_price_cr") or economy.get("base_price_cr")


def _resolve_character_for_web(account):
    """
    Resolve the active Character for web APIs.
    Returns (character, None) on success, or (None, error_message) on failure.
    """
    try:
        puppets = account.get_all_puppets()
    except Exception:
        puppets = []

    for p in puppets:
        if p and p.is_typeclass("typeclasses.characters.Character", exact=False):
            return p, None

    try:
        playable = list(account.characters)
    except Exception:
        playable = []

    chars = [c for c in playable if c.is_typeclass("typeclasses.characters.Character", exact=False)]
    if len(chars) == 1:
        return chars[0], None
    if len(chars) == 0:
        return None, "No playable character on this account."

    return None, "Multiple characters; connect with a puppet so the active character is known."


def _character_for_web_purchase(account):
    """
    Resolve Character for purchases from the authenticated Account (request.user).
    Uses: (1) any connected puppet that is a Character, else (2) sole playable Character.
    """
    char, msg = _resolve_character_for_web(account)
    if char is not None:
        return char, None
    return None, JsonResponse({"ok": False, "message": msg}, status=400)


def _resolve_exit_destination(ex):
    dest_key = ex.get("destination")
    if not dest_key:
        return None
    found = search_object(dest_key)
    return found[0] if found else None


def _is_mining_site_room(room):
    if not room:
        return False, None
    for obj in room.contents:
        if obj.tags.has("mining_site", category="mining"):
            return True, obj
    return False, None


def _should_show_mining_exit(ex, char):
    dest = _resolve_exit_destination(ex)
    is_site, site = _is_mining_site_room(dest)
    if not is_site:
        return True
    if not getattr(site.db, "is_claimed", False):
        return False
    return site.db.owner == char


def _room_exits(room):
    exits = []
    for obj in room.contents:
        if getattr(obj, "destination", None):
            exits.append(
                {
                    "key": obj.key,
                    "label": obj.key.title(),
                    "command": obj.key,
                    "destination": obj.destination.key if obj.destination else None,
                }
            )
    return exits


def _room_actions(room):
    actions = []

    has_shipyard = any(_is_ship_catalog_vendor(obj) for obj in room.contents)
    has_catalog_shop = any(_is_items_catalog_vendor(obj) for obj in room.contents)
    has_bank = any(
        obj.is_typeclass("typeclasses.bank.CentralBank", exact=False)
        for obj in room.contents
    )

    if has_shipyard:
        actions.append(
            {
                "key": "open_shipyard",
                "label": "Open Shipyard",
                "href": "/shipyard",
            }
        )

    if has_catalog_shop:
        actions.append(
            {
                "key": "open_shop",
                "label": "Open Shop",
                "href": f"/shop?room={quote(room.key)}",
            }
        )

    if has_bank:
        actions.append(
            {
                "key": "open_bank",
                "label": "Open Bank",
                "href": "/bank",
            }
        )

    actions.append(
        {
            "key": "look",
            "label": "Refresh View",
            "href": f"/play?room={room.key}",
        }
    )
    return actions


def _serialize_room(room):
    desc = room.db.desc or "No description available."
    return {
        "roomName": room.key,
        "roomDescription": desc,
        "storyLines": [
            {"id": "title", "text": room.key, "kind": "title"},
            {"id": "desc", "text": desc, "kind": "room"},
        ],
        "exits": _room_exits(room),
        "actions": _room_actions(room),
    }


def _serialize_mining_site(site, char=None):
    """
    Serialize a MiningSite with all available API data.
    Returns a dict suitable for PlayState.site (or None if site is invalid).
    If char is provided and owns the site, adds canUndeploy / canListProperty / canReactivate.
    """
    if not site or not getattr(site, "db", None):
        return None
    if not site.tags.has("mining_site", category="mining"):
        return None

    deposit = site.db.deposit or {}
    richness = float(deposit.get("richness", 0) or 0)
    base_tons = float(deposit.get("base_output_tons", 0) or 0)
    raw_comp = deposit.get("composition") or {}
    comp = {str(k): float(v) for k, v in raw_comp.items()}
    dep_rate = float(deposit.get("depletion_rate", 0.002) or 0.002)
    richness_floor = float(deposit.get("richness_floor", 0.10) or 0.10)

    from typeclasses.mining import _volume_tier, _resource_rarity_tier

    volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
    resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(raw_comp)

    hazard = float(site.db.hazard_level or 0)
    if hazard <= 0.20:
        hazard_label = "Low"
    elif hazard <= 0.50:
        hazard_label = "Medium"
    else:
        hazard_label = "High"

    from typeclasses.mining import (
        get_commodity_bid,
        MODE_OUTPUT_MODIFIERS,
        POWER_OUTPUT_MODIFIERS,
        WEAR_OUTPUT_PENALTY,
    )

    installed_rigs = [r for r in (site.db.rigs or []) if r]
    operational_rigs = [r for r in installed_rigs if r.db.is_operational]
    active_rig = min(operational_rigs, key=lambda r: r.db.wear) if operational_rigs else None

    storage = site.db.linked_storage
    raw_inv = storage.db.inventory if storage else {}
    inv = {str(k): float(v) for k, v in raw_inv.items()}
    cap = float(storage.db.capacity_tons) if storage else 500.0
    used = round(sum(inv.values()), 1) if inv else 0

    estimated_value_per_cycle = 0
    loc = site.location
    if site.is_active and active_rig:
        rig_rating = float(active_rig.db.rig_rating)
        mode = active_rig.db.mode
        power = active_rig.db.power_level
        wear = float(active_rig.db.wear)
        mode_mod = MODE_OUTPUT_MODIFIERS[mode]
        power_mod = POWER_OUTPUT_MODIFIERS[power]
        wear_mod = 1.0 - (wear * WEAR_OUTPUT_PENALTY)
        total_tons = base_tons * richness * rig_rating * mode_mod * power_mod * wear_mod
        for k, frac in raw_comp.items():
            estimated_value_per_cycle += total_tons * float(frac) * get_commodity_bid(k, location=loc)
    else:
        total_tons = base_tons * richness
        for k, frac in raw_comp.items():
            estimated_value_per_cycle += total_tons * float(frac) * get_commodity_bid(k, location=loc)
    estimated_value_per_cycle = int(round(estimated_value_per_cycle))

    families = ", ".join(sorted(raw_comp.keys())) if raw_comp else "unknown"
    owner_key = site.db.owner.key if site.db.owner else None

    rigs_payload = [
        {
            "key": r.key,
            "rating": float(r.db.rig_rating),
            "wear": int(r.db.wear * 100),
            "operational": r.db.is_operational,
            "mode": r.db.mode,
            "powerLevel": r.db.power_level,
            "targetFamily": r.db.target_family,
            "purityCutoff": r.db.purity_cutoff,
            "maintenanceLevel": r.db.maintenance_level,
        }
        for r in installed_rigs
    ]

    payload = {
        "id": site.id,
        "key": site.key,
        "siteKey": site.key,
        "roomKey": site.location.key if site.location else site.key,
        "location": site.location.key if site.location else None,
        "isClaimed": bool(site.db.is_claimed),
        "owner": owner_key,
        "surveyLevel": int(site.db.survey_level),
        "richness": round(richness, 4),
        "volumeTier": volume_tier,
        "volumeTierCls": volume_tier_cls,
        "resourceRarityTier": resource_rarity_tier,
        "resourceRarityTierCls": resource_rarity_tier_cls,
        "baseOutputTons": base_tons,
        "composition": comp,
        "resources": families,
        "depletionRate": dep_rate,
        "richnessFloor": richness_floor,
        "licenseLevel": int(site.db.license_level),
        "taxRate": float(site.db.tax_rate),
        "hazardLevel": round(hazard, 4),
        "hazardLabel": hazard_label,
        "nextCycleAt": site.db.next_cycle_at,
        "lastProcessedAt": site.db.last_processed_at,
        "cycleLog": list(site.db.cycle_log)[-20:],
        "hazardLog": list(site.db.hazard_log)[-10:],
        "estimatedValuePerCycle": estimated_value_per_cycle,
        "active": site.is_active,
        "rigs": rigs_payload,
        "rig": active_rig.key if active_rig else None,
        "rigRating": float(active_rig.db.rig_rating) if active_rig else None,
        "rigWear": int(active_rig.db.wear * 100) if active_rig else None,
        "rigOperational": active_rig.db.is_operational if active_rig else False,
        "rigMode": active_rig.db.mode if active_rig else None,
        "rigPowerLevel": active_rig.db.power_level if active_rig else None,
        "rigTargetFamily": active_rig.db.target_family if active_rig else None,
        "rigPurityCutoff": active_rig.db.purity_cutoff if active_rig else None,
        "rigMaintenanceLevel": active_rig.db.maintenance_level if active_rig else None,
        "storageUsed": used,
        "storageCapacity": cap,
        "inventory": inv,
    }
    mo_active = getattr(site.db, "mine_operation_active", True)
    payload["mineOperationActive"] = mo_active
    if char and getattr(site.db, "is_claimed", False) and site.db.owner == char:
        if getattr(site.db, "package_tier", None):
            if mo_active:
                payload["canUndeploy"] = True
            else:
                payload["canListProperty"] = True
                payload["canReactivate"] = True
    return payload


@csrf_exempt
@require_POST
def claims_market_list_claim(request):
    """List a mining claim deed from inventory. Body: { "claimId": int, "price": number }"""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    char, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    from typeclasses.claim_listings import list_claim_for_sale

    success, msg = list_claim_for_sale(char, body.get("claimId"), body.get("price"))
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({"ok": True, "message": msg, "dashboard": dash_data})


@csrf_exempt
@require_POST
def claims_market_purchase_listed_claim(request):
    """Buy a player-listed claim deed. Body: { "claimId": int }"""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    from typeclasses.claim_listings import buy_listed_claim

    success, msg = buy_listed_claim(buyer, body.get("claimId"))
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({"ok": True, "message": msg, "dashboard": dash_data})


@require_GET
def claim_detail_state(request):
    """Mining claim detail. Query: claimId=int"""
    from evennia import search_object

    raw = request.GET.get("claimId")
    try:
        cid = int(raw)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "Missing or invalid claimId."}, status=400)

    found = search_object("#" + str(cid))
    claim = found[0] if found else None
    if not claim or not claim.tags.has("mining_claim", category="mining"):
        return JsonResponse({"ok": False, "message": "Claim not found."}, status=404)

    char = None
    if request.user.is_authenticated:
        char, _ = _resolve_character_for_web(request.user)

    site = getattr(claim.db, "site_ref", None)
    site_payload = _serialize_mining_site(site, char=char) if site else None

    from typeclasses.claim_listings import claim_is_publicly_listed

    is_owner = bool(char and claim.location == char)
    listed = claim_is_publicly_listed(claim)

    if not is_owner and not listed:
        return JsonResponse({"ok": False, "message": "Not allowed."}, status=403)

    preview = None
    if char:
        preview = _dashboard_inventory_item_for_obj(char, claim)
    elif listed:
        preview = _dashboard_inventory_item_for_obj(claim.location, claim)

    desc = getattr(claim.db, "desc", None) or ""
    allowed = list(getattr(claim.db, "allowed_purposes", None) or ["mining"])

    return JsonResponse(
        {
            "ok": True,
            "claim": {
                "id": claim.id,
                "key": claim.key,
                "description": desc,
                "isJackpot": bool(getattr(claim.db, "is_jackpot", False)),
                "allowedPurposes": allowed,
            },
            "site": site_payload,
            "inventoryPreview": preview,
            "isOwner": is_owner,
            "isListed": listed,
        }
    )


@require_GET
def play_state(request):
    room_key = request.GET.get("room") or DEFAULT_PLAY_ROOM
    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    data = _serialize_room(room)
    is_site, site = _is_mining_site_room(room)
    char = None
    if request.user.is_authenticated:
        char, _ = _resolve_character_for_web(request.user)
    if is_site and site:
        data["site"] = _serialize_mining_site(site, char=char)
        # Insert Processing link before Refresh View for mine rooms
        data["actions"].insert(
            -1,
            {"key": "open_processing", "label": "Processing", "href": "/processing"},
        )
    return JsonResponse(data)


NAV_KIOSKS = {
    "bank": {"label": "Bank", "href": "/bank"},
    "claims market": {"label": "Claims Market", "href": "/claims-market"},
    "processing plant": {"label": "Processing Pl.", "href": "/processing"},
}

SHIPYARD_SHOP_ENTRY = {"roomKey": SHIPYARD_ROOM_KEY, "label": "Shipyard"}


@require_GET
def nav_state(request):
    """
    Hub exits plus catalog shop rooms (including shipyard) plus kiosks (bank).
    Mining site exits are hidden unless the user owns the site.
    """
    from world.bootstrap_shops import SHOPS

    hub = _first_object(HUB_ROOM_KEY)
    if not hub:
        raise Http404(f"Room '{HUB_ROOM_KEY}' was not found.")

    all_exits = _room_exits(hub)
    char = None
    if request.user.is_authenticated:
        char, _ = _resolve_character_for_web(request.user)

    kiosks = []
    exits = []
    mines = []
    for ex in all_exits:
        key_lower = ex["key"].lower()
        if key_lower in NAV_KIOSKS and ex.get("destination"):
            kiosks.append(
                {
                    "key": ex["key"],
                    "label": NAV_KIOSKS[key_lower]["label"],
                    "href": NAV_KIOSKS[key_lower]["href"],
                }
            )
        else:
            dest = _resolve_exit_destination(ex)
            is_site, _ = _is_mining_site_room(dest)
            if is_site:
                if char is None or not _should_show_mining_exit(ex, char):
                    continue
                mines.append(ex)
            else:
                exits.append(ex)

    shops = [{"roomKey": entry["room_key"], "label": entry["vendor_name"]} for entry in SHOPS]
    shops.append(SHIPYARD_SHOP_ENTRY)

    claims_nav = [{"label": "Claims Market", "href": "/claims-market"}]
    if char:
        for obj in char.contents:
            if getattr(obj, "destination", None):
                continue
            if getattr(obj.db, "is_template", False):
                continue
            if obj.tags.has("mining_claim", category="mining"):
                claims_nav.append({"label": obj.key, "href": f"/claims/{obj.id}"})

    return JsonResponse(
        {
            "hubRoomKey": hub.key,
            "exits": exits,
            "mines": mines,
            "claims": claims_nav,
            "shops": shops,
            "kiosks": kiosks,
        }
    )


@require_GET
def bank_state(request):
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    room = _first_object(BANK_ROOM_KEY)

    if not room:
        raise Http404(f"Room '{BANK_ROOM_KEY}' was not found.")

    treasury_balance = econ.get_balance("treasury:alpha-prime")

    return JsonResponse(
        {
            "bankName": "Alpha Prime",
            "roomName": room.key,
            "roomDescription": room.db.desc or "",
            "treasuryBalance": treasury_balance,
            "storyLines": [
                {"id": "bank-title", "text": "Alpha Prime", "kind": "title"},
                {
                    "id": "bank-desc",
                    "text": room.db.desc or "No description available.",
                    "kind": "room",
                },
                {
                    "id": "bank-treasury",
                    "text": f"Treasury balance: {treasury_balance:,} cr",
                    "kind": "system",
                },
            ],
            "exits": _room_exits(room),
        }
    )


@require_GET
def processing_state(request):
    from typeclasses.mining import COMMODITY_ASK_OVER_BID
    from typeclasses.refining import PROCESSING_FEE_RATE, RAW_SALE_FEE_RATE, REFINING_RECIPES

    room = _first_object(PROCESSING_PLANT_ROOM_KEY)
    if not room:
        raise Http404(f"Room '{PROCESSING_PLANT_ROOM_KEY}' was not found.")

    # Locate Ore Receiving Bay and Refinery in the room
    receiving_bay = None
    refinery_obj = None
    for obj in room.contents:
        if obj.tags.has("mining_storage", category="mining") and not receiving_bay:
            key_lower = obj.key.lower()
            if "receiving" in key_lower or "bay" in key_lower:
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

    # Per-miner data for authenticated user
    my_ore_queued = None
    my_refined_output = None
    my_refined_output_value = None
    my_delivery_modes = None

    if request.user.is_authenticated:
        char, _ = _resolve_character_for_web(request.user)
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
            my_delivery_modes = haulers

    story_lines = [
        {"id": "plant-title", "text": room.key, "kind": "title"},
        {"id": "plant-desc", "text": room.db.desc or "No description.", "kind": "room"},
        {
            "id": "plant-storage",
            "text": f"Ore Receiving Bay: {raw_used:.1f} / {raw_cap:.0f} t",
            "kind": "system",
        },
        {
            "id": "plant-refinery",
            "text": (
                f"Shared refinery input: {refinery_input_tons:.1f} t  |  "
                f"Output value: {refinery_output_value:,} cr"
            ),
            "kind": "system",
        },
    ]

    return JsonResponse({
        "plantName": "Aurnom Ore Processing Plant",
        "roomName": room.key,
        "roomDescription": room.db.desc or "",
        "storyLines": story_lines,
        "exits": _room_exits(room),
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
        "myHaulers": my_delivery_modes,
    })


def _dashboard_inventory_item_for_obj(char, obj):
    """Single carried-object payload for dashboard JSON (one physical object)."""
    desc = getattr(obj.db, "desc", None) or ""
    inv_entry = {
        "id": obj.id,
        "key": obj.key,
        "description": desc,
    }
    if obj.tags.has("mining_package", category="mining"):
        inv_entry["isMiningPackage"] = True
        inv_entry["estimatedValue"] = int(getattr(obj.db, "estimated_value", 0) or 0)
    if obj.tags.has("mining_claim", category="mining"):
        inv_entry["isMiningClaim"] = True
        site = getattr(obj.db, "site_ref", None)
        if site and hasattr(site, "db"):
            from typeclasses.mining import get_commodity_bid, _volume_tier, _resource_rarity_tier

            deposit = site.db.deposit or {}
            comp = deposit.get("composition") or {}
            richness = float(deposit.get("richness", 0) or 0)
            base_tons = float(deposit.get("base_output_tons", 0) or 0)
            hazard = float(site.db.hazard_level or 0)
            estimated_value = 0
            total_tons = base_tons * richness
            loc = site.location
            for k, frac in comp.items():
                price = get_commodity_bid(k, location=loc)
                estimated_value += total_tons * float(frac) * price
            volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
            resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(comp)
            inv_entry["claimSpecs"] = {
                "roomKey": site.location.key if site.location else site.key,
                "richness": round(richness, 2),
                "baseOutputTons": base_tons,
                "composition": {str(k): float(v) for k, v in comp.items()},
                "hazardLevel": round(hazard, 2),
                "hazardLabel": "Low" if hazard <= 0.20 else "Medium" if hazard <= 0.50 else "High",
                "estimatedValuePerCycle": int(round(estimated_value)),
                "volumeTier": volume_tier,
                "volumeTierCls": volume_tier_cls,
                "resourceRarityTier": resource_rarity_tier,
                "resourceRarityTierCls": resource_rarity_tier_cls,
            }
    return inv_entry


@require_GET
def dashboard_state(request):
    """
    Character-centric snapshot for the web dashboard: credits, carried items,
    owned ships, plus Alpha Prime treasury (public). Always returns 200 JSON.
    """
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    treasury_balance = None
    bank_room = _first_object(BANK_ROOM_KEY)
    if bank_room:
        treasury_balance = econ.get_balance("treasury:alpha-prime")

    base = {
        "treasuryBalance": treasury_balance,
    }

    empty_alerts = {"critical": [], "warning": [], "info": []}

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                **base,
                "authenticated": False,
                "character": None,
                "credits": None,
                "inventory": [],
                "ships": [],
                "mines": [],
                "miningEstimatedValuePerCycle": 0,
                "miningTotalStoredValue": 0,
                "message": None,
                "alerts": [],
                "groupedAlerts": empty_alerts,
            }
        )

    from typeclasses.system_alerts import get_system_alerts_script

    alerts = []
    grouped_alerts = empty_alerts
    script = get_system_alerts_script(create_missing=True)
    if script:
        raw_alerts = script.get_visible_for_account(request.user.id, limit=200)
        alerts = [dict(a) for a in raw_alerts]
        grouped_alerts = _group_alerts(alerts)

    char, msg = _resolve_character_for_web(request.user)
    if char is None:
        return JsonResponse(
            {
                **base,
                "authenticated": True,
                "character": None,
                "credits": None,
                "inventory": [],
                "ships": [],
                "mines": [],
                "miningEstimatedValuePerCycle": 0,
                "miningTotalStoredValue": 0,
                "message": msg,
                "alerts": alerts,
                "groupedAlerts": grouped_alerts,
            }
        )

    credits = econ.get_character_balance(char)

    claim_inventory = []
    stackable_objs = []
    for obj in char.contents:
        if getattr(obj, "destination", None):
            continue
        if getattr(obj.db, "is_template", False):
            continue
        if obj.tags.has("mining_claim", category="mining"):
            claim_inventory.append(_dashboard_inventory_item_for_obj(char, obj))
        else:
            stackable_objs.append(obj)

    inventory = list(claim_inventory)
    for _numbered_name, _desc, objs in utils.group_objects_by_key_and_desc(stackable_objs, caller=char):
        inv_entry = _dashboard_inventory_item_for_obj(char, objs[0])
        if len(objs) > 1:
            inv_entry["count"] = len(objs)
            inv_entry["stacked"] = True
            inv_entry["ids"] = [o.id for o in objs]
        inventory.append(inv_entry)

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
        is_autonomous = (
            hasattr(obj, "tags") and obj.tags.has("autonomous_hauler", category="mining")
        )
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
        rows = autonomous_by_key[ship_key]
        if len(rows) == 1:
            ships.append(rows[0])
        else:
            ships.append(
                {
                    "id": rows[0]["id"],
                    "key": ship_key,
                    "location": None,
                    "pilot": rows[0]["pilot"],
                    "state": rows[0]["state"],
                    "summary": rows[0]["summary"],
                    "is_autonomous": True,
                    "count": len(rows),
                    "stacked": True,
                    "ids": [r["id"] for r in rows],
                    "locations": [r["location"] for r in rows],
                }
            )
    ships.extend(ships_other)

    from typeclasses.mining import (
        get_commodity_bid,
        MODE_OUTPUT_MODIFIERS,
        POWER_OUTPUT_MODIFIERS,
        WEAR_OUTPUT_PENALTY,
    )

    mines = []
    mining_value_per_cycle = 0
    mining_total_stored = 0

    for site in (char.db.owned_sites or []):
        if not site or not getattr(site, "db", None):
            continue
        site_installed_rigs = [r for r in (site.db.rigs or []) if r]
        site_operational_rigs = [r for r in site_installed_rigs if r.db.is_operational]
        site_active_rig = min(site_operational_rigs, key=lambda r: r.db.wear) if site_operational_rigs else None

        storage = site.db.linked_storage
        deposit = site.db.deposit
        richness = float(deposit.get("richness", 0))
        raw_comp = deposit.get("composition") or {}
        comp = {str(k): float(v) for k, v in raw_comp.items()}
        next_cycle = site.db.next_cycle_at

        raw_inv = storage.db.inventory if storage else {}
        inv = {str(k): float(v) for k, v in raw_inv.items()}
        cap = float(storage.db.capacity_tons) if storage else 500.0
        used = sum(inv.values()) if inv else 0

        sloc = site.location
        for k, tons in inv.items():
            price = get_commodity_bid(k, location=sloc)
            mining_total_stored += tons * price

        base_tons = float(deposit.get("base_output_tons", 0))
        estimated_value_per_cycle = 0
        estimated_output_tons = 0
        if site.is_active and site_active_rig:
            rig_rating = float(site_active_rig.db.rig_rating)
            mode = site_active_rig.db.mode
            power = site_active_rig.db.power_level
            wear = float(site_active_rig.db.wear)
            mode_mod = MODE_OUTPUT_MODIFIERS[mode]
            power_mod = POWER_OUTPUT_MODIFIERS[power]
            wear_mod = 1.0 - (wear * WEAR_OUTPUT_PENALTY)
            total_tons = base_tons * richness * rig_rating * mode_mod * power_mod * wear_mod
            estimated_output_tons = total_tons
            for k, frac in raw_comp.items():
                price = get_commodity_bid(k, location=sloc)
                val = total_tons * float(frac) * price
                estimated_value_per_cycle += val
                mining_value_per_cycle += val
        else:
            estimated_output_tons = base_tons * richness
            for k, frac in raw_comp.items():
                price = get_commodity_bid(k, location=sloc)
                estimated_value_per_cycle += estimated_output_tons * float(frac) * price

        from typeclasses.mining import _volume_tier, _resource_rarity_tier

        volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
        resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(raw_comp)

        mines.append({
            "id": site.id,
            "key": site.key,
            "location": site.location.key if site.location else None,
            "active": site.is_active,
            "richness": richness,
            "volumeTier": volume_tier,
            "volumeTierCls": volume_tier_cls,
            "resourceRarityTier": resource_rarity_tier,
            "resourceRarityTierCls": resource_rarity_tier_cls,
            "baseOutputTons": deposit.get("base_output_tons", 0),
            "estimatedOutputTons": round(estimated_output_tons, 1),
            "estimatedValuePerCycle": int(round(estimated_value_per_cycle)),
            "composition": comp,
            "nextCycleAt": next_cycle,
            "rigs": [
                {
                    "key": r.key,
                    "wear": int(r.db.wear * 100),
                    "operational": r.db.is_operational,
                }
                for r in site_installed_rigs
            ],
            "rig": site_active_rig.key if site_active_rig else None,
            "rigWear": int(site_active_rig.db.wear * 100) if site_active_rig else None,
            "rigOperational": site_active_rig.db.is_operational if site_active_rig else False,
            "storageUsed": round(used, 1),
            "storageCapacity": cap,
            "inventory": inv,
            "licenseLevel": int(site.db.license_level),
            "taxRate": float(site.db.tax_rate),
            "hazardLevel": float(site.db.hazard_level),
        })

    room_key = char.location.key if char.location else None
    rpg = char.get_rpg_dashboard_snapshot()

    return JsonResponse(
        {
            **base,
            "authenticated": True,
            "character": {"id": char.id, "key": char.key, "room": room_key, **rpg},
            "credits": credits,
            "inventory": inventory,
            "ships": ships,
            "mines": mines,
            "miningEstimatedValuePerCycle": int(round(mining_value_per_cycle)),
            "miningTotalStoredValue": int(round(mining_total_stored)),
            "message": None,
            "alerts": alerts,
            "groupedAlerts": grouped_alerts,
        }
    )


@csrf_exempt
@require_POST
def dashboard_ack_alert(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    body = _json_body(request)
    alert_id = str(body.get("alertId") or "").strip()
    if not alert_id:
        return JsonResponse({"ok": False, "message": "Missing alertId."}, status=400)

    from typeclasses.system_alerts import get_system_alerts_script

    script = get_system_alerts_script(create_missing=True)
    if not script:
        return JsonResponse({"ok": False, "message": "Alerts script unavailable."}, status=500)

    script.ack_for_account(request.user.id, alert_id)

    dash = dashboard_state(request)
    dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    return JsonResponse({"ok": True, "message": "Alert acknowledged.", "dashboard": dash_data})


@require_GET
def shop_state(request):
    """
    JSON for any CatalogVendor in the given room (items or ships).
    Query: room=<exact room key>, e.g. room=Aurnom%20Tech%20Depot
    """
    room_key = request.GET.get("room")
    if not room_key:
        raise Http404("Missing required query parameter 'room'.")

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    shop = _get_any_vendor_in_room(room)

    if not shop:
        raise Http404("No catalog shop or shipyard kiosk found in this room.")

    data = shop.get_shop_state_for_api(buyer=None)
    return JsonResponse(data)


@csrf_exempt
@require_POST
def shop_inspect(request):
    body = _json_body(request)
    if body.get("buyer") is not None:
        return JsonResponse(
            {"ok": False, "message": "Client-supplied buyer is not allowed."},
            status=400,
        )

    room_key = body.get("room")
    item_id = body.get("itemId") or body.get("shipId")
    item_name = body.get("name")

    if not room_key:
        return JsonResponse({"ok": False, "message": "Missing room."}, status=400)

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    vendor = _get_any_vendor_in_room(room)
    if not vendor:
        raise Http404("No catalog shop or shipyard kiosk found in this room.")

    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=item_id, name=item_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Item or ship not found in catalog."}, status=404)

    if _is_ship_catalog_vendor(vendor):
        summary = template.get_vehicle_summary() if hasattr(template, "get_vehicle_summary") else template.key
        ship_id = (getattr(template.db, "catalog", None) or {}).get("vehicle_id") or template.key
        return JsonResponse(
            {
                "ok": True,
                "message": f"{template.key}\n{template.db.desc or 'No description available.'}\n{summary}",
                "ship": {
                    "id": str(ship_id),
                    "key": template.key,
                    "description": getattr(template.db, "desc", "") or "",
                    "summary": summary,
                    "price": _ship_price(template),
                },
                "state": vendor.get_shop_state_for_api(),
            }
        )

    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    market_type = getattr(vendor.db, "market_type", None) or "normal"
    price = econ.get_final_price(template, buyer=None, location=room, market_type=market_type)
    desc = template.db.desc or ""

    return JsonResponse(
        {
            "ok": True,
            "message": f"{template.key}\n{desc or 'No description available.'}",
            "item": {
                "id": str(template.id),
                "key": template.key,
                "description": desc,
                "summary": desc[:120] + ("…" if len(desc) > 120 else ""),
                "price": price,
            },
            "state": vendor.get_shop_state_for_api(buyer=None),
        }
    )


@require_GET
def resources_state(request):
    """
    Central resource catalog — keys, names, categories, base prices.
    Single source of truth for all resource-consuming UIs (mining, refining, market).
    """
    from typeclasses.mining import RESOURCE_CATALOG

    resources = []
    for key, info in RESOURCE_CATALOG.items():
        resources.append({
            "key": key,
            "name": info["name"],
            "category": info["category"],
            "basePriceCrPerTon": info["base_price_cr_per_ton"],
            "desc": info["desc"],
        })

    return JsonResponse({"resources": resources})


@require_GET
def market_state(request):
    """
    Live commodity prices for all mining resources.
    Applies all EconomyEngine modifiers so the frontend always shows current rates.
    """
    from typeclasses.mining import RESOURCE_CATALOG, get_commodity_ask, get_commodity_bid

    commodities = []
    for resource_key, info in RESOURCE_CATALOG.items():
        sell_price = get_commodity_bid(resource_key)
        buy_price = get_commodity_ask(resource_key)
        commodities.append(
            {
                "key":               resource_key,
                "name":              info["name"],
                "category":          info["category"],
                "basePriceCrPerTon": info["base_price_cr_per_ton"],
                "sellPriceCrPerTon": sell_price,
                "buyPriceCrPerTon":  buy_price,
                "desc":              info["desc"],
            }
        )

    return JsonResponse({"commodities": commodities})


@require_GET
def claims_market_state(request):
    """
    List mining sites open on the claims market (unclaimed, no outstanding deed).
    Public — no auth required.
    """
    from evennia import search_tag

    from typeclasses.claim_market import (
        _existing_deed_for_site,
        _get_property_listings_script,
        claims_market_row_extras,
        site_is_claims_market_listable,
    )
    from typeclasses.mining import _resource_rarity_tier, _volume_tier

    sites = search_tag("mining_site", category="mining")
    listable = [s for s in sites if site_is_claims_market_listable(s)]

    claims = []
    for site in listable:
        room = site.location
        room_key = room.key if room else "unknown"
        deposit = site.db.deposit or {}
        comp = deposit.get("composition", {})
        families = ", ".join(comp.keys()) if comp else "unknown"
        richness = float(deposit.get("richness", 0.0))
        hazard = float(site.db.hazard_level or 0.0)
        base_tons = float(deposit.get("base_output_tons", 0) or 0)

        volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
        resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(comp)
        if hazard <= 0.20:
            hazard_label = "Low"
        elif hazard <= 0.50:
            hazard_label = "Medium"
        else:
            hazard_label = "High"
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
        }
        row.update(claims_market_row_extras(site))
        row["playerListing"] = False
        claims.append(row)

    script = _get_property_listings_script()
    if script:
        for ent in list(script.db.listings or []):
            sid = ent.get("site_id")
            site = next((s for s in sites if s.id == sid), None)
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
            families = ", ".join(comp.keys()) if comp else "unknown"
            richness = float(deposit.get("richness", 0.0))
            hazard = float(site.db.hazard_level or 0.0)
            base_tons = float(deposit.get("base_output_tons", 0) or 0)
            volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
            resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(comp)
            if hazard <= 0.20:
                hazard_label = "Low"
            elif hazard <= 0.50:
                hazard_label = "Medium"
            else:
                hazard_label = "High"
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
                    "hazardLabel": hazard_label,
                    "baseOutputTons": base_tons,
                    "listingPriceCr": int(ent.get("price", 0) or 0),
                    "purchasable": True,
                    "playerListing": True,
                    "sellerKey": seller_key,
                }
            )

    from typeclasses.claim_listings import get_claim_listings_rows

    for row in get_claim_listings_rows():
        claims.append(row)

    from evennia import search_script

    disc = search_script("site_discovery_engine")
    next_discovery_at = None
    if disc:
        eta = disc[0].db.next_discovery_at
        if eta is not None:
            next_discovery_at = eta.isoformat()

    return JsonResponse({"claims": claims, "nextDiscoveryAt": next_discovery_at})


@csrf_exempt
@require_POST
def claims_market_purchase(request):
    """
    Buy a claim deed for a listed unclaimed site.
    Body: { "siteKey": "<MiningSite.key>" }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    site_key = body.get("siteKey")
    if not site_key:
        return JsonResponse({"ok": False, "message": "Missing siteKey."}, status=400)

    from typeclasses.claim_market import (
        get_property_listing_for_site_id,
        purchase_property_listing,
        purchase_site_claim_deed,
        _resolve_mining_site_by_key,
    )
    from typeclasses.economy import get_economy

    site = _resolve_mining_site_by_key(site_key)
    if site and get_property_listing_for_site_id(site.id):
        success, msg, claim = purchase_property_listing(buyer, site)
    else:
        success, msg, claim = purchase_site_claim_deed(buyer, site_key)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    econ = get_economy(create_missing=True)
    buyer_credits = econ.get_character_balance(buyer)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}

    return JsonResponse(
        {
            "ok": True,
            "message": msg,
            "claim": {"id": claim.id, "key": claim.key},
            "buyerCredits": buyer_credits,
            "dashboard": dash_data,
        }
    )


@csrf_exempt
@require_POST
def shop_buy(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    body = _json_body(request)
    if body.get("buyer") is not None:
        return JsonResponse(
            {"ok": False, "message": "Client-supplied buyer is not allowed."},
            status=400,
        )

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    room_key = body.get("room")
    item_id = body.get("itemId") or body.get("shipId")
    item_name = body.get("name")

    if not room_key:
        return JsonResponse({"ok": False, "message": "Missing room."}, status=400)

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    vendor = _get_any_vendor_in_room(room)
    if not vendor:
        raise Http404("No catalog shop or shipyard kiosk found in this room.")

    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=item_id, name=item_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Item or ship not found in catalog."}, status=404)

    if _is_ship_catalog_vendor(vendor):
        price = _ship_price(template)
        if price is None:
            return JsonResponse({"ok": False, "message": "Ship has no listed price."}, status=400)

        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        credits = econ.get_character_balance(buyer)
        if credits < price:
            return JsonResponse(
                {
                    "ok": False,
                    "message": f"{template.key} costs {price:,} cr. Buyer has {credits:,} cr.",
                    "needed": price - credits,
                },
                status=400,
            )

        delivery = vendor.db.delivery_room or getattr(room.db, "ship_delivery_room", None)
        if not delivery:
            return JsonResponse({"ok": False, "message": "Shipyard delivery room is not configured."}, status=500)

        new_ship = template.copy(new_key=template.key)
        new_ship.db.is_template = False
        if new_ship.tags.has("for_sale", category="shop_stock"):
            new_ship.tags.remove("for_sale", category="shop_stock")
        vid = vendor.db.vendor_id
        if vid and new_ship.tags.has(vid, category="vendor"):
            new_ship.tags.remove(vid, category="vendor")
        new_ship.db.owner = buyer
        new_ship.db.allowed_boarders = [buyer]
        new_ship.db.state = "docked"
        new_ship.db.fuel = template.db.max_fuel or 100
        new_ship.db.max_fuel = new_ship.db.fuel
        new_ship.db.desc = f"Your {template.key}, ready for travel."
        new_ship.move_to(delivery, quiet=True)

        vendor_amount, tax_amount = vendor.record_sale(
            buyer,
            price,
            tx_type="ship_purchase",
            memo=f"{buyer.key} purchased a ship from {vendor.key}",
            withdraw_memo=f"Ship purchase at {vendor.key}",
        )

        owned = buyer.db.owned_vehicles or []
        if new_ship not in owned:
            owned.append(new_ship)
            buyer.db.owned_vehicles = owned

        return JsonResponse(
            {
                "ok": True,
                "message": (
                    f"Purchased {template.key} for {price:,} cr. "
                    f"Delivered to {delivery.key}. Remaining balance: {buyer.db.credits:,} cr."
                ),
                "vendorAmount": vendor_amount,
                "taxAmount": tax_amount,
                "buyerCredits": buyer.db.credits,
                "state": vendor.get_shop_state_for_api(buyer=buyer),
            }
        )

    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    market_type = getattr(vendor.db, "market_type", None) or "normal"
    price = econ.get_final_price(template, buyer=buyer, location=room, market_type=market_type)
    if price <= 0:
        return JsonResponse({"ok": False, "message": "Item has no valid price."}, status=400)

    credits = econ.get_character_balance(buyer)
    if credits < price:
        return JsonResponse(
            {
                "ok": False,
                "message": f"{template.key} costs {price:,} cr. Buyer has {credits:,} cr.",
                "needed": price - credits,
            },
            status=400,
        )

    if getattr(template.db, "grants_random_claim_only", False):
        vendor_amount, tax_amount = vendor.record_sale(
            buyer,
            price,
            tx_type="catalog_purchase",
            memo=f"{buyer.key} bought {template.key} from {vendor.key}",
        )
        message = (
            f"Purchased {template.key} for {price:,} cr. "
            f"Remaining balance: {buyer.db.credits:,} cr."
        )
        from typeclasses.claim_utils import grant_random_claim_on_purchase

        claim, jackpot = grant_random_claim_on_purchase(buyer)
        if claim:
            if jackpot:
                message += " ★ JACKPOT! You received an Elite Claim! ★"
            else:
                message += f" Random claim: {claim.key}."
        return JsonResponse(
            {
                "ok": True,
                "message": message,
                "vendorAmount": vendor_amount,
                "taxAmount": tax_amount,
                "buyerCredits": buyer.db.credits,
                "state": vendor.get_shop_state_for_api(buyer=buyer),
            }
        )

    new_item = template.copy(new_key=template.key)
    new_item.db.is_template = False
    if new_item.tags.has("for_sale", category="shop_stock"):
        new_item.tags.remove("for_sale", category="shop_stock")
    vid = vendor.db.vendor_id
    if vid and new_item.tags.has(vid, category="vendor"):
        new_item.tags.remove(vid, category="vendor")
    new_item.db.owner = buyer
    new_item.locks.add("get:true();drop:true();give:true()")
    if getattr(template.db, "is_sale_package", False):
        new_item.db.package_tier = getattr(template.db, "package_tier", None) or template.key
        new_item.tags.add("mining_package", category="mining")
    new_item.move_to(buyer, quiet=True)

    vendor_amount, tax_amount = vendor.record_sale(
        buyer,
        price,
        tx_type="catalog_purchase",
        memo=f"{buyer.key} bought {template.key} from {vendor.key}",
    )

    message = f"Purchased {new_item.key} for {price:,} cr. Remaining balance: {buyer.db.credits:,} cr."
    if getattr(template.db, "is_sale_package", False) and getattr(
        template.db, "includes_random_claim", True
    ):
        from typeclasses.claim_utils import grant_random_claim_on_purchase

        claim, jackpot = grant_random_claim_on_purchase(buyer)
        if claim:
            if jackpot:
                message += " ★ JACKPOT! You received an Elite Claim! ★"
            else:
                message += f" Random claim: {claim.key}."

    return JsonResponse(
        {
            "ok": True,
            "message": message,
            "vendorAmount": vendor_amount,
            "taxAmount": tax_amount,
            "buyerCredits": buyer.db.credits,
            "state": vendor.get_shop_state_for_api(buyer=buyer),
        }
    )


# ---------------------------------------------------------------------------
# Mine deploy / undeploy API
# ---------------------------------------------------------------------------


@require_GET
def mine_claims(request):
    """
    List mining sites open for listing (unclaimed and no outstanding claim deed).
    Query: none. Returns JSON with claims array.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    from evennia import search_tag

    from typeclasses.claim_market import site_is_claims_market_listable
    from typeclasses.mining import _volume_tier, _resource_rarity_tier

    sites = search_tag("mining_site", category="mining")
    listable = [s for s in sites if site_is_claims_market_listable(s)]

    claims = []
    for site in listable:
        room = site.location
        room_name = room.key if room else "unknown"
        deposit = site.db.deposit or {}
        comp = deposit.get("composition", {})
        families = ", ".join(comp.keys()) if comp else "unknown"
        richness = float(deposit.get("richness", 0.0))
        base_tons = float(deposit.get("base_output_tons", 0) or 0)
        hazard = float(site.db.hazard_level or 0.0)
        volume_tier, volume_tier_cls = _volume_tier(richness, base_tons)
        resource_rarity_tier, resource_rarity_tier_cls = _resource_rarity_tier(comp)
        claims.append({
            "siteKey": site.key,
            "roomKey": room_name,
            "resources": families,
            "richness": richness,
            "volumeTier": volume_tier,
            "volumeTierCls": volume_tier_cls,
            "resourceRarityTier": resource_rarity_tier,
            "resourceRarityTierCls": resource_rarity_tier_cls,
            "hazardLevel": hazard,
        })

    return JsonResponse({"ok": True, "claims": claims})


@csrf_exempt
@require_POST
def mine_deploy(request):
    """
    Deploy a mining package from inventory at a claim.
    Body: { "packageId": <int>, "claimId": <int> }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    package_id = body.get("packageId")
    claim_id = body.get("claimId")

    if not package_id:
        return JsonResponse({"ok": False, "message": "Missing packageId."}, status=400)
    if not claim_id:
        return JsonResponse({"ok": False, "message": "Missing claimId."}, status=400)

    try:
        pid = int(package_id)
        cid = int(claim_id)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "Invalid packageId or claimId."}, status=400)

    package = None
    claim = None
    for obj in buyer.contents:
        if obj.id == pid and obj.tags.has("mining_package", category="mining"):
            package = obj
        if obj.id == cid and obj.tags.has("mining_claim", category="mining"):
            claim = obj
    if not package:
        return JsonResponse({"ok": False, "message": "Package not found."}, status=404)
    if not claim:
        return JsonResponse({"ok": False, "message": "Claim not found."}, status=404)

    from typeclasses.packages import deploy_package_from_inventory

    success, msg = deploy_package_from_inventory(buyer, package, claim)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({
        "ok": True,
        "message": msg,
        "dashboard": dash_data,
    })


@csrf_exempt
@require_POST
def mine_undeploy(request):
    """
    Undeploy an owned mine; returns a fresh package to inventory.
    Body: { "siteKey": "<room or site name>" } or { "siteId": <int> }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    site_key = (body.get("siteKey") or "").strip()
    site_id = body.get("siteId")

    site = None
    if site_id is not None:
        try:
            sid = int(site_id)
        except (TypeError, ValueError):
            pass
        else:
            from evennia import search_tag
            for s in search_tag("mining_site", category="mining"):
                if s.id == sid and getattr(s.db, "is_claimed", False) and s.db.owner == buyer:
                    site = s
                    break
    if site is None and site_key:
        from evennia import search_tag
        sites = search_tag("mining_site", category="mining")
        q = site_key.lower()
        for s in sites:
            if not getattr(s.db, "is_claimed", False) or s.db.owner != buyer:
                continue  # skip unclaimed or not owned by buyer
            if q in (s.key or "").lower() or (s.location and q in (s.location.key or "").lower()):
                site = s
                break

    if not site:
        return JsonResponse({"ok": False, "message": "Mine not found or you do not own it."}, status=404)

    from typeclasses.packages import undeploy_mine_to_package

    success, msg, returned = undeploy_mine_to_package(buyer, site)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({
        "ok": True,
        "message": msg,
        "dashboard": dash_data,
        "returnedEquipment": returned or {},
    })


@csrf_exempt
@require_POST
def mine_reactivate(request):
    """
    Reactivate an idle owned mine. Body: { "siteId": int, "packageId"?: int }
    If packageId is set, that package is consumed; otherwise inventory gear is used.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    site_id = body.get("siteId")
    package_id = body.get("packageId")

    if site_id is None:
        return JsonResponse({"ok": False, "message": "Missing siteId."}, status=400)

    try:
        sid = int(site_id)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "Invalid siteId."}, status=400)

    from evennia import search_tag

    site = None
    for s in search_tag("mining_site", category="mining"):
        if s.id == sid and getattr(s.db, "is_claimed", False) and s.db.owner == buyer:
            site = s
            break
    if not site:
        return JsonResponse({"ok": False, "message": "Mine not found or you do not own it."}, status=404)

    from typeclasses.packages import reactivate_mine_from_package, reactivate_mine_inventory_only

    if package_id is not None:
        try:
            pid = int(package_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "Invalid packageId."}, status=400)
        package = None
        for obj in buyer.contents:
            if obj.id == pid and obj.tags.has("mining_package", category="mining"):
                package = obj
                break
        if not package:
            return JsonResponse({"ok": False, "message": "Package not found."}, status=404)
        success, msg = reactivate_mine_from_package(buyer, package, site)
    else:
        success, msg = reactivate_mine_inventory_only(buyer, site)

    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({"ok": True, "message": msg, "dashboard": dash_data})


@csrf_exempt
@require_POST
def claims_market_list_property(request):
    """List an idle owned mining property for sale. Body: { "siteId": int, "price": number }"""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    site_id = body.get("siteId")
    price = body.get("price")
    if site_id is None:
        return JsonResponse({"ok": False, "message": "Missing siteId."}, status=400)

    from typeclasses.claim_market import list_property_for_sale

    success, msg = list_property_for_sale(buyer, site_id, price)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({"ok": True, "message": msg, "dashboard": dash_data})


@csrf_exempt
@require_POST
def package_list_for_sale(request):
    """
    List a mining package for sale. Body: { "packageId": int, "price": int }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    package_id = body.get("packageId")
    price = body.get("price")

    from typeclasses.packages import list_package_for_sale

    success, msg = list_package_for_sale(buyer, package_id, price)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({
        "ok": True,
        "message": msg,
        "dashboard": dash_data,
    })


@require_GET
def package_listings_state(request):
    """Return all active package listings for sale."""
    from typeclasses.packages import get_package_listings

    listings = get_package_listings()
    return JsonResponse({"listings": listings})


@csrf_exempt
@require_POST
def package_buy_listed(request):
    """
    Buy a listed mining package. Body: { "packageId": int }
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    buyer, err = _character_for_web_purchase(request.user)
    if err is not None:
        return err

    body = _json_body(request)
    package_id = body.get("packageId")

    from typeclasses.packages import buy_listed_package

    success, msg = buy_listed_package(buyer, package_id)
    if not success:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    try:
        dash = dashboard_state(request)
        dash_data = json.loads(dash.content.decode("utf-8")) if hasattr(dash, "content") else {}
    except Exception:
        dash_data = {}
    return JsonResponse({
        "ok": True,
        "message": msg,
        "dashboard": dash_data,
    })
