"""
Manufacturing — parcel workshops (fab bay / assembly cell).

Players must be in a property interior room whose db.holding_ref points at
their titled parcel. Workshops live on the holding next to structures.
"""

from commands.command import Command
from typeclasses.manufacturing import MANUFACTURED_CATALOG, MANUFACTURING_RECIPES, Workshop
from typeclasses.refining import REFINING_RECIPES


def _manufactured_display_name(key: str) -> str:
    return MANUFACTURED_CATALOG.get(key, {}).get("name", key)


def _resolve_holding(caller):
    loc = caller.location
    if not loc:
        return None, "You have no location."
    holding = getattr(loc.db, "holding_ref", None)
    if not holding:
        return None, "You must be on a parcel interior with a fabrication workshop."
    if getattr(holding.db, "title_owner", None) != caller:
        return None, "This is not your parcel."
    return holding, None


def _workshops_on_holding(holding):
    return [o for o in holding.contents if o.is_typeclass(Workshop, exact=False)]


def _pick_workshop(workshops, fragment: str | None):
    if not workshops:
        return None
    if not fragment:
        return workshops[0]
    frag = fragment.lower().strip()
    for w in workshops:
        bp = str(getattr(w.db, "blueprint_id", "") or "").lower()
        if frag in bp or frag in w.key.lower():
            return w
    return None


