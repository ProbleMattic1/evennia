import json
from urllib.parse import quote

from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from evennia import search_object

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


def _first_object(key):
    found = search_object(key)
    return found[0] if found else None


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


@require_GET
def play_state(request):
    room_key = request.GET.get("room") or DEFAULT_PLAY_ROOM
    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    return JsonResponse(_serialize_room(room))


@require_GET
def nav_state(request):
    """
    Hub exits plus catalog shop rooms for persistent web navigation.
    Shop list is sourced from world.bootstrap_shops.SHOPS (single source of truth).
    """
    from world.bootstrap_shops import SHOPS

    hub = _first_object(HUB_ROOM_KEY)
    if not hub:
        raise Http404(f"Room '{HUB_ROOM_KEY}' was not found.")

    shops = [{"roomKey": entry["room_key"], "label": entry["vendor_name"]} for entry in SHOPS]

    return JsonResponse(
        {
            "hubRoomKey": hub.key,
            "exits": _room_exits(hub),
            "shops": shops,
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

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                **base,
                "authenticated": False,
                "character": None,
                "credits": None,
                "inventory": [],
                "ships": [],
                "message": None,
            }
        )

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
                "message": msg,
            }
        )

    credits = econ.get_character_balance(char)

    inventory = []
    for obj in char.contents:
        if getattr(obj, "destination", None):
            continue
        if getattr(obj.db, "is_template", False):
            continue
        desc = getattr(obj.db, "desc", None) or ""
        if len(desc) > 500:
            desc = desc[:500] + "…"
        inventory.append(
            {
                "id": obj.id,
                "key": obj.key,
                "description": desc,
            }
        )

    ships = []
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
        ships.append(
            {
                "id": obj.id,
                "key": obj.key,
                "location": loc,
                "pilot": pilot_key,
                "state": getattr(obj.db, "state", None),
                "summary": summary,
            }
        )

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
            "message": None,
        }
    )


@require_GET
def shipyard_state(request):
    room = _first_object(SHIPYARD_ROOM_KEY)
    if not room:
        raise Http404(f"Room '{SHIPYARD_ROOM_KEY}' was not found.")

    shop = _get_vendor_in_room(room, ships_mode=True)

    if not shop:
        raise Http404("Shipyard shop not found in room.")

    data = shop.get_shop_state_for_api()
    return JsonResponse(data)


@require_GET
def shop_state(request):
    """
    JSON for a general CatalogVendor in the given room.
    Query: room=<exact room key>, e.g. room=Aurnom%20Tech%20Depot
    """
    room_key = request.GET.get("room")
    if not room_key:
        raise Http404("Missing required query parameter 'room'.")

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    shop = _get_vendor_in_room(room, ships_mode=False)

    if not shop:
        raise Http404("No catalog shop kiosk found in this room.")

    data = shop.get_shop_state_for_api(buyer=None)
    return JsonResponse(data)


@csrf_exempt
@require_POST
def shipyard_inspect(request):
    body = _json_body(request)
    ship_id = body.get("shipId")
    ship_name = body.get("name")

    room = _first_object(SHIPYARD_ROOM_KEY)
    if not room:
        raise Http404(f"Room '{SHIPYARD_ROOM_KEY}' was not found.")

    vendor = _get_vendor_in_room(room, ships_mode=True)
    if not vendor:
        raise Http404("Shipyard shop not found in room.")

    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=ship_id, name=ship_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Ship not found in shipyard catalog."}, status=404)

    summary = template.get_vehicle_summary() if hasattr(template, "get_vehicle_summary") else template.key
    return JsonResponse(
        {
            "ok": True,
            "message": f"{template.key}\n{template.db.desc or 'No description available.'}\n{summary}",
            "ship": {
                "id": str((getattr(template.db, "catalog", None) or {}).get("vehicle_id") or template.id),
                "key": template.key,
                "description": template.db.desc or "",
                "summary": summary,
                "price": _ship_price(template),
            },
            "state": vendor.get_shop_state_for_api(),
        }
    )


@csrf_exempt
@require_POST
def shipyard_buy(request):
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

    ship_id = body.get("shipId")
    ship_name = body.get("name")

    room = _first_object(SHIPYARD_ROOM_KEY)
    if not room:
        raise Http404(f"Room '{SHIPYARD_ROOM_KEY}' was not found.")

    vendor = _get_vendor_in_room(room, ships_mode=True)
    if not vendor:
        raise Http404("Shipyard shop not found in room.")

    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=ship_id, name=ship_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Ship not found in catalog."}, status=404)

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
    item_id = body.get("itemId")
    item_name = body.get("name")

    if not room_key:
        return JsonResponse({"ok": False, "message": "Missing room."}, status=400)

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    vendor = _get_vendor_in_room(room, ships_mode=False)
    if not vendor:
        raise Http404("No catalog shop kiosk found in this room.")

    buyer = None
    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=item_id, name=item_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Item not found in catalog."}, status=404)

    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    market_type = getattr(vendor.db, "market_type", None) or "normal"
    price = econ.get_final_price(template, buyer=buyer, location=room, market_type=market_type)
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
            "state": vendor.get_shop_state_for_api(buyer=buyer),
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
    item_id = body.get("itemId")
    item_name = body.get("name")

    if not room_key:
        return JsonResponse({"ok": False, "message": "Missing room."}, status=400)

    room = _first_object(room_key)
    if not room:
        raise Http404(f"Room '{room_key}' was not found.")

    vendor = _get_vendor_in_room(room, ships_mode=False)
    if not vendor:
        raise Http404("No catalog shop kiosk found in this room.")

    stock = _template_stock(vendor)
    template = _find_template(stock, template_id=item_id, name=item_name)
    if not template:
        return JsonResponse({"ok": False, "message": "Item not found in catalog."}, status=404)

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

    new_item = template.copy(new_key=template.key)
    new_item.db.is_template = False
    if new_item.tags.has("for_sale", category="shop_stock"):
        new_item.tags.remove("for_sale", category="shop_stock")
    vid = vendor.db.vendor_id
    if vid and new_item.tags.has(vid, category="vendor"):
        new_item.tags.remove(vid, category="vendor")
    new_item.db.owner = buyer
    new_item.locks.add("get:true();drop:true();give:true()")
    new_item.move_to(buyer, quiet=True)

    vendor_amount, tax_amount = vendor.record_sale(
        buyer,
        price,
        tx_type="catalog_purchase",
        memo=f"{buyer.key} bought {template.key} from {vendor.key}",
    )

    return JsonResponse(
        {
            "ok": True,
            "message": f"Purchased {new_item.key} for {price:,} cr. Remaining balance: {buyer.db.credits:,} cr.",
            "vendorAmount": vendor_amount,
            "taxAmount": tax_amount,
            "buyerCredits": buyer.db.credits,
            "state": vendor.get_shop_state_for_api(buyer=buyer),
        }
    )
