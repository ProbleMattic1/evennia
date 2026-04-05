"""Log slow /ui/* requests for performance regression tracking."""

from __future__ import annotations

import logging
import time

log = logging.getLogger("aurnom.ui.slow")

SLOW_UI_MS = 2000.0


class SlowUiRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = getattr(request, "path", "") or ""
        if not path.startswith("/ui/"):
            return self.get_response(request)
        t0 = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if elapsed_ms >= SLOW_UI_MS:
            log.warning(
                "slow_ui path=%s method=%s ms=%.0f",
                path,
                getattr(request, "method", "?"),
                elapsed_ms,
            )
        return response
