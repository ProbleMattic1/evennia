from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from world.models import HaulerDispatchRow
from world.time import MAX_HAULERS_PER_ENGINE_TICK, parse_iso


def _dt_from_hauler_iso(iso_str: str | None) -> datetime | None:
    dt = parse_iso(iso_str)
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, dt_timezone.utc)
    return dt


def sync_hauler_dispatch_row(hauler) -> None:
    """Persist dispatch index for this hauler from hauler.db.hauler_next_cycle_at."""
    dt = _dt_from_hauler_iso(getattr(hauler.db, "hauler_next_cycle_at", None))
    if dt is None:
        return
    HaulerDispatchRow.objects.update_or_create(
        objectdb_id=hauler.id,
        defaults={"next_run": dt},
    )


def delete_hauler_dispatch_row(hauler_or_id) -> None:
    pk = hauler_or_id.id if hasattr(hauler_or_id, "id") else int(hauler_or_id)
    HaulerDispatchRow.objects.filter(objectdb_id=pk).delete()


def fetch_due_hauler_ids(*, now=None, limit: int | None = None) -> list[int]:
    now = now or timezone.now()
    lim = MAX_HAULERS_PER_ENGINE_TICK if limit is None else limit
    return list(
        HaulerDispatchRow.objects.filter(next_run__lte=now)
        .order_by("next_run")
        .values_list("objectdb_id", flat=True)[:lim]
    )
