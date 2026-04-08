"""
One-shot Django `/ui/*` preflight on the Evennia WSGI thread pool.

The first HTTP request through Twisted's WSGI pipeline pays a large one-time cost
(URLConf resolution, middleware chain, heavy view imports). Running synthetic GETs
via Django's test client inside the same LockableThreadPool as production WSGI
warms that cost off the critical path of the first browser/API call, without
blocking the reactor or AMP handlers.

Scheduled from server.conf.at_server_startstop.at_server_start (after DB/scripts).
"""

from __future__ import annotations

import logging
import time
import traceback

log = logging.getLogger("aurnom.wsgi_preflight")


def schedule_ui_wsgi_preflight() -> None:
    """
    Queue background warm on the game's WSGI thread pool. Non-blocking on the
    Twisted thread that runs at_server_start.
    """
    from django.conf import settings

    if not getattr(settings, "WEBSERVER_ENABLED", True):
        return

    try:
        import evennia
    except Exception:
        return

    svc = getattr(evennia, "EVENNIA_SERVER_SERVICE", None)
    web_root = getattr(svc, "web_root", None) if svc is not None else None
    pool = getattr(web_root, "pool", None) if web_root is not None else None
    if pool is None:
        log.warning("UI WSGI preflight skipped: web_root or thread pool not present.")
        return

    print("[startup] UI WSGI preflight queued on web thread pool (non-blocking).")

    def _run_preflight() -> None:
        t0_wall = time.perf_counter()
        try:
            from django.test import Client

            client = Client(HTTP_HOST="127.0.0.1", enforce_csrf_checks=False)

            t_h = time.perf_counter()
            r_health = client.get("/ui/health")
            ms_health = (time.perf_counter() - t_h) * 1000.0

            t_c = time.perf_counter()
            r_cs = client.get("/ui/control-surface")
            ms_cs = (time.perf_counter() - t_c) * 1000.0

            ms_total = (time.perf_counter() - t0_wall) * 1000.0

            log.info(
                "wsgi_preflight_complete health_status=%s health_ms=%.0f "
                "control_surface_status=%s control_surface_ms=%.0f total_ms=%.0f",
                getattr(r_health, "status_code", None),
                ms_health,
                getattr(r_cs, "status_code", None),
                ms_cs,
                ms_total,
            )
            print(
                "[startup] UI WSGI preflight complete: "
                f"/ui/health={r_health.status_code} ({ms_health:.0f}ms) "
                f"/ui/control-surface={r_cs.status_code} ({ms_cs:.0f}ms) "
                f"total={ms_total:.0f}ms"
            )
        except Exception:
            log.exception("wsgi_preflight_failed")
            traceback.print_exc()

    pool.callInThread(_run_preflight)
