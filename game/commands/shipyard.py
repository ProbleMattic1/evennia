"""
Shipyard commands: browse stock, inspect ships, purchase.

Commands provided:
  shipyard       — list ships for sale at the current location
  inspectship    — show full details on a specific ship
  buyship        — purchase a ship, deduct credits, spawn in delivery hangar
"""

from commands.command import Command


# ---------------------------------------------------------------------------
# Room-level helpers
# ---------------------------------------------------------------------------

def _get_ship_vendor_in_room(caller):
    """First CatalogVendor with catalog_mode='ships' in caller's room."""
    loc = caller.location
    if not loc:
        return None
    for obj in loc.contents:
        if not obj.is_typeclass("typeclasses.shops.CatalogVendor", exact=False):
            continue
        if getattr(obj.db, "catalog_mode", None) == "ships":
            return obj
    return None


def _get_stock_for_shop(shop):
    """
    Return sale templates from the vendor-assigned catalog for this shipyard.

    Assignment model: tag (vendor_id, category="vendor") on the catalog object.
    Only template entries are considered sellable stock.
    """
    if not shop:
        return []
    return [obj for obj in shop.get_catalog_items() if getattr(obj.db, "is_template", False)]


def _find_template_by_name(name, candidates):
    """Find a for-sale template by partial name match (case-insensitive)."""
    name = (name or "").strip().lower()
    if not name:
        return None
    for obj in candidates:
        if name in obj.key.lower():
            return obj
    return None


def _update_owned_vehicles(owner, ship):
    """Add ship to owner's owned_vehicles list if not already present."""
    if not owner:
        return
    owned = owner.db.owned_vehicles or []
    if ship not in owned:
        owned.append(ship)
    owner.db.owned_vehicles = owned


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class CmdShipyard(Command):
    """
    List ships for sale at a shipyard.

    Usage:
      catalog
      browse
      ships
      shipyard   (alias — also works once you are inside the shipyard)

    Must be standing in a room with a shipyard kiosk.
    The primary key is a verb so it does not shadow room exits named 'shipyard'.
    """

    key = "catalog"
    aliases = ["browse", "ships", "listships", "shipyard"]
    locks = "cmd:all()"
    help_category = "Shipyard"

    def func(self):
        caller = self.caller
        shop = _get_ship_vendor_in_room(caller)
        if not shop:
            caller.msg("There is no shipyard here. Find a shipyard kiosk to browse available ships.")
            return

        stock = _get_stock_for_shop(shop)
        if not stock:
            caller.msg("No ships are currently on display here.")
            return

        lines = [f"|wShips for sale at {shop.key}:|n"]
        for v in stock:
            lines.append(f"  {v.get_vehicle_summary()}")
        caller.msg("\n".join(lines))


class CmdInspectShip(Command):
    """
    Inspect a ship on display at a shipyard.

    Usage:
      inspectship <name>

    Must be standing in a room with a shipyard kiosk.
    """

    key = "inspectship"
    aliases = ["inspect"]
    locks = "cmd:all()"
    help_category = "Shipyard"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Inspect which ship? Use |wshipyard|n to list available ships.")
            return

        shop = _get_ship_vendor_in_room(caller)
        if not shop:
            caller.msg("There is no shipyard here.")
            return

        stock = _get_stock_for_shop(shop)
        ship = _find_template_by_name(self.args, stock)
        if not ship:
            caller.msg(f"No ship matching '{self.args.strip()}' is on display. Use |wshipyard|n to list options.")
            return

        caller.msg(f"|w{ship.key}|n\n{ship.db.desc or 'No description available.'}\n{ship.get_vehicle_summary()}")


class CmdBuyShip(Command):
    """
    Purchase a ship from a shipyard.

    Usage:
      buyship <name>

    Deducts credits and places your ship in the delivery hangar.
    Must be standing in a room with a shipyard kiosk.
    """

    key = "buyship"
    aliases = ["buyship"]
    locks = "cmd:all()"
    help_category = "Shipyard"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Buy which ship? Use |wshipyard|n to list ships and |winspectship <name>|n for details.")
            return

        shop = _get_ship_vendor_in_room(caller)
        if not shop:
            caller.msg("There is no shipyard here.")
            return

        stock = _get_stock_for_shop(shop)
        template = _find_template_by_name(self.args, stock)
        if not template:
            caller.msg(f"No ship matching '{self.args.strip()}' is for sale. Use |wshipyard|n to list options.")
            return

        from typeclasses.economy import get_economy
        from world.econ_automation.resolve_prices import resolve_vehicle_listing_price

        price = resolve_vehicle_listing_price(template, room=caller.location, buyer=caller, vendor=shop)
        if int(price) <= 0:
            caller.msg("This ship has no listed price. Contact an administrator.")
            return

        econ = get_economy(create_missing=True)
        credits = econ.get_character_balance(caller)
        if credits < price:
            caller.msg(
                f"|w{template.key}|n costs |y{price:,}|n cr. "
                f"You have |y{credits:,}|n cr. You need |r{price - credits:,}|n more."
            )
            return

        delivery = shop.db.delivery_room or getattr(caller.location.db, "ship_delivery_room", None)
        if not delivery:
            caller.msg("This shipyard has no delivery hangar configured. Contact an administrator.")
            return

        # Spawn a copy; the template object stays in the showroom for future buyers.
        new_ship = template.copy(new_key=template.key)
        new_ship.db.is_template = False
        new_ship.tags.remove("for_sale", category="shop_stock")
        vid = shop.db.vendor_id
        if vid and new_ship.tags.has(vid, category="vendor"):
            new_ship.tags.remove(vid, category="vendor")
        new_ship.db.owner = caller
        new_ship.db.allowed_boarders = [caller]
        new_ship.db.state = "docked"
        new_ship.db.fuel = template.db.max_fuel or 100
        new_ship.db.max_fuel = new_ship.db.fuel
        new_ship.db.desc = f"Your {template.key}, ready for travel."
        new_ship.move_to(delivery, quiet=True)

        vendor_amount, tax_amount = shop.record_sale(
            caller,
            price,
            tx_type="ship_purchase",
            memo=f"{caller.key} purchased a ship from {shop.key}",
            withdraw_memo=f"Ship purchase at {shop.key}",
        )
        _update_owned_vehicles(caller, new_ship)

        msg = (
            f"You purchase |w{template.key}|n for |y{price:,}|n cr. "
            f"Your ship is waiting in |w{delivery.key}|n. "
            f"Remaining balance: |y{caller.db.credits:,}|n cr."
        )
        if tax_amount > 0:
            msg += f" (|y{vendor_amount:,}|n cr to vendor, |y{tax_amount:,}|n cr tax)"
        caller.msg(msg)
