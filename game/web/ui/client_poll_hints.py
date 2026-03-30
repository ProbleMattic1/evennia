"""
Suggested web client polling intervals in milliseconds.

Keep keys in sync with frontend ``UI_REFRESH_MS`` / ``ClientPollHints``.
Tune here to reduce portal load during long-running worlds without redeploying the Next app.
"""

CLIENT_POLL_HINTS_MS = {
    "controlSurface": 15_000,
    "postDeadlinePoll": 15_000,
    "marketSnapshot": 30_000,
    "worldGraph": 45_000,
    "msgStream": 3_000,
}
