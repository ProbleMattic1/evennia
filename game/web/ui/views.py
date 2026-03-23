from urllib.parse import quote

from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET
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
def shipyard_state(request):
    room = _first_object(SHIPYARD_ROOM_KEY)
    if not room:
        raise Http404(f"Room '{SHIPYARD_ROOM_KEY}' was not found.")

    shop = None
    for obj in room.contents:
        if _is_ship_catalog_vendor(obj):
            shop = obj
            break

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

    shop = None
    for obj in room.contents:
        if _is_items_catalog_vendor(obj):
            shop = obj
            break

    if not shop:
        raise Http404("No catalog shop kiosk found in this room.")

    data = shop.get_shop_state_for_api(buyer=None)
    return JsonResponse(data)
