from django.db.models import Q

from evennia import search_tag
from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultObject
from evennia.typeclasses.tags import Tag

from .objects import ObjectParent


class CatalogVendor(ObjectParent, DefaultObject):
    """
    Room kiosk backed by a vendor tag catalog.
    catalog_mode: "items" (general goods) or "ships" (vehicles).
    Catalog objects carry tag (vendor_id, category="vendor") and db.is_template.
    """

    def at_object_creation(self):
        self.db.vendor_id = None
        self.db.vendor_name = None
        self.db.inventory = []
        self.db.credits = 0
        self.db.catalog_mode = "items"

    def get_catalog_items(self):
        """
        Return all objects tagged for sale at this vendor.
        Assignment = tag (vendor_id, category="vendor") on the Object.
        Add the tag from the Object's edit page (Tags inline), not standalone Tag admin.

        Fallback: if primary search returns nothing, also match tags with
        db_tagtype NULL or empty (some admin UIs save tagtype as "").
        """
        vid = self.db.vendor_id
        if not vid:
            return []
        items = search_tag(vid, category="vendor")
        if items:
            return items
        tags = Tag.objects.filter(
            db_key__iexact=vid.strip().lower(),
            db_category__iexact="vendor",
            db_model__iexact="objectdb",
        ).filter(Q(db_tagtype__isnull=True) | Q(db_tagtype=""))
        if not tags.exists():
            return []
        return list(ObjectDB.objects.filter(db_tags__in=tags).distinct())

    def record_sale(self, caller, price, *, tx_type="vendor_sale", memo=None, withdraw_memo=None):
        """
        Route a purchase through the economy ledger.
        Returns (vendor_amount, tax_amount).
        """
        tax_rate = getattr(self.db, "tax_rate", None)
        if tax_rate is None or not isinstance(tax_rate, (int, float)):
            tax_rate = 0.0
        tax_rate = max(0.0, min(1.0, float(tax_rate)))

        tax_amount = int(round(price * tax_rate))
        vendor_amount = price - tax_amount

        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        player_account = econ.get_character_account(caller)
        vendor_account = getattr(self.db, "vendor_account", None) or econ.get_vendor_account(
            getattr(self.db, "vendor_id", None) or "vendor"
        )
        treasury_account = econ.get_treasury_account("alpha-prime")

        econ.ensure_account(player_account, opening_balance=int(caller.db.credits or 0))
        econ.ensure_account(vendor_account, opening_balance=int(self.db.credits or 0))
        econ.ensure_account(treasury_account, opening_balance=int(econ.db.tax_pool or 0))

        w_memo = withdraw_memo or f"Purchase at {self.key}"
        econ.withdraw(player_account, price, memo=w_memo)
        econ.deposit(vendor_account, vendor_amount, memo=f"Vendor revenue from {self.key}")

        if tax_amount > 0:
            econ.deposit(treasury_account, tax_amount, memo=f"Sales tax from {self.key}")

        econ.record_transaction(
            tx_type=tx_type,
            amount=price,
            from_account=player_account,
            to_account=vendor_account,
            memo=memo or f"{caller.key} purchased at {self.key}",
            extra={
                "tax_amount": tax_amount,
                "treasury_account": treasury_account,
                "vendor_account": vendor_account,
            },
        )

        caller.db.credits = econ.get_balance(player_account)
        self.db.credits = econ.get_balance(vendor_account)
        econ.db.tax_pool = econ.get_balance(treasury_account)

        return vendor_amount, tax_amount

    def _exits_for_api(self):
        room = self.location
        exits = []
        if room:
            for ex in room.contents:
                dest = getattr(ex, "destination", None)
                if not dest:
                    continue
                exits.append(
                    {
                        "key": ex.key,
                        "label": ex.key.title(),
                        "command": ex.key,
                        "destination": dest.key if dest else None,
                    }
                )
        return exits

    def get_shop_state_for_api(self, buyer=None):
        """
        Unified API for both items and ships modes.
        Returns dict with shopName, roomName, roomDescription, exits, storyLines,
        plus items (for catalog_mode="items") or ships (for catalog_mode="ships").
        """
        mode = getattr(self.db, "catalog_mode", None) or "items"
        room = self.location
        room_name = room.key if room else ""
        room_desc = (getattr(room.db, "desc", None) or "") if room else ""
        exits = self._exits_for_api()

        if mode == "ships":
            ships = []
            for obj in self.get_catalog_items():
                economy = getattr(obj.db, "economy", None) or {}
                price = economy.get("total_price_cr") or economy.get("base_price_cr")
                summary = (
                    obj.get_vehicle_summary()
                    if hasattr(obj, "get_vehicle_summary")
                    else str(obj.key)
                )
                ship_id = (getattr(obj.db, "catalog", None) or {}).get("vehicle_id") or obj.key
                ships.append(
                    {
                        "id": str(ship_id),
                        "key": obj.key,
                        "description": getattr(obj.db, "desc", "") or "",
                        "summary": summary,
                        "price": price,
                    }
                )
            count = len(ships)
            return {
                "catalogMode": "ships",
                "vendorId": self.db.vendor_id or "",
                "shopName": self.db.vendor_name or self.key,
                "roomName": room_name,
                "roomDescription": room_desc,
                "ships": ships,
                "items": [],
                "exits": exits,
                "storyLines": [
                    {"id": "yard-title", "text": room_name, "kind": "title"},
                    {"id": "yard-desc", "text": room_desc or "No description available.", "kind": "room"},
                    {"id": "yard-summary", "text": f"{count} ships currently listed for sale.", "kind": "system"},
                ],
            }

        from typeclasses.economy import get_economy

        econ = get_economy(create_missing=True)
        market_type = getattr(self.db, "market_type", None) or "normal"
        catalog = []
        for obj in self.get_catalog_items():
            if not getattr(obj.db, "is_template", False):
                continue
            if getattr(obj.db, "grants_random_claim_only", False):
                continue
            price = econ.get_final_price(
                obj,
                buyer=buyer,
                location=room,
                market_type=market_type,
            )
            desc = getattr(obj.db, "desc", "") or ""
            catalog.append(
                {
                    "id": str(obj.id),
                    "key": obj.key,
                    "description": desc,
                    "summary": desc[:120] + ("…" if len(desc) > 120 else ""),
                    "price": price,
                }
            )
        count = len(catalog)
        return {
            "catalogMode": "items",
            "vendorId": self.db.vendor_id or "",
            "shopName": self.db.vendor_name or self.key,
            "roomName": room_name,
            "roomDescription": room_desc,
            "ships": [],
            "items": catalog,
            "exits": exits,
            "storyLines": [
                {"id": "shop-title", "text": room_name, "kind": "title"},
                {"id": "shop-desc", "text": room_desc or "No description available.", "kind": "room"},
                {"id": "shop-summary", "text": f"{count} items listed for sale.", "kind": "system"},
            ],
        }
