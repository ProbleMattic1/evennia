"""
Mining commands — Pass 2.

Commands
--------
survey        Advance and display the geological survey for a MiningSite.
claimsite     Claim an unclaimed MiningSite.
deployrig     Install a MiningRig (from inventory or room) at the current site.
linkstorage   Attach a MiningStorage unit (from inventory or room) to the site.
mines         List all sites you own.
minestatus    Show full status for a site (defaults to site in current room).
collectore    Sell all ore in the site's linked storage at base price.
setrig        Tune rig settings (mode, power_level, target_family,
              purity_cutoff, maintenance_level).
repairrig     Repair a broken rig, resetting wear to 0.

Design notes
------------
- All room-level lookups use the "mining_site" / "mining_rig" tags.
- survey now advances the survey_level tier (0→3) and shows tiered info.
- collectore is a simplified "sell to depot" action (Pass 3 replaces with
  proper market pricing, taxation, and transport).
"""

from commands.command import Command
from typeclasses.mining import RESOURCE_CATALOG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_site_in_room(caller):
    """Return the first MiningSite object in caller's current location."""
    if not caller.location:
        return None
    for obj in caller.location.contents:
        if obj.tags.has("mining_site", category="mining"):
            return obj
    return None


def _find_tagged_object(caller, tag_key, name=None):
    """
    Search caller's inventory then current room for an object with the given
    mining tag.  If name is given, filter by case-insensitive key match.
    Returns the first match or None.
    """
    candidates = list(caller.contents)
    if caller.location:
        candidates += list(caller.location.contents)
    for obj in candidates:
        if not obj.tags.has(tag_key, category="mining"):
            continue
        if name and name.lower() not in obj.key.lower():
            continue
        return obj
    return None


def _find_owned_sites(caller):
    """Return all MiningSites from caller's db.owned_sites list."""
    from evennia import search_object

    owned = caller.db.owned_sites or []
    sites = []
    for entry in owned:
        if hasattr(entry, "key"):
            sites.append(entry)
        else:
            result = search_object(entry)
            if result:
                sites.append(result[0])
    return sites


