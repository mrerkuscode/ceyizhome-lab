"""Watchdog-based folder monitor for the DXF library.

Optional daemon — the library still works via on-demand `api_refresh()`. The
watcher is started by `start_watcher(project_root)` and stopped via
`stop_watcher()`. It debounces file events (filesystems can emit multiple
events per save) and re-scans the library on quiet.

Design:
- Single Observer covers all three size-group folders.
- Debounce: 1.0s of quiet before rescan (CorelDRAW DXF export writes are
  short; 1s is generous).
- Errors during scan are swallowed (logged via stderr) so the watcher
  thread never crashes the app.
- Thread-safe; the watcher runs in its own background thread.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover
    Observer = None  # type: ignore[assignment]
    FileSystemEventHandler = object  # type: ignore[assignment,misc]
    WATCHDOG_AVAILABLE = False

from webui_backend.dxf_library_api import (
    DXF_LIBRARY_DIR_RELATIVE,
    SIZE_GROUPS,
    scan_library,
)


_state_lock = threading.Lock()
_observer: Any = None
_debounce_timer: threading.Timer | None = None
_last_scan_result: dict[str, Any] | None = None
_on_scan_callbacks: list[Callable[[dict[str, Any]], None]] = []


class _DxfEventHandler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root

    def _is_dxf(self, path: str) -> bool:
        return path.lower().endswith(".dxf")

    def on_created(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and self._is_dxf(event.src_path):
            _trigger_debounced_scan(self.project_root)

    def on_modified(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and self._is_dxf(event.src_path):
            _trigger_debounced_scan(self.project_root)

    def on_deleted(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and self._is_dxf(event.src_path):
            _trigger_debounced_scan(self.project_root)

    def on_moved(self, event):  # type: ignore[no-untyped-def]
        src_dxf = self._is_dxf(getattr(event, "src_path", "") or "")
        dst_dxf = self._is_dxf(getattr(event, "dest_path", "") or "")
        if not event.is_directory and (src_dxf or dst_dxf):
            _trigger_debounced_scan(self.project_root)


def _run_scan(project_root: Path) -> None:
    global _last_scan_result
    try:
        result = scan_library(project_root)
    except Exception as exc:  # noqa: BLE001 — never let watcher thread crash
        import sys
        print(f"[dxf_library_watcher] scan failed: {exc}", file=sys.stderr)
        return
    with _state_lock:
        _last_scan_result = result
        callbacks = list(_on_scan_callbacks)
    for cb in callbacks:
        try:
            cb(result)
        except Exception as exc:  # noqa: BLE001
            import sys
            print(f"[dxf_library_watcher] callback raised: {exc}", file=sys.stderr)


def _trigger_debounced_scan(project_root: Path, delay: float = 1.0) -> None:
    global _debounce_timer
    with _state_lock:
        if _debounce_timer is not None:
            _debounce_timer.cancel()
        _debounce_timer = threading.Timer(delay, _run_scan, args=(project_root,))
        _debounce_timer.daemon = True
        _debounce_timer.start()


def is_running() -> bool:
    with _state_lock:
        return _observer is not None


def watchdog_available() -> bool:
    return WATCHDOG_AVAILABLE


def register_on_scan(callback: Callable[[dict[str, Any]], None]) -> None:
    """Subscribe to scan-complete events (called from watcher thread)."""
    with _state_lock:
        _on_scan_callbacks.append(callback)


def get_last_scan_result() -> dict[str, Any] | None:
    with _state_lock:
        return _last_scan_result


def start_watcher(project_root: Path) -> dict[str, Any]:
    global _observer
    if not WATCHDOG_AVAILABLE:
        return {"status": "UNAVAILABLE", "message": "watchdog modülü yüklü değil; manuel tarama kullan."}
    with _state_lock:
        if _observer is not None:
            return {"status": "ALREADY_RUNNING", "message": "DXF kütüphane izleyici zaten çalışıyor."}
    lib_root = project_root / DXF_LIBRARY_DIR_RELATIVE
    if not lib_root.exists():
        lib_root.mkdir(parents=True, exist_ok=True)
    handler = _DxfEventHandler(project_root)
    obs = Observer()
    paths_watched = []
    for group in SIZE_GROUPS:
        group_dir = lib_root / group
        group_dir.mkdir(parents=True, exist_ok=True)
        obs.schedule(handler, str(group_dir), recursive=False)
        paths_watched.append(str(group_dir))
    obs.daemon = True
    obs.start()
    with _state_lock:
        _observer = obs
    # Trigger an immediate scan on startup so the index is fresh.
    _trigger_debounced_scan(project_root, delay=0.1)
    return {
        "status": "OK",
        "message": "DXF kütüphane izleyici başlatıldı.",
        "paths_watched": paths_watched,
    }


def stop_watcher() -> dict[str, Any]:
    global _observer, _debounce_timer
    with _state_lock:
        if _observer is None:
            return {"status": "NOT_RUNNING", "message": "İzleyici zaten çalışmıyor."}
        try:
            _observer.stop()
            _observer.join(timeout=3.0)
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR", "message": f"İzleyici durdurulamadı: {exc}"}
        _observer = None
        if _debounce_timer is not None:
            _debounce_timer.cancel()
            _debounce_timer = None
    return {"status": "OK", "message": "DXF kütüphane izleyici durduruldu."}
