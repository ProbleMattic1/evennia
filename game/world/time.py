"""
Universal wall-clock time for the game server.

- Authority: real UTC (datetime with tzinfo=UTC or epoch seconds).
- Alignment: periods are seconds, snapped to Unix epoch (same grid worldwide).
- Features (mining, haulers, daily resets) import this; they do not own time math.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc

# Common periods (seconds). Add more as needed; subsystems can pass literals too.
SECOND = 1
MINUTE = 60
HOUR = 3600
DAY = 86400
MINING_DELIVERY_PERIOD = 30 * MINUTE  # 1800 s = 30 min; change to 3 * HOUR before live launch

# Flora production grid (epoch-aligned UTC). Hauler pickup uses FLORA_HAULER_PICKUP_OFFSET_SEC
# (fixed 15 min after deposit / next boundary), not half of this period.
FLORA_DELIVERY_PERIOD = HOUR
FLORA_HAULER_PICKUP_OFFSET_SEC = 15 * MINUTE

# HaulerEngine wake: must be <= each pipeline's pickup offset (mining: half of 30m = 15m;
# flora: FLORA_HAULER_PICKUP_OFFSET_SEC) so a hauler due at deposit+offset is picked up
# within roughly one engine interval. 5 * MINUTE scales O(n) hauler scans; tune 300–900 as needed.
HAULER_ENGINE_INTERVAL_SEC = 5 * MINUTE


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_timestamp(dt: datetime) -> float:
    return dt.astimezone(UTC).timestamp()


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat()


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def floor_period(dt: datetime, period_seconds: int) -> datetime:
    """Start of the period slot containing dt (UTC, epoch-aligned)."""
    if period_seconds <= 0:
        raise ValueError("period_seconds must be positive")
    ts = utc_timestamp(dt)
    floored = math.floor(ts / period_seconds) * period_seconds
    return datetime.fromtimestamp(floored, tz=UTC)


def ceil_period(dt: datetime, period_seconds: int) -> datetime:
    """Earliest instant >= dt on the period grid (UTC, epoch-aligned)."""
    if period_seconds <= 0:
        raise ValueError("period_seconds must be positive")
    ts = utc_timestamp(dt)
    ceiled = math.ceil(ts / period_seconds) * period_seconds
    return datetime.fromtimestamp(ceiled, tz=UTC)


def next_period_after_completed(
    completed_boundary: datetime, period_seconds: int
) -> datetime:
    """Next due instant after a completed slot (stay on grid)."""
    return completed_boundary.astimezone(UTC) + timedelta(seconds=period_seconds)


def next_mining_delivery_slot_after(dt: datetime) -> datetime:
    """First instant at the next mining delivery grid boundary after the slot containing dt."""
    dt = dt.astimezone(UTC)
    slot_start = floor_period(dt, MINING_DELIVERY_PERIOD)
    return next_period_after_completed(slot_start, MINING_DELIVERY_PERIOD)


def next_mining_delivery_boundary_iso() -> str:
    """
    Next UTC epoch-aligned instant for the mining delivery grid (>= now), as ISO string.

    Matches the default branch of MiningSite.schedule_next_cycle(None), which uses
    ceil_period(utc_now(), MINING_DELIVERY_PERIOD). For web/UI when all mines share
    the same period without scanning objects.
    """
    iso = to_iso(ceil_period(utc_now(), MINING_DELIVERY_PERIOD))
    return iso if iso else ""


def current_mining_delivery_slot_start_iso() -> str:
    """Start of the UTC epoch-aligned mining delivery slot containing now."""
    iso = to_iso(floor_period(utc_now(), MINING_DELIVERY_PERIOD))
    return iso if iso else ""


def next_flora_delivery_boundary_iso() -> str:
    """
    Next UTC epoch-aligned instant for the flora delivery grid (>= now), as ISO string.

    Matches FloraSite.schedule_next_cycle(None): ceil_period(utc_now(), FLORA_DELIVERY_PERIOD).
    """
    iso = to_iso(ceil_period(utc_now(), FLORA_DELIVERY_PERIOD))
    return iso if iso else ""


def start_of_utc_day(dt: datetime) -> datetime:
    d = dt.astimezone(UTC).date()
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def utc_calendar_date(dt: datetime) -> date:
    return dt.astimezone(UTC).date()


def slot_index_in_utc_day(dt: datetime, period_seconds: int) -> int:
    """0 .. (DAY // period_seconds) - 1 within the UTC calendar day."""
    sod = start_of_utc_day(dt)
    elapsed = int((utc_timestamp(dt) - utc_timestamp(sod)))
    return elapsed // period_seconds
