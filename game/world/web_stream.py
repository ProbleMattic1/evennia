"""Web UI message stream metadata contract.

Optional billboard keys (for LocationBanner / msg-stream):
  billboardHeadline — non-empty str shows a timed strip when room matches
  billboardSeverity — "info" | "warn" | "alert"
  billboardTtlSec — float/int seconds visible (default interpreted client-side)
  billboardRoomKey — if set, only show when player current room equals this key
"""

WEB_STREAM_OPTIONS_KEY = "web_stream"

DEFAULT_WEB_STREAM_META = {
    "eventType": "emit",
    "interactionKey": None,
    "speakerKey": None,
    "destinationRoomKey": None,
    "surface": None,
    "billboardHeadline": None,
    "billboardSeverity": None,
    "billboardTtlSec": None,
    "billboardRoomKey": None,
}


def normalize_web_stream_meta(partial: dict) -> dict:
    merged = dict(DEFAULT_WEB_STREAM_META)
    merged.update(partial)
    return merged
