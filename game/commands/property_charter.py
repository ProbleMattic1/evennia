"""
Admin / staff commands for managing NanoMegaPlex charter property lots.

These commands require perm(Admin) and operate on broker-held deed inventory.

Commands:
  charterinventory          — list all charter deeds currently on the broker
  grantcharter <player> <lot_key|#claim_id>
                            — transfer a broker-held charter deed to a player
  releasecharter <lot_key|#claim_id> <price>
                            — list a broker deed on the secondary deed market
"""

from commands.command import Command

from typeclasses.characters import NANOMEGA_REALTY_CHARACTER_KEY
from typeclasses.property_claims import PROPERTY_CLAIM_CATEGORY, PROPERTY_CLAIM_TAG
from typeclasses.property_deed_market import list_property_deed_for_sale
from typeclasses.property_title_sync import sync_property_title_from_deed_location


def _get_broker():
    from evennia import search_object
    found = search_object(NANOMEGA_REALTY_CHARACTER_KEY)
    return found[0] if found else None


def _charter_deeds_on_broker(broker):
    """Return PropertyClaim objects currently in the broker's inventory."""
    return [
        obj
        for obj in broker.contents
        if obj.tags.has(PROPERTY_CLAIM_TAG, category=PROPERTY_CLAIM_CATEGORY)
    ]


def _find_claim(broker, identifier):
    """
    Resolve a claim from broker inventory by:
      - exact lot_key match (case-insensitive)
      - numeric dbref / claim id   e.g. "42" or "#42"
    Returns the first match or None.
    """
    ident = identifier.strip().lstrip("#")
    deeds = _charter_deeds_on_broker(broker)
    # Try numeric dbref first
    if ident.isdigit():
        target_id = int(ident)
        for deed in deeds:
            if deed.id == target_id:
                return deed
    # Try lot_key substring (case-insensitive)
    lower = ident.lower()
    for deed in deeds:
        lot_key = (getattr(deed.db, "lot_key", None) or "").lower()
        if lower in lot_key or lower in deed.key.lower():
            return deed
    return None


class CmdCharterInventory(Command):
    """
    List all charter property deeds currently held by the NanoMegaPlex Real
    Estate broker (broker-held vault inventory, not on the primary exchange).

    Usage:
      charterinventory
    """

    key = "charterinventory"
    aliases = ["charterlisting", "charterinv"]
    locks = "cmd:perm(Admin)"
    help_category = "Charter"

    def func(self):
        broker = _get_broker()
        if not broker:
            self.caller.msg(f"Broker '{NANOMEGA_REALTY_CHARACTER_KEY}' not found.")
            return

        deeds = _charter_deeds_on_broker(broker)
        if not deeds:
            self.caller.msg("No charter deeds currently in broker inventory.")
            return

        lines = [f"Charter inventory ({len(deeds)} deed{'s' if len(deeds) != 1 else ''}):\n"]
        for deed in sorted(deeds, key=lambda d: d.key):
            lot_key = getattr(deed.db, "lot_key", "unknown")
            tier    = getattr(deed.db, "lot_tier", "?")
            lot_ref = getattr(deed.db, "lot_ref", None)
            zone    = (getattr(lot_ref.db, "zone", "?") if lot_ref else "?")
            size    = (getattr(lot_ref.db, "size_units", "?") if lot_ref else "?")
            district = (getattr(lot_ref.db, "district_label", "") if lot_ref else "")
            district_str = f"  [{district}]" if district else ""
            lines.append(
                f"  #{deed.id}  {lot_key}  "
                f"(Tier {tier}, {zone}, {size} units{district_str})"
            )
        self.caller.msg("\n".join(lines))