def _add_owned_site(caller, site):
    owned = caller.db.owned_sites or []
    if site not in owned:
        owned.append(site)
    caller.db.owned_sites = owned


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class CmdSurvey(Command):
    """
    Survey the mineral deposit at the current location.

    Usage:
      survey
      prospect

    Each use advances the survey level of the site by one tier (max 3):
      Level 0 — unsurveyed (no data)
      Level 1 — basic scan (richness tier, content families, rough output range)
      Level 2 — standard assessment (approximate percentages)
      Level 3 — full geological survey (exact composition and depletion data)

    Use |wminestatus|n to view the current survey data without advancing it.
    """

    key = "survey"
    aliases = ["prospect"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no minable deposit here.")
            return

        new_level, report = site.advance_survey()
        from typeclasses.mining import SURVEY_LEVELS
        label = SURVEY_LEVELS.get(new_level, "?")
        if new_level >= 3:
            caller.msg(f"|wSurvey complete ({label}).|n\n{report}")
        else:
            remaining = 3 - new_level
            caller.msg(
                f"|wSurvey advanced to level {new_level} ({label}).|n  "
                f"({remaining} more survey{'s' if remaining > 1 else ''} to full assessment)\n{report}"
            )


class CmdClaimSite(Command):
    """
    Claim an unclaimed mineral deposit.

    Usage:
      claimsite

    You must be standing in a room that contains an unclaimed MiningSite.
    Once claimed you are the site owner and can deploy equipment.
    """

    key = "claimsite"
    aliases = ["claim"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no minable deposit here to claim.")
            return
        if site.db.is_claimed:
            owner = site.db.owner
            if owner == caller:
                caller.msg(f"You already own |w{site.key}|n.")
            else:
                caller.msg(
                    f"|w{site.key}|n is already claimed"
                    + (f" by {owner.key}." if owner else ".")
                )
            return

        site.db.is_claimed = True
        site.db.owner = caller
        _add_owned_site(caller, site)

        caller.msg(f"You register a claim on |w{site.key}|n. Deploy a rig and storage to begin production.")
        caller.location.msg_contents(
            f"{caller.key} files a mining claim on {site.key}.",
            exclude=caller,
        )


class CmdDeployRig(Command):
    """
    Install a mining rig at the current site.

    Usage:
      deployrig
      deployrig <rig name>

    Searches your inventory then the room for a MiningRig object.
    You must own the site.  Only one rig can be active per site.
    Once deployed the rig is linked to the site and production will begin
    as soon as storage is also linked.
    """

    key = "deployrig"
    aliases = ["installrig"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return
        if site.db.active_rig:
            caller.msg(
                f"|w{site.key}|n already has a rig installed: {site.db.active_rig.key}. "
                f"Uninstall it first."
            )
            return

        name = self.args.strip() or None
        rig = _find_tagged_object(caller, "mining_rig", name=name)
        if not rig:
            msg = "No mining rig found"
            if name:
                msg += f" matching '{name}'"
            msg += " in your inventory or this room."
            caller.msg(msg)
            return

        rig.install(site, owner=caller)
        site.db.active_rig = rig

        if site.db.linked_storage:
            site.schedule_next_cycle()
            caller.msg(
                f"You install |w{rig.key}|n at |w{site.key}|n. "
                f"Production scheduled — first cycle in 12 hours."
            )
        else:
            caller.msg(
                f"You install |w{rig.key}|n at |w{site.key}|n. "
                f"Link a storage unit to begin production."
            )


class CmdLinkStorage(Command):
    """
    Link a storage unit to the current mining site.

    Usage:
      linkstorage
      linkstorage <storage name>

    Searches your inventory then the room for a MiningStorage object.
    You must own the site.  Once linked, ore output will be deposited here
    every 12-hour cycle.
    """

    key = "linkstorage"
    aliases = ["attachstorage", "setstorage"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return

        name = self.args.strip() or None
        storage = _find_tagged_object(caller, "mining_storage", name=name)
        if not storage:
            msg = "No mining storage unit found"
            if name:
                msg += f" matching '{name}'"
            msg += " in your inventory or this room."
            caller.msg(msg)
            return

        old = site.db.linked_storage
        site.db.linked_storage = storage
        storage.db.site = site
        storage.db.owner = caller

        if old and old != storage:
            caller.msg(
                f"Storage swapped: |w{old.key}|n replaced by |w{storage.key}|n."
            )
        else:
            caller.msg(f"Storage unit |w{storage.key}|n linked to |w{site.key}|n.")

        if site.db.active_rig and site.db.active_rig.db.is_operational:
            if not site.db.next_cycle_at:
                site.schedule_next_cycle()
                caller.msg("Production scheduled — first cycle in 12 hours.")


class CmdMines(Command):
    """
    List all mining sites you own.

    Usage:
      mines
    """

    key = "mines"
    aliases = ["mysites", "mymines"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        sites = _find_owned_sites(caller)
        if not sites:
            caller.msg("You do not own any mining sites.")
            return

        lines = ["|wYour Mining Sites|n"]
        for site in sites:
            rig = site.db.active_rig
            storage = site.db.linked_storage
            status = "|gactive|n" if site.is_active else "|rinactive|n"
            loc = site.location.key if site.location else "?"
            lines.append(
                f"  {site.key:<30} {status}  "
                f"rig: {rig.key if rig else 'none':<20} "
                f"storage: {storage.key if storage else 'none':<20} "
                f"at: {loc}"
            )
        caller.msg("\n".join(lines))


class CmdMineStatus(Command):
    """
    Show full status of a mining site.

    Usage:
      minestatus
      minestatus <site name>

    Without arguments shows the status of a site in the current room.
    With a name, searches your owned sites.
    """

    key = "minestatus"
    aliases = ["minestat", "sitestat"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        name = self.args.strip()

        if name:
            sites = _find_owned_sites(caller)
            site = next(
                (s for s in sites if name.lower() in s.key.lower()),
                None,
            )
            if not site:
                caller.msg(f"No owned site matching '{name}'.")
                return
        else:
            site = _find_site_in_room(caller)
            if not site:
                caller.msg("There is no mining site here. Use |wminestatus <name>|n to check a remote site.")
                return

        caller.msg(site.get_status_report(looker=caller))

        storage = site.db.linked_storage
        if storage:
            caller.msg(storage.get_inventory_report())


class CmdCollectOre(Command):
    """
    Sell all ore in the site's storage at base market price.

    Usage:
      collectore

    Converts the aggregate storage inventory to credits at the standard
    base price per ton and deposits the amount into your account.

    Note: this is a simplified Pass-1 action.  Pass 3 will replace it with
    proper market pricing, taxation, and transport-based selling.
    """

    key = "collectore"
    aliases = ["sellore", "cashout"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return

        storage = site.db.linked_storage
        if not storage:
            caller.msg(f"|w{site.key}|n has no linked storage.")
            return

        inventory = storage.db.inventory or {}
        if not inventory:
            caller.msg(f"|w{storage.key}|n is empty — nothing to collect.")
            return

        from typeclasses.mining import get_commodity_price
        license_level = int(site.db.license_level or 0)
        sell_type = "sell" if license_level > 0 else "sell"

        total_value = 0
        lines = [
            f"|wOre collection — {site.key}|n"
            + (f"  [licensed — market pricing]" if license_level > 0 else "  [unlicensed — base pricing]")
        ]
        for key in sorted(inventory):
            tons = float(inventory[key])
            info = RESOURCE_CATALOG.get(key, {})
            name = info.get("name", key)
            price = get_commodity_price(key, location=caller.location, transaction_type=sell_type)
            value = int(tons * price)
            total_value += value
            lines.append(f"  {name:<28} {tons:>8.2f}t  @ {price:,} cr/t  |y{value:>10,}|n cr")

        lines.append(f"  {'Total':<28} {'':>8}    |y{total_value:>10,}|n cr")

        storage.withdraw_all()

        from typeclasses.economy import grant_character_credits

        grant_character_credits(
            caller,
            total_value,
            memo=f"Ore sale from {site.key}",
        )

        lines.append(f"\n|gDeposited |y{total_value:,}|g cr to your account.|n")
        lines.append(f"Remaining balance: |y{caller.db.credits:,}|n cr.")
        caller.msg("\n".join(lines))


class CmdLicenseSite(Command):
    """
    Register an extraction license for your mining site.

    Usage:
      licensesite
      licensesite upgrade

    Levels:
      1 — Standard license  (2,000 cr):  enables market-rate selling;
          5 % extraction tax per cycle deposited to the treasury.
      2 — Certified license (8,000 cr):  preferred-buyer status;
          5 % extraction tax (no increase — certification reduces other costs).

    Unlicensed operation restricts ore selling to base-price depots only.
    """

    key = "licensesite"
    aliases = ["mininglicense", "registerclaim"]
    help_category = "Mining"

    def func(self):
        from typeclasses.mining import LICENSE_COST, LICENSE_TAX_RATE_DEFAULT
        from typeclasses.economy import get_economy

        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return

        current_level = int(site.db.license_level or 0)
        if current_level >= 2:
            caller.msg(f"|w{site.key}|n already holds a Certified license (level 2).")
            return

        target_level = current_level + 1
        cost = LICENSE_COST.get(target_level, 0)

        econ = get_economy(create_missing=True)
        acct = econ.get_character_account(caller)
        econ.ensure_account(acct, opening_balance=int(caller.db.credits or 0))
        balance = econ.get_balance(acct)

        if balance < cost:
            caller.msg(
                f"License level {target_level} costs |y{cost:,}|n cr. "
                f"You have |y{balance:,}|n cr — need |r{cost - balance:,}|n more."
            )
            return

        econ.withdraw(acct, cost, memo=f"Mining license L{target_level}: {site.key}")
        econ.deposit(
            econ.get_treasury_account("alpha-prime"),
            cost,
            memo=f"License fee from {caller.key}",
        )
        caller.db.credits = econ.get_balance(acct)
        site.db.license_level = target_level
        site.db.tax_rate = LICENSE_TAX_RATE_DEFAULT

        level_names = {1: "Standard", 2: "Certified"}
        caller.msg(
            f"|g{level_names[target_level]} mining license registered for |w{site.key}|n.|n "
            f"Cost: |y{cost:,}|n cr.  Extraction tax: |y{int(LICENSE_TAX_RATE_DEFAULT * 100)}%|n/cycle."
        )


class CmdSetRig(Command):
    """
    Tune a rig's operating settings.

    Usage:
      setrig <field> <value>

    Fields and valid values:
      mode            balanced | selective | overdrive
      power_level     low | normal | high
      target_family   metals | gems | mixed
      purity_cutoff   low | medium | high
      maintenance_level  low | standard | premium

    You must be standing at the site where the rig is installed and own
    the site.  Changes take effect on the next production cycle.

    Effects summary:
      mode balanced    — normal output, normal wear
      mode selective   — 75 % output, 80 % wear; respects target_family/purity
      mode overdrive   — 140 % output, 200 % wear; higher breakdown risk
      power low        — 70 % output, 60 % wear
      power high       — 130 % output, 150 % wear
      maintenance low  — 150 % wear rate, 8 % base breakdown chance/cycle
      maintenance premium — 60 % wear rate, 1 % base breakdown chance/cycle
    """

    key = "setrig"
    aliases = ["rigset", "configrig"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        args = self.args.strip().split(None, 1)
        if len(args) < 2:
            caller.msg(
                "Usage: setrig <field> <value>\n"
                "Fields: mode, power_level, target_family, purity_cutoff, maintenance_level"
            )
            return

        field, value = args[0].lower(), args[1].lower()

        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return

        rig = site.db.active_rig
        if not rig:
            caller.msg(f"|w{site.key}|n has no installed rig.")
            return

        ok, msg = rig.set_option(field, value)
        if ok:
            caller.msg(f"|w{rig.key}|n — {msg}")
        else:
            caller.msg(f"|r{msg}|n")


class CmdRepairRig(Command):
    """
    Repair a broken or worn mining rig.

    Usage:
      repairrig

    Resets the rig's wear to 0 and restores it to operational status.
    You must be at the site where the rig is installed and own the site.

    In Pass 3 this command will require a repair kit or credit cost.
    """

    key = "repairrig"
    aliases = ["fixrig", "maintainrig"]
    help_category = "Mining"

    def func(self):
        caller = self.caller
        site = _find_site_in_room(caller)
        if not site:
            caller.msg("There is no mining site here.")
            return
        if not site.db.is_claimed or site.db.owner != caller:
            caller.msg("You do not own this site.")
            return

        rig = site.db.active_rig
        if not rig:
            caller.msg(f"|w{site.key}|n has no installed rig to repair.")
            return

        was_broken = not rig.db.is_operational
        old_wear = int(float(getattr(rig.db, "wear", 0.0) or 0.0) * 100)
        rig.repair()

        if was_broken:
            caller.msg(
                f"|w{rig.key}|n repaired and back online. "
                f"Wear reset from {old_wear}% to 0%."
            )
            # Reschedule next cycle now that the rig is operational again
            if site.db.linked_storage and not site.db.next_cycle_at:
                site.schedule_next_cycle()
                caller.msg("Production rescheduled — next cycle in 12 hours.")
        else:
            caller.msg(
                f"|w{rig.key}|n serviced. Wear reset from {old_wear}% to 0%."
            )


class CmdAvailableClaims(Command):
    """
    List unclaimed mining sites that can be purchased as part of a mining package.

    Usage:
      availableclaims
      claims

    Shows each unclaimed MiningSite. Buy a package at Mining Outfitters to
    receive a random claim, then |wdeploymine <package> <claim>|n.
    """

    key = "availableclaims"
    aliases = ["claims"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        from evennia import search_tag

        sites = search_tag("mining_site", category="mining")
        unclaimed = [s for s in sites if not getattr(s.db, "is_claimed", False)]

        if not unclaimed:
            self.caller.msg("There are no unclaimed mining sites available at this time.")
            return

        lines = ["|wAvailable Mining Claims:|n"]
        lines.append("|x" + "-" * 52 + "|n")
        for site in unclaimed:
            room = site.location
            room_name = room.key if room else "unknown location"
            deposit = site.db.deposit or {}
            comp = deposit.get("composition", {})
            families = ", ".join(comp.keys()) if comp else "unknown"
            richness = float(deposit.get("richness", 0.0))
            if richness >= 0.85:
                richness_label = "|gRich|n"
            elif richness >= 0.60:
                richness_label = "|yModerate|n"
            else:
                richness_label = "|rLean|n"
            hazard = float(site.db.hazard_level or 0.0)
            if hazard <= 0.20:
                hazard_label = "|gLow|n"
            elif hazard <= 0.50:
                hazard_label = "|yMedium|n"
            else:
                hazard_label = "|rHigh|n"
            lines.append(
                f"  |c{room_name}|n  ({richness_label} deposit, {hazard_label} hazard)\n"
                f"    Resources: {families}"
            )
        lines.append("|x" + "-" * 52 + "|n")
        lines.append("Buy a package at Mining Outfitters for a random claim, then |wdeploymine <package> <claim>|n")
        self.caller.msg("\n".join(lines))


def _find_mining_package_in_inventory(caller, query):
    """Find a mining package in caller's inventory by name or id."""
    if not query or not query.strip():
        return None
    q = query.strip().lower()
    for obj in caller.contents:
        if not obj.tags.has("mining_package", category="mining"):
            continue
        if q in (obj.key or "").lower():
            return obj
        if str(obj.id) == q:
            return obj
    return None


def _find_claim_in_inventory(caller, query):
    """Find a mining claim in caller's inventory by name or id."""
    if not query or not query.strip():
        return None
    q = query.strip().lower()
    for obj in caller.contents:
        if not obj.tags.has("mining_claim", category="mining"):
            continue
        if q in (obj.key or "").lower():
            return obj
        if str(obj.id) == q:
            return obj
    return None


def _find_owned_site_by_query(caller, query):
    """Find an owned MiningSite by room/site name match."""
    if not query or not query.strip():
        return None
    q = query.strip().lower()
    for site in _find_owned_sites(caller):
        if not site or not getattr(site, "db", None):
            continue
        site_key = (site.key or "").lower()
        room_key = (site.location.key if site.location else "").lower()
        if q in site_key or q in room_key:
            return site
    return None


class CmdDeployMine(Command):
    """
    Deploy a mining package at a claim you own.

    Usage:
      deploymine <package> <claim>

    Consumes both the package and the claim. Buy packages at Mining Outfitters
    to receive a random claim. Use |wavailableclaims|n to see unclaimed sites.
    """

    key = "deploymine"
    aliases = ["deploypackage", "deploy"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: deploymine <package> <claim>")
            return

        parts = args.split(None, 1)
        package_query = parts[0] if parts else ""
        claim_query = parts[1].strip() if len(parts) > 1 else ""

        if not claim_query:
            caller.msg(
                "Usage: |wdeploymine <package> <claim>|n — you need a claim from a package purchase."
            )
            return

        package = _find_mining_package_in_inventory(caller, package_query)
        if not package:
            caller.msg(f"No mining package matching '{package_query}' in your inventory.")
            return

        claim = _find_claim_in_inventory(caller, claim_query)
        if not claim:
            caller.msg(f"No mining claim matching '{claim_query}' in your inventory.")
            return

        from typeclasses.packages import deploy_package_from_inventory

        success, msg = deploy_package_from_inventory(caller, package, claim)
        if success:
            caller.msg(msg)
        else:
            caller.msg(f"|r{msg}|n")


class CmdUndeployMine(Command):
    """
    Pack up an owned mine and return it as a deployable package to inventory.

    Usage:
      undeploymine [site]

    Full teardown: rig, storage, hauler removed; site freed. A fresh package
    is returned to your inventory.
    """

    key = "undeploymine"
    aliases = ["undeploy", "packmine"]
    locks = "cmd:all()"
    help_category = "Mining"

    def func(self):
        caller = self.caller
        query = (self.args or "").strip()
        site = None
        if query:
            site = _find_owned_site_by_query(caller, query)
        if not site:
            site = _find_site_in_room(caller)
            if site and getattr(site.db, "is_claimed", False) and site.db.owner == caller:
                pass
            else:
                site = None
        if not site:
            if query:
                caller.msg(f"You do not own a mine matching '{query}'.")
            else:
                caller.msg(
                    "Usage: |wundeploymine [site]|n — specify a site or stand in your mine's room."
                )
            return

        from typeclasses.packages import undeploy_mine_to_package

        success, msg, _pkg = undeploy_mine_to_package(caller, site)
        if success:
            caller.msg(msg)
        else:
            caller.msg(f"|r{msg}|n")
