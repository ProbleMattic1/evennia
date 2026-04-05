"""
In-character time helpers (Evennia ``evennia.utils.gametime``).

Configure ``TIME_GAME_EPOCH`` and ``TIME_FACTOR`` in ``server.conf.settings``.

**Two clocks (intentional):**
- **In-character** narrative time: this module and ``WorldClockScript`` / world engines.
- **Wall / grid UTC** for industry schedules (mining windows, hauler dispatch): ``world.time``
  (``utc_now``, epoch-aligned periods). Do not replace those with gametime; they are separate
  contracts already documented there.
"""

from __future__ import annotations

from datetime import datetime, timezone


def game_timestamp(*, absolute: bool = True) -> float:
    from evennia.utils import gametime as gt

    return float(gt.gametime(absolute=absolute))


def game_datetime_utc(*, absolute: bool = True) -> datetime:
    return datetime.fromtimestamp(game_timestamp(absolute=absolute), tz=timezone.utc)


def compute_clock_snapshot() -> dict:
    """
    Serializable snapshot for engines, web UI, and room ticks.

    Keys are stable for API consumers.
    """
    dt = game_datetime_utc(absolute=True)
    hour = int(dt.hour)
    month = int(dt.month)

    if 5 <= hour < 8:
        day_phase = "dawn"
    elif 8 <= hour < 17:
        day_phase = "day"
    elif 17 <= hour < 21:
        day_phase = "dusk"
    else:
        day_phase = "night"

    if month in (12, 1, 2):
        season = "winter"
    elif month in (3, 4, 5):
        season = "spring"
    elif month in (6, 7, 8):
        season = "summer"
    else:
        season = "autumn"

    ambient_w = {"dawn": 0.95, "day": 1.0, "dusk": 1.05, "night": 0.88}
    crime_w = {"dawn": 1.0, "day": 0.92, "dusk": 1.08, "night": 1.12}
    battle_w = {"dawn": 1.02, "day": 1.0, "dusk": 1.0, "night": 1.06}

    return {
        "game_timestamp": game_timestamp(absolute=True),
        "iso_utc": dt.isoformat(),
        "hour": hour,
        "month": month,
        "day_of_month": int(dt.day),
        "day_phase": day_phase,
        "season": season,
        "ambient_weight": float(ambient_w[day_phase]),
        "crime_weight": float(crime_w[day_phase]),
        "battlespace_weight": float(battle_w[day_phase]),
    }
