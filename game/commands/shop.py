"""
General catalog vendor commands (tech, supply, mining, toy kiosks).

Uses CatalogVendor with catalog_mode="items". Ship catalogs use shipyard commands.
"""

from commands.command import Command


def _get_general_vendor_in_room(caller):
    """First CatalogVendor with catalog_mode='items' in caller's room."""
    loc = caller.location
    if not loc:
        return None
    for obj in loc.contents:
        if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            continue
        if getattr(obj.db, "catalog_mode", None) == "ships":
            continue
        return obj
    return None


def _get_stock_for_vendor(shop):
    if not shop:
        return []
    return [obj for obj in shop.get_catalog_items() if getattr(obj.db, "is_template", False)]


def _find_template_by_name(name, candidates):
    name = (name or "").strip().lower()
    if not name:
        return None
    for obj in candidates:
        if name in obj.key.lower():
            return obj
    return None


class CmdShop(Command):
    """
    List goods for sale at a general merchant kiosk.

    Usage:
      shop
      wares

    For ships at a shipyard, use |wcatalog|n or |wshipyard|n instead.
    """

    key = "shop"
    aliases = ["wares", "browseware"]
    locks = "cmd:all()"
    help_category = "Commerce"

    def func(self):
        caller = self.caller
        vendor = _get_general_vendor_in_room(caller)
        if not vendor:
            caller.msg("There is no merchant kiosk here. (For ships, try |wcatalog|n at a shipyard.)")
            return

        stock = _get_stock_for_vendor(vendor)
        if not stock:
            caller.msg("Nothing is on sale here right now.")
            return

        from world.econ_automation.resolve_prices import resolve_catalog_item_price

        market_type = getattr(vendor.db, "market_type", None) or "normal"
        lines = [f"|w{vendor.db.vendor_name or vendor.key}:|n"]
        for item in stock:
            if getattr(item.db, "grants_random_claim_only", False):
                continue
            price = resolve_catalog_item_price(
                item,
                buyer=caller,
                room=caller.location,
                market_type=market_type,
                vendor=vendor,
            )
            if getattr(item.db, "is_sale_package", False):
                if getattr(item.db, "includes_random_claim", True):
                    extra = "package + random claim — deploymine <package> <claim>"
                else:
                    extra = "equipment only — deploymine <package> <claim>"
                lines.append(f"  |c{item.key}|n — |y{price:,}|n cr  |x[{extra}]|n")
            elif getattr(item.db, "grants_random_claim_only", False):
                lines.append(
                    f"  |c{item.key}|n — |y{price:,}|n cr  "
                    f"|x[random claim deed — deploymine with a package]|n"
                )
            else:
                lines.append(f"  |c{item.key}|n — |y{price:,}|n cr")
        caller.msg("\n".join(lines))