class CmdGrantCharter(Command):
    """
    Transfer a broker-held charter property deed to a player at no cost.

    The deed moves from the NanoMegaPlex Real Estate broker to the target
    player's inventory.  Title ownership updates immediately.  Use
    charterinventory to see available lot keys and claim ids.

    Usage:
      grantcharter <player> = <lot_key or #claim_id>

    Examples:
      grantcharter Varek = Crown Atrium Penthouse I
      grantcharter Varek = #42
    """

    key = "grantcharter"
    aliases = ["chartergrant"]
    locks = "cmd:perm(Admin)"
    help_category = "Charter"

    def parse(self):
        if "=" in self.args:
            left, _, right = self.args.partition("=")
            self.player_name = left.strip()
            self.lot_identifier = right.strip()
        else:
            self.player_name = ""
            self.lot_identifier = ""

    def func(self):
        caller = self.caller

        if not self.player_name or not self.lot_identifier:
            caller.msg("Usage: grantcharter <player> = <lot_key or #claim_id>")
            return

        broker = _get_broker()
        if not broker:
            caller.msg(f"Broker '{NANOMEGA_REALTY_CHARACTER_KEY}' not found.")
            return

        deed = _find_claim(broker, self.lot_identifier)
        if not deed:
            caller.msg(
                f"No charter deed matching '{self.lot_identifier}' in broker inventory.\n"
                "Use |wcharterinventory|n to see available deeds."
            )
            return

        # Resolve the target player character
        from evennia import search_object
        matches = search_object(self.player_name, typeclass="typeclasses.characters.Character")
        if not matches:
            caller.msg(f"No character found matching '{self.player_name}'.")
            return
        if len(matches) > 1:
            names = ", ".join(m.key for m in matches)
            caller.msg(f"Multiple matches: {names}. Be more specific.")
            return
        recipient = matches[0]

        lot = getattr(deed.db, "lot_ref", None)
        lot_key = getattr(deed.db, "lot_key", deed.key)

        # Move deed from broker to recipient
        deed.move_to(recipient, quiet=True)
        sync_property_title_from_deed_location(deed)

        # Align lot.db.owner with the new title holder
        if lot:
            lot.db.owner = recipient

        caller.msg(
            f"Charter deed '{lot_key}' (#{deed.id}) granted to {recipient.key}."
        )
        recipient.msg(
            f"\n|wCharter grant:|n You have received the deed to |y{lot_key}|n "
            f"from NanoMegaPlex Real Estate.\n"
            f"Use |wstartproperty|n to begin generating income from your parcel."
        )


class CmdReleaseCharter(Command):
    """
    List a broker-held charter deed on the secondary deed market at the
    specified price.  Buyers can then purchase it through the web UI or the
    |wbuypropertydeed|n command.

    This moves the deed to hub escrow (same path as a normal resale listing).
    Title ownership is cleared until a buyer completes the purchase.

    Usage:
      releasecharter <lot_key or #claim_id> = <price in cr>

    Examples:
      releasecharter Crown Atrium Penthouse I = 500000
      releasecharter #42 = 500000
    """

    key = "releasecharter"
    aliases = ["charterrelease"]
    locks = "cmd:perm(Admin)"
    help_category = "Charter"

    def parse(self):
        if "=" in self.args:
            left, _, right = self.args.partition("=")
            self.lot_identifier = left.strip()
            self.price_str = right.strip()
        else:
            self.lot_identifier = self.args.strip()
            self.price_str = ""

    def func(self):
        caller = self.caller

        if not self.lot_identifier or not self.price_str:
            caller.msg("Usage: releasecharter <lot_key or #claim_id> = <price>")
            return

        try:
            price = int(round(float(self.price_str.replace(",", ""))))
            if price < 0:
                raise ValueError
        except ValueError:
            caller.msg("Price must be a positive integer (credits).")
            return

        broker = _get_broker()
        if not broker:
            caller.msg(f"Broker '{NANOMEGA_REALTY_CHARACTER_KEY}' not found.")
            return

        deed = _find_claim(broker, self.lot_identifier)
        if not deed:
            caller.msg(
                f"No charter deed matching '{self.lot_identifier}' in broker inventory.\n"
                "Use |wcharterinventory|n to see available deeds."
            )
            return

        lot_key = getattr(deed.db, "lot_key", deed.key)
        ok, msg = list_property_deed_for_sale(broker, deed.id, price)
        if not ok:
            caller.msg(f"Could not list deed: {msg}")
            return

        caller.msg(
            f"Charter deed '{lot_key}' listed on the secondary market for {price:,} cr."
        )
