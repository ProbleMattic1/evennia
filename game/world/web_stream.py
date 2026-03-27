"""Web UI message stream metadata contract."""

WEB_STREAM_OPTIONS_KEY = "web_stream"

DEFAULT_WEB_STREAM_META = {
    "eventType": "emit",
    "interactionKey": None,
    "speakerKey": None,
    "destinationRoomKey": None,
}


def normalize_web_stream_meta(partial: dict) -> dict:
    merged = dict(DEFAULT_WEB_STREAM_META)
    merged.update(partial)
    return merged
