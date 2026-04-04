from __future__ import annotations

from datetime import timedelta
from typing import Any

from evennia import search_script
from evennia.scripts.scripts import DefaultScript

from world.time import parse_iso, to_iso, utc_now

SEED_QUEUE_MAX = 1000
DEFAULT_TTL_SECONDS = 6 * 3600


class MissionSeedsScript(DefaultScript):
    """
    Global feed of story opportunities produced by world simulation.

    Seeds are not missions themselves. They are time-limited world events that
    can unlock one or more mission opportunities for individual characters.
    """

    def at_script_creation(self):
        self.key = "mission_seeds"
        self.desc = "Global story seed registry for mission opportunities."
        self.interval = 0
        self.persistent = True
        self.db.rows = []
        self.db.next_id = 1

    def _next_id(self) -> int:
        nid = int(self.db.next_id or 1)
        self.db.next_id = nid + 1
        return nid

    def enqueue(
        self,
        *,
        kind: str,
        seed_id: str,
        source_key: str,
        title: str = "",
        summary: str = "",
        payload: dict[str, Any] | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, Any]:
        """
        Create or refresh a global story seed.

        Dedupe is by (kind, source_key). If the same source fires again during
        its lifetime, refresh the existing record instead of adding duplicates.
        """
        now = utc_now()
        expires_at = now + timedelta(seconds=max(60, int(ttl_seconds or DEFAULT_TTL_SECONDS)))

        rows = [dict(row) for row in list(self.db.rows or [])]
        for row in rows:
            if row.get("kind") == kind and row.get("sourceKey") == source_key:
                row["seedId"] = seed_id
                row["title"] = title
                row["summary"] = summary
                row["payload"] = dict(payload or {})
                row["createdAt"] = to_iso(now)
                row["expiresAt"] = to_iso(expires_at)
                self.db.rows = rows[-SEED_QUEUE_MAX:]
                return row

        row = {
            "id": f"seed-{self._next_id()}",
            "kind": str(kind or "").strip().lower(),
            "seedId": str(seed_id or "").strip(),
            "sourceKey": str(source_key or "").strip(),
            "title": str(title or "").strip(),
            "summary": str(summary or "").strip(),
            "payload": dict(payload or {}),
            "createdAt": to_iso(now),
            "expiresAt": to_iso(expires_at),
        }
        rows.append(row)
        self.db.rows = rows[-SEED_QUEUE_MAX:]
        return row

    def live_rows(self, limit: int = 200) -> list[dict[str, Any]]:
        now = utc_now()
        live = []
        changed = False
        for row in list(self.db.rows or []):
            expires_at = parse_iso(row.get("expiresAt"))
            if expires_at and expires_at < now:
                changed = True
                continue
            live.append(dict(row))
        if changed:
            self.db.rows = live[-SEED_QUEUE_MAX:]
        return live[-max(1, int(limit or 200)) :]


def get_mission_seeds_script(create_missing: bool = True) -> MissionSeedsScript | None:
    from evennia import GLOBAL_SCRIPTS

    script = GLOBAL_SCRIPTS.get("mission_seeds")
    if script:
        return script
    found = search_script("mission_seeds")
    if found:
        return found[0]
    if not create_missing:
        return None
    raise RuntimeError(
        "mission_seeds global script missing. Add it to server.conf.settings.GLOBAL_SCRIPTS."
    )


def enqueue_mission_seed(**kwargs) -> dict[str, Any] | None:
    script = get_mission_seeds_script(create_missing=True)
    if not script:
        return None
    return script.enqueue(**kwargs)
