"""
Hourly batch: roll named property incidents from staff/security quality (Phase 2).
"""

from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.property_incident_templates import (
    expire_property_incidents,
    pick_incident,
    template_by_id,
    trim_property_event_queue,
)
from world.time import utc_now

from typeclasses.mission_seeds import enqueue_mission_seed
from typeclasses.property_operation_registry import get_property_operation_registry
from typeclasses.scripts import Script
from typeclasses.system_alerts import enqueue_system_alert

MAX_EVENTS_PER_TICK = 100


def _apply_spawn_bonus(holding, amount: int) -> None:
    owner = holding.db.title_owner
    if not owner or amount <= 0:
        return
    from typeclasses.economy import get_economy

    econ = get_economy(create_missing=True)
    acct = econ.get_character_account(owner)
    econ.ensure_account(acct, opening_balance=int(owner.db.credits or 0))
    econ.deposit(acct, int(amount), memo=f"Property incident bonus ({holding.key})")
    owner.db.credits = econ.get_balance(acct)


def _maybe_enqueue_system_alert(holding, record: dict) -> None:
    sev = record.get("severity") or "info"
    tmpl = template_by_id(record.get("template_id") or "")
    should = sev in ("warning", "critical")
    if tmpl and tmpl.get("broadcast"):
        should = True
    if not should:
        return
    title = record.get("title") or "Property incident"
    summary = record.get("summary") or ""
    detail = f"{summary} (Parcel: {holding.key})"
    enqueue_system_alert(
        severity=sev if sev in ("warning", "critical", "info") else "info",
        category="property",
        title=title,
        detail=detail,
        source=f"holding:{holding.id}",
        dedupe_key=f"property-incident:{record.get('id')}",
    )


class PropertyEventsEngine(Script):
    def at_script_creation(self):
        self.key = "property_events_engine"
        self.desc = "Property holding named incident rolls (staff/security scaled)."
        self.persistent = True
        self.interval = 3600
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self):
        reg = get_property_operation_registry(create_missing=False)
        if not reg:
            return
        ids = list(reg.db.active_holding_ids or [])[:MAX_EVENTS_PER_TICK]
        now = utc_now()
        for obj in ObjectDB.objects.filter(id__in=ids):
            if not obj.tags.has("property_holding", category="realty"):
                continue
            self._tick_holding(obj, now)

    def _tick_holding(self, holding, now):
        expire_property_incidents(holding, now)
        rolled = pick_incident(holding, now)
        if not rolled:
            return
        record, spawn_bonus = rolled
        q = list(holding.db.event_queue or [])
        q.append(record)
        holding.db.event_queue = trim_property_event_queue(q)
        if spawn_bonus > 0:
            _apply_spawn_bonus(holding, spawn_bonus)
        _maybe_enqueue_system_alert(holding, record)
        enqueue_mission_seed(
            kind="incident",
            seed_id=record.get("template_id") or "",
            source_key=f"property-incident:{record.get('id')}",
            title=record.get("title") or "Property incident",
            summary=record.get("summary") or "",
            payload={
                "holdingId": holding.id,
                "holdingKey": holding.key,
                "severity": record.get("severity"),
            },
            ttl_seconds=12 * 3600,
        )
        logger.log_info(
            f"[property_events] holding={holding.key} "
            f"template={record.get('template_id')} id={record.get('id')}"
        )
