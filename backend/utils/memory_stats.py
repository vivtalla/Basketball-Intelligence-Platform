"""Sprint 100 (Stream D) — process + system memory snapshot.

Wraps psutil behind a small surface that the health endpoints call.  All
callers must tolerate `psutil` being unavailable (e.g. during test runs
where the dep isn't installed) — the helper returns
``{"error": "unavailable", ...}`` rather than raising.

Why this exists: today (2026-05-16) a gunicorn worker hit OOM on the
Hetzner CPX11 box (2 GB RAM).  We had no health-endpoint visibility into
RAM/swap pressure, so UptimeRobot only noticed once Cloudflare started
returning 522s.  These helpers feed `/api/health` and a dedicated
`/api/health/memory` endpoint with the numbers needed for proactive
alerting.
"""

from __future__ import annotations

from typing import Any, Dict

try:  # psutil is added in Sprint 100 (requirements.txt).
    import psutil  # type: ignore

    _PSUTIL_AVAILABLE = True
except Exception:  # pragma: no cover - defensive
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False


def get_memory_snapshot() -> Dict[str, Any]:
    """Return a single-point-in-time snapshot of process + system memory.

    Keys (when available):
      - ``process_rss_mb`` / ``process_vms_mb`` — gunicorn worker footprint
      - ``system_total_mb`` / ``system_available_mb`` / ``system_used_pct``
      - ``swap_total_mb`` / ``swap_used_mb`` / ``swap_used_pct``

    If psutil is not importable, returns ``{"error": "unavailable"}``.  If a
    metric raises mid-snapshot, that field is omitted; the rest of the
    snapshot is still returned so callers always get usable data.
    """
    if not _PSUTIL_AVAILABLE:
        return {"error": "unavailable"}

    snapshot: Dict[str, Any] = {}
    try:
        proc = psutil.Process()
        info = proc.memory_info()
        snapshot["process_rss_mb"] = round(info.rss / 1024 / 1024, 1)
        snapshot["process_vms_mb"] = round(info.vms / 1024 / 1024, 1)
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        vm = psutil.virtual_memory()
        snapshot["system_total_mb"] = round(vm.total / 1024 / 1024, 1)
        snapshot["system_available_mb"] = round(vm.available / 1024 / 1024, 1)
        snapshot["system_used_pct"] = round(vm.percent, 1)
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        swap = psutil.swap_memory()
        snapshot["swap_total_mb"] = round(swap.total / 1024 / 1024, 1)
        snapshot["swap_used_mb"] = round(swap.used / 1024 / 1024, 1)
        snapshot["swap_used_pct"] = round(swap.percent, 1)
    except Exception:  # pragma: no cover - defensive
        pass

    return snapshot


def classify_memory_status(snapshot: Dict[str, Any]) -> str:
    """Reduce a snapshot to ``ok`` | ``warning`` | ``critical``.

    Thresholds chosen to fire BEFORE the kernel OOM-kills (which on the
    CPX11 happens once swap is fully consumed).  ``critical`` is intended
    to page UptimeRobot.
    """
    if snapshot.get("error"):
        return "unknown"
    swap_pct = snapshot.get("swap_used_pct", 0) or 0
    sys_pct = snapshot.get("system_used_pct", 0) or 0
    if swap_pct > 85 or sys_pct > 95:
        return "critical"
    if swap_pct > 60 or sys_pct > 90:
        return "warning"
    return "ok"