def _match_recipe_key(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    for key in MANUFACTURING_RECIPES:
        name = MANUFACTURING_RECIPES[key].get("name", key)
        if q == key or q in key.lower() or q in name.lower():
            return key
    return None


def _refined_sources_for_feed(holding, room, caller):
    """Portable processors (and titled refineries) on holding or parcel room."""
    seen = set()
    for parent in (holding, room):
        if not parent:
            continue
        for obj in parent.contents:
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            out = getattr(obj.db, "output_inventory", None) or {}
            if not out:
                continue
            if obj.tags.has("portable_processor", category="mining"):
                if getattr(obj.db, "owner", None) != caller:
                    continue
                yield obj
            elif obj.tags.has("refinery", category="mining") and getattr(
                obj.db, "owner", None
            ) == caller:
                yield obj


def _refined_sources_on_holding_only(holding, caller):
    """Portable processor / titled refinery output on the holding only (ignores caller.location)."""
    for obj in holding.contents:
        out = getattr(obj.db, "output_inventory", None) or {}
        if not out:
            continue
        if obj.tags.has("portable_processor", category="mining"):
            if getattr(obj.db, "owner", None) != caller:
                continue
            yield obj
        elif obj.tags.has("refinery", category="mining") and getattr(
            obj.db, "owner", None
        ) == caller:
            yield obj


def _withdraw_refined_units(source, product_key: str, units: float) -> float:
    out = dict(source.db.output_inventory or {})
    available = float(out.get(product_key, 0.0))
    if available <= 0:
        return 0.0
    take = round(min(float(units), available), 2)
    remaining = round(available - take, 2)
    if remaining <= 0:
        out.pop(product_key, None)
    else:
        out[product_key] = remaining
    source.db.output_inventory = out
    return take


class CmdWorkshopStatus(Command):
    """
    Show fabrication workshops on your current parcel.

    Usage:
      workshopstatus
      ws
    """

    key = "workshopstatus"
    aliases = ["ws"]
    help_category = "Manufacturing"

    def func(self):
        caller = self.caller
        holding, err = _resolve_holding(caller)
        if err:
            caller.msg(err)
            return
        workshops = _workshops_on_holding(holding)
        if not workshops:
            caller.msg("No workshop is installed on this parcel (fab bay or assembly cell).")
            return
        lines = ["|wParcel fabrication|n"]
        for w in workshops:
            bp = getattr(w.db, "blueprint_id", "") or "?"
            kind = getattr(w.db, "station_kind", "") or "?"
            lines.append(f"\n  |w{w.key}|n  ({bp}, {kind})")
            q = list(w.db.job_queue or [])
            lines.append(f"    Queue: {len(q)} job(s)")
            for j in q[:5]:
                rk = j.get("recipe_key", "?")
                name = MANUFACTURING_RECIPES.get(rk, {}).get("name", rk)
                lines.append(f"      → {name} × {j.get('runs', 0)}")
            if len(q) > 5:
                lines.append(f"      … +{len(q) - 5} more")
            ins = w.db.input_inventory or {}
            outs = w.db.output_inventory or {}
            if ins:
                lines.append("    Inputs:")
                for k, v in sorted(ins.items()):
                    nm = REFINING_RECIPES.get(k, {}).get("name", k)
                    lines.append(f"      {nm}: {v:.2f} u")
            else:
                lines.append("    Inputs: (empty)")
            if outs:
                lines.append("    Output:")
                for k, v in sorted(outs.items()):
                    nm = _manufactured_display_name(k)
                    lines.append(f"      {nm}: {v:.2f} u")
            else:
                lines.append("    Output: (empty)")
        caller.msg("\n".join(lines))


class CmdFeedFab(Command):
    """
    Move refined units from your portable processor (or titled refinery)
    on this parcel into the workshop input buffer.

    Usage:
      feedfab <refined product> <units> [workshop fragment]

    Example:
      feedfab steel 4
    """

    key = "feedfab"
    aliases = ["feedworkshop"]
    help_category = "Manufacturing"

    def func(self):
        caller = self.caller
        holding, err = _resolve_holding(caller)
        if err:
            caller.msg(err)
            return
        workshops = _workshops_on_holding(holding)
        if not workshops:
            caller.msg("No workshop on this parcel.")
            return

        parts = self.args.strip().split()
        if len(parts) < 2:
            caller.msg("Usage: feedfab <refined product> <units> [workshop]")
            return

        product_query = parts[0].lower()
        try:
            units = float(parts[1])
        except ValueError:
            caller.msg("Units must be a number.")
            return
        wfrag = parts[2] if len(parts) >= 3 else None

        if units <= 0:
            caller.msg("Units must be positive.")
            return

        matched_product = None
        for key in REFINING_RECIPES:
            name = REFINING_RECIPES[key].get("name", key)
            if product_query in key.lower() or product_query in name.lower():
                matched_product = key
                break
        if not matched_product:
            caller.msg(f"No refined product matching '{product_query}'.")
            return

        w = _pick_workshop(workshops, wfrag)
        if not w:
            caller.msg("No matching workshop.")
            return

        room = caller.location
        total_taken = 0.0
        for src in _refined_sources_for_feed(holding, room, caller):
            chunk = _withdraw_refined_units(src, matched_product, units - total_taken)
            if chunk > 0:
                fed = w.feed(matched_product, chunk)
                total_taken += fed
            if total_taken + 1e-6 >= units:
                break

        if total_taken <= 0:
            caller.msg(
                "No matching refined output found on this parcel "
                "(portable processor or your refinery output)."
            )
            return
        nm = REFINING_RECIPES[matched_product]["name"]
        caller.msg(f"Fed |w{total_taken:.2f}|n units of {nm} into |w{w.key}|n.")


class CmdQueueFab(Command):
    """
    Queue a manufacturing recipe at your parcel workshop.

    Usage:
      queuefab <recipe> [runs] [workshop fragment]

    Example:
      queuefab rig_service_kit 2
    """

    key = "queuefab"
    help_category = "Manufacturing"

    def func(self):
        caller = self.caller
        holding, err = _resolve_holding(caller)
        if err:
            caller.msg(err)
            return
        workshops = _workshops_on_holding(holding)
        if not workshops:
            caller.msg("No workshop on this parcel.")
            return

        parts = self.args.strip().split()
        if not parts:
            caller.msg("Usage: queuefab <recipe> [runs] [workshop]")
            return

        runs = 1
        if len(parts) >= 2 and parts[-1].isdigit():
            runs = max(1, int(parts.pop()))

        wfrag = None
        if len(parts) >= 2:
            wfrag = parts.pop()

        recipe_query = " ".join(parts).strip()
        rk = _match_recipe_key(recipe_query)
        if not rk:
            caller.msg(f"No manufacturing recipe matching '{recipe_query}'.")
            return

        w = _pick_workshop(workshops, wfrag)
        if not w:
            caller.msg("No matching workshop.")
            return

        try:
            w.queue_job(caller, rk, runs)
        except PermissionError as e:
            caller.msg(str(e))
            return
        except ValueError as e:
            caller.msg(str(e))
            return

        name = MANUFACTURING_RECIPES[rk]["name"]
        caller.msg(f"Queued |w{runs}|n × |w{name}|n at |w{w.key}|n.")


class CmdCollectFab(Command):
    """
    Sell manufactured output from your parcel workshop (commodity multiplier applies).

    Usage:
      collectfab
      collectfab <product fragment> [workshop fragment]
    """

    key = "collectfab"
    help_category = "Manufacturing"

    def func(self):
        caller = self.caller
        holding, err = _resolve_holding(caller)
        if err:
            caller.msg(err)
            return
        workshops = _workshops_on_holding(holding)
        if not workshops:
            caller.msg("No workshop on this parcel.")
            return

        parts = self.args.strip().split()
        w = None
        if len(parts) >= 2:
            trial = _pick_workshop(workshops, parts[-1])
            if trial is not None:
                parts.pop()
                w = trial
        if w is None:
            w = _pick_workshop(workshops, None)
        if not w:
            caller.msg("No matching workshop.")
            return

        outs = dict(w.db.output_inventory or {})
        if not outs:
            caller.msg("Output bin empty.")
            return

        if not parts:
            total = 0
            try:
                for pk in list(outs.keys()):
                    u, v = w.collect_manufactured(caller, pk, None)
                    total += v
            except PermissionError as e:
                caller.msg(str(e))
                return
            caller.msg(f"Credited |y{total:,}|n cr for manufactured goods.")
            return

        product_query = " ".join(parts).lower()
        matched = None
        for pk in outs:
            name = MANUFACTURED_CATALOG[pk]["name"]
            if product_query in pk.lower() or product_query in name.lower():
                matched = pk
                break
        if not matched:
            caller.msg("No matching product in output bin.")
            return
        try:
            u, v = w.collect_manufactured(caller, matched, None)
        except PermissionError as e:
            caller.msg(str(e))
            return
        caller.msg(f"Sold |w{u:.2f}|n units for |y{v:,}|n cr.")


class CmdProcessFab(Command):
    """
    Run one fabrication step immediately (process the next queued job if possible).

    Usage:
      processfab [workshop fragment]
    """

    key = "processfab"
    help_category = "Manufacturing"

    def func(self):
        caller = self.caller
        holding, err = _resolve_holding(caller)
        if err:
            caller.msg(err)
            return
        workshops = _workshops_on_holding(holding)
        if not workshops:
            caller.msg("No workshop on this parcel.")
            return

        wfrag = self.args.strip() or None
        w = _pick_workshop(workshops, wfrag)
        if not w:
            caller.msg("No matching workshop.")
            return
        if not w.access(caller, "control", default=False):
            caller.msg("Not your workshop.")
            return

        ok, msg = w.process_next_job()
        if ok:
            caller.msg(f"|g{msg}|n")
        else:
            caller.msg(f"|y{msg}|n")
