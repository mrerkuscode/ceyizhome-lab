"""Trendyol auto-sync background scheduler.

Runs delta_sync_for_poll() on a configurable interval in a daemon thread.
Start/stop is controlled by auto_sync_enabled in trendyol_settings.json.
"""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any

_lock = threading.Lock()
_stop_event = threading.Event()
_thread: threading.Thread | None = None
_project_root: Path | None = None

_state: dict[str, Any] = {
    "enabled": False,
    "interval_sec": 30,
    "running_poll": False,
    "last_run_at": "",
    "last_new_orders": 0,
    "last_new_questions": 0,
    "last_status": "",
    "last_message": "",
    "current_interval_sec": 30,
}


def start(project_root: Path, interval_sec: int = 30) -> None:
    """Start the background scheduler thread (idempotent)."""
    global _thread, _project_root
    with _lock:
        _project_root = project_root
        _state["interval_sec"] = max(10, int(interval_sec))
        _state["current_interval_sec"] = _state["interval_sec"]
        _state["enabled"] = True
        if _thread and _thread.is_alive():
            return
        _stop_event.clear()
        _thread = threading.Thread(
            target=_run_loop,
            args=(project_root,),
            daemon=True,
            name="trendyol-autosync",
        )
        _thread.start()


def stop() -> None:
    """Signal the scheduler to stop after the current interval."""
    with _lock:
        _state["enabled"] = False
    _stop_event.set()


def is_alive() -> bool:
    return bool(_thread and _thread.is_alive())


def get_status() -> dict[str, Any]:
    with _lock:
        return dict(_state)


def _run_loop(project_root: Path) -> None:
    while not _stop_event.is_set():
        with _lock:
            if not _state["enabled"]:
                break
            interval = float(_state["current_interval_sec"])

        # Wait for the interval; stop_event wakes it early on stop()
        _stop_event.wait(timeout=interval)
        if _stop_event.is_set():
            break

        # Overlap guard: skip if previous poll is still running
        with _lock:
            if _state["running_poll"]:
                continue
            _state["running_poll"] = True

        try:
            _do_poll(project_root)
        finally:
            with _lock:
                _state["running_poll"] = False


def _do_poll(project_root: Path) -> None:
    from webui_backend import trendyol_api as _ta  # deferred to avoid circular imports
    try:
        result = _ta.delta_sync_for_poll(project_root)
        with _lock:
            _state["last_run_at"] = datetime.now().strftime("%H:%M:%S")
            _state["last_new_orders"] = int(result.get("new_orders") or 0)
            _state["last_new_questions"] = int(result.get("new_questions") or 0)
            _state["last_status"] = str(result.get("status") or "OK")
            _state["last_message"] = str(result.get("message") or "")
            # Restore normal interval on success
            _state["current_interval_sec"] = _state["interval_sec"]
    except Exception as exc:  # noqa: BLE001
        err_str = str(exc)
        with _lock:
            _state["last_run_at"] = datetime.now().strftime("%H:%M:%S")
            _state["last_status"] = "ERROR"
            _state["last_message"] = err_str[:200]
            # Expand interval on rate-limit / transient API errors
            if any(kw in err_str for kw in ("429", "Rate", "UNAVAILABLE", "timeout")):
                _state["current_interval_sec"] = min(_state["current_interval_sec"] * 2, 300)
