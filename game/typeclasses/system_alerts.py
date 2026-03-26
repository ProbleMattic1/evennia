"""
Persistent system alerts queue with per-account acknowledgements.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from evennia import create_script, search_script
from evennia.scripts.scripts import DefaultScript


ALERT_SEVERITIES = {"critical", "warning", "info"}
ALERT_CATEGORIES = {"mining", "market", "system", "world", "district", "property", "shipping"}


class SystemAlertsScript(DefaultScript):
    """Persistent event queue + per-account acknowledgements."""

    def at_script_creation(self):
        self.key = "system_alerts"
        self.desc = "Global system alerts queue with persisted acknowledgements."
        self.interval = 0
        self.persistent = True
        self.db.events = []
        self.db.acked_by_account = {}  # { "<account_id>": [alert_id, ...] }

    def _next_id(self) -> int:
        return int(self.db.next_id or 1)

    def _set_next_id(self, value: int) -> None:
        self.db.next_id = int(value)

    def enqueue(
        self,
        *,
        severity: str,
        category: str,
        title: str,
        detail: str = "",
        source: str = "",
        dedupe_key: str = "",
    ) -> dict[str, Any]:
        if severity not in ALERT_SEVERITIES:
            severity = "info"
        if category not in ALERT_CATEGORIES:
            category = "system"

        now = timezone.now()
        aid = self._next_id()
        self._set_next_id(aid + 1)

        row = {
            "id": f"alert-{aid}",
            "severity": severity,
            "category": category,
            "title": title,
            "detail": detail,
            "source": source,
            "dedupeKey": dedupe_key or None,
            "createdAt": now.isoformat(),
        }
        events = list(self.db.events or [])
        events.append(row)
        self.db.events = events[-1000:]
        return row

    def ack_for_account(self, account_id: int, alert_id: str) -> bool:
        key = str(int(account_id))
        ack_map = dict(self.db.acked_by_account or {})
        acked = set(ack_map.get(key, []))
        acked.add(alert_id)
        ack_map[key] = sorted(acked)
        self.db.acked_by_account = ack_map
        return True

    def get_visible_for_account(self, account_id: int, limit: int = 200) -> list[dict[str, Any]]:
        key = str(int(account_id))
        acked = set((self.db.acked_by_account or {}).get(key, []))
        events = [dict(e) for e in list(self.db.events or []) if e.get("id") not in acked]
        return events[-limit:]


def get_system_alerts_script(create_missing: bool = True) -> SystemAlertsScript | None:
    found = search_script("system_alerts")
    if found:
        return found[0]
    if not create_missing:
        return None
    return create_script("typeclasses.system_alerts.SystemAlertsScript", key="system_alerts")


def enqueue_system_alert(**kwargs) -> dict[str, Any] | None:
    script = get_system_alerts_script(create_missing=True)
    if not script:
        return None
    return script.enqueue(**kwargs)
