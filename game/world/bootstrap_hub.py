"""
Game hub: repurposes default room #2 (Evennia Limbo) as the NanoMegaPlex Promenade.

Must run before other world bootstraps that wire exits from the hub.

Called from server/conf/at_server_cold_start (at_server_startstop.py) on cold start.
Idempotent.
"""

HUB_ROOM_KEY = "NanoMegaPlex Promenade"

HUB_ROOM_DESC = (
    "The NanoMegaPlex Promenade — the largest and most popular multiplex in the sector. "
    "A vaulted gallery of storefronts, kiosks, transit links, and holo signage draws "
    "crowds from every worldline. Ship brokers, banks, and retail arcades all branch from here."
)


def get_hub_room():
    """
    Return the hub room (default #2 after bootstrap_hub), or None if missing.
    Prefer key match after rename; fall back to #2.
    """
    from evennia import search_object

    found = search_object(HUB_ROOM_KEY)
    if found:
        return found[0]
    found = search_object("#2")
    return found[0] if found else None


def bootstrap_hub():
    """Rename and describe #2 as the NanoMegaPlex Promenade (stable DEFAULT_HOME)."""
    from evennia import search_object

    found = search_object("#2")
    if not found:
        print("[hub] WARNING: #2 not found; DEFAULT_HOME / START_LOCATION may be invalid.")
        return

    room = found[0]
    room.key = HUB_ROOM_KEY
    room.db.desc = HUB_ROOM_DESC
    print(f"[hub] Hub ready: {HUB_ROOM_KEY} (#{room.id})")