class CmdBuy(Command):
    """
    Buy an item from the merchant kiosk in this room.

    Usage:
      buy <name>

    Matches display names from |wshop|n. Mining packages go to inventory;
    use |wdeploymine <package> <claim>|n to deploy. For spacecraft, use |wbuyship|n.
    """

    key = "buy"
    aliases = ["purchase"]
    locks = "cmd:all()"
    help_category = "Commerce"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Buy what? Use |wshop|n to see goods. For ships, use |wbuyship <name>|n.")
            return

        vendor = _get_general_vendor_in_room(caller)
        if not vendor:
            caller.msg("There is no merchant kiosk here. For ships, use |wbuyship|n at a shipyard.")
            return

        stock = _get_stock_for_vendor(vendor)

        from typeclasses.economy import get_economy
        from world.econ_automation.resolve_prices import resolve_catalog_item_price

        econ = get_economy(create_missing=True)
        market_type = getattr(vendor.db, "market_type", None) or "normal"

        # Normal item purchase (includes mining packages — they go to inventory)
        template = _find_template_by_name(self.args, stock)
        if not template:
            caller.msg(f"No item matching '{self.args.strip()}' is sold here. Use |wshop|n to list stock.")
            return

        price = resolve_catalog_item_price(
            template,
            buyer=caller,
            room=caller.location,
            market_type=market_type,
            vendor=vendor,
        )
        if price <= 0:
            caller.msg("That item has no valid price. Contact an administrator.")
            return

        credits = econ.get_character_balance(caller)
        if credits < price:
            caller.msg(
                f"|w{template.key}|n costs |y{price:,}|n cr. "
                f"You have |y{credits:,}|n cr. You need |r{price - credits:,}|n more."
            )
            return

        if getattr(template.db, "grants_random_claim_only", False):
            from typeclasses.claim_market import collect_primary_deed_sale, get_primary_deed_broker

            broker = get_primary_deed_broker()
            if broker:
                vendor_amount, tax_amount = collect_primary_deed_sale(
                    caller,
                    price,
                    broker,
                    tx_type="catalog_purchase",
                    memo=f"{caller.key} bought {template.key} from {vendor.key}",
                    withdraw_memo=f"Purchase at {vendor.key}",
                )
                revenue_to = "broker"
            else:
                vendor_amount, tax_amount = vendor.record_sale(
                    caller,
                    price,
                    tx_type="catalog_purchase",
                    memo=f"{caller.key} bought {template.key} from {vendor.key}",
                    sold_template=template,
                )
                revenue_to = "vendor"
            msg = (
                f"You purchase |w{template.key}|n for |y{price:,}|n cr. "
                f"Remaining balance: |y{caller.db.credits:,}|n cr."
            )
            from typeclasses.claim_utils import grant_random_claim_on_purchase

            claim, jackpot = grant_random_claim_on_purchase(caller)
            if claim:
                if jackpot:
                    msg += "\n|g★ JACKPOT! You received an |wElite Claim|n! ★|n"
                else:
                    msg += f"\nYou received a random claim: |w{claim.key}|n."
            if tax_amount > 0:
                msg += (
                    f" (|y{vendor_amount:,}|n cr to {revenue_to}, |y{tax_amount:,}|n cr tax)"
                )
            caller.msg(msg)
            return

        new_item = template.copy(new_key=template.key)
        new_item.db.is_template = False
        if new_item.tags.has("for_sale", category="shop_stock"):
            new_item.tags.remove("for_sale", category="shop_stock")
        vid = vendor.db.vendor_id
        if vid and new_item.tags.has(vid, category="vendor"):
            new_item.tags.remove(vid, category="vendor")
        new_item.db.owner = caller
        new_item.locks.add("get:true();drop:true();give:true()")
        if getattr(template.db, "is_sale_package", False):
            new_item.db.package_tier = getattr(template.db, "package_tier", None) or template.key
            new_item.tags.add("mining_package", category="mining")
        new_item.move_to(caller, quiet=True)

        vendor_amount, tax_amount = vendor.record_sale(
            caller,
            price,
            tx_type="catalog_purchase",
            memo=f"{caller.key} bought {template.key} from {vendor.key}",
            sold_template=template,
        )

        msg = (
            f"You buy |w{new_item.key}|n for |y{price:,}|n cr. "
            f"Remaining balance: |y{caller.db.credits:,}|n cr."
        )
        if getattr(template.db, "is_sale_package", False) and getattr(
            template.db, "includes_random_claim", True
        ):
            from typeclasses.claim_utils import grant_random_claim_on_purchase

            claim, jackpot = grant_random_claim_on_purchase(caller)
            if claim:
                if jackpot:
                    msg += "\n|g★ JACKPOT! You received an |wElite Claim|n! ★|n"
                else:
                    msg += f"\nYou received a random claim: |w{claim.key}|n."
        if tax_amount > 0:
            msg += f" (|y{vendor_amount:,}|n cr to vendor, |y{tax_amount:,}|n cr tax)"
        caller.msg(msg)
