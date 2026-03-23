"""
at_initial_setup runs exactly once on a fresh database.

All world data seeding is handled in at_server_cold_start (at_server_startstop.py)
so that it runs reliably on every cold start, not just the first boot.
"""


def at_initial_setup():
    pass
