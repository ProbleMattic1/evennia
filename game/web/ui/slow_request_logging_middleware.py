"""Log slow /ui/* requests for performance regression tracking."""

from __future__ import annotations

import logging
import os
import time

log = logging.getLogger("aurnom.ui.slow")

_DEFAULT_SLOW_MS = 2000.0


def _base_slow_ui_ms() -> float:
    raw = os.environ.get("AURNOM_SLOW_UI_LOG_MS", "").strip()
    if not raw:
        return _DEFAULT_SLOW_MS
    try:
        v = float(raw)
    except ValueError:
        return _DEFAULT_SLOW_MS
    return v if v > 0 else _DEFAULT_SLOW_MS


def _slow_threshold_ms(request, path: str) -> tuple[float, str]:
    """
    Return (threshold_ms, extra_log_suffix).
    msg-stream long-poll uses block_ms; wall time near block_ms is expected, not a regression.
    """
    base = _base_slow_ui_ms()
    p = path.rstrip("/") or "/"
    if p != "/ui/msg-stream" and not p.startswith("/ui/msg-stream/"):
        return base, ""
    try:
        block_ms = int(request.GET.get("block_ms", 0))
    except (TypeError, ValueError):
        block_ms = 0
    block_ms = max(0, min(block_ms, 25_000))
    if block_ms <= 0:
        return base, ""
    # Log only if handling exceeds requested block plus slack (poll interval granularity).
    thr = max(base, float(block_ms) + 1500.0)
    return thr, f" block_ms={block_ms}"


class SlowUiRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = getattr(request, "path", "") or ""
        if not path.startswith("/ui/"):
            return self.get_response(request)
        threshold, extra_suffix = _slow_threshold_ms(request, path)
        t0 = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if elapsed_ms >= threshold:
            log.warning(
                "slow_ui path=%s method=%s ms=%.0f%s",
                path,
                getattr(request, "method", "?"),
                elapsed_ms,
                extra_suffix,
            )
        return response
