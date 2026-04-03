"""Apply point-offer effects after purchase validation and point debit."""

from __future__ import annotations

from typing import Any, Callable

from evennia.utils import logger

from world.mission_loader import get_mission_template
from world.point_store.perk_defs_loader import get_perk_def
from typeclasses.refining import REFINING_RECIPES

EffectFn = Callable[[Any, dict[str, Any]], None]

_REGISTRY: dict[str, EffectFn] = {}


def register_effect(name: str, fn: EffectFn) -> None:
    _REGISTRY[str(name).strip().lower()] = fn


def apply_effect(handler: Any, effect: dict[str, Any]) -> None:
    """Dispatch on effect['type']. Raises ValueError on unknown or invalid effect."""
    if not isinstance(effect, dict):
        raise ValueError("effect must be dict")
    kind = str(effect.get("type") or "").strip().lower()
    if kind == "compound":
        steps = effect.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("compound effect requires non-empty steps list")
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(f"compound step {i} must be dict")
            apply_effect(handler, step)
        return
    fn = _REGISTRY.get(kind)
    if not fn:
        raise ValueError(f"unknown point-offer effect type {kind!r}")
    fn(handler, effect)


def _trait_bump(handler: Any, effect: dict[str, Any]) -> None:
    char = handler.obj
    which = str(effect.get("handler") or "skills").strip().lower()
    trait_key = str(effect.get("traitKey") or "").strip()
    if not trait_key:
        raise ValueError("trait_bump requires traitKey")
    th = char.stats if which == "stats" else char.skills
    char.ensure_default_rpg_traits()
    trait = th.get(trait_key)
    if trait is None:
        raise ValueError(f"unknown trait key {trait_key!r} on {which}")
    if not any(k in effect for k in ("baseDelta", "modDelta", "multDelta")):
        raise ValueError("trait_bump requires at least one of baseDelta, modDelta, multDelta")
    if "baseDelta" in effect:
        trait.base += int(effect["baseDelta"])
    if "modDelta" in effect:
        trait.mod += int(effect["modDelta"])
    if "multDelta" in effect:
        trait.mult = float(trait.mult) + float(effect["multDelta"])
    logger.log_info(f"[point_store] trait_bump {char.key} {which}.{trait_key}")


def _perk_slot(handler: Any, effect: dict[str, Any]) -> None:
    delta = int(effect.get("delta") or 0)
    if delta <= 0:
        raise ValueError("perk_slot requires positive delta")
    handler._bump_perk_slots(delta)


def _grant_perk(handler: Any, effect: dict[str, Any]) -> None:
    pid = str(effect.get("perkId") or "").strip()
    if not pid:
        raise ValueError("grant_perk requires perkId")
    if not get_perk_def(pid):
        raise ValueError(f"unknown perk id {pid!r} (not in perk_defs)")
    handler._grant_and_try_equip_perk(pid)


def _mission_offer_fixed(handler: Any, effect: dict[str, Any]) -> None:
    tid = str(effect.get("templateId") or "").strip()
    if not tid:
        raise ValueError("mission_offer requires templateId")
    tmpl = get_mission_template(tid)
    if not tmpl:
        raise ValueError(f"unknown mission template {tid!r}")
    char = handler.obj
    offer_id = str(effect.get("sourceOfferId") or getattr(handler, "_effect_offer_id", "") or "").strip()
    sk = f"point_store:{offer_id or 'unknown'}:{tid}"
    char.missions._offer_template(
        tmpl,
        source={"kind": "alert", "sourceKey": sk},
    )


def _unlock_tags(handler: Any, effect: dict[str, Any]) -> None:
    tags = [str(t).strip() for t in list(effect.get("tags") or []) if str(t).strip()]
    if not tags:
        raise ValueError("unlock_tags requires non-empty tags")
    handler._add_unlock_tags(tags)


def _license_tier(handler: Any, effect: dict[str, Any]) -> None:
    lk = str(effect.get("licenseKey") or "").strip()
    if not lk:
        raise ValueError("license_tier requires licenseKey")
    tier = int(effect.get("tier") or 0)
    if tier < 1:
        raise ValueError("license_tier tier must be >= 1")
    handler._set_license_tier_floor(lk, tier)


def _refining_recipe_unlock(handler: Any, effect: dict[str, Any]) -> None:
    keys = [str(k).strip() for k in list(effect.get("recipeKeys") or []) if str(k).strip()]
    if not keys:
        raise ValueError("refining_recipe_unlock requires recipeKeys")
    for rk in keys:
        if rk not in REFINING_RECIPES:
            raise ValueError(f"unknown refining recipe key {rk!r}")
    handler._unlock_refining_recipes(keys)


def _register_builtins() -> None:
    register_effect("trait_bump", _trait_bump)
    register_effect("perk_slot", _perk_slot)
    register_effect("grant_perk", _grant_perk)
    register_effect("mission_offer", _mission_offer_fixed)
    register_effect("unlock_tags", _unlock_tags)
    register_effect("license_tier", _license_tier)
    register_effect("refining_recipe_unlock", _refining_recipe_unlock)


_register_builtins()
