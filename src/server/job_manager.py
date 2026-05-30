"""
Browser Mode — Thread-based background job registry.

Usage:
    job_id = start_job("render_labels", some_fn, arg1, arg2)
    status = get_status(job_id)
    log    = get_log(job_id, tail=50)
    result = cancel_job(job_id)
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Callable, Any

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _log(job_id: str, line: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["log"].append(line)


def start_job(name: str, fn: Callable, *args: Any, **kwargs: Any) -> str:
    """Start fn(*args, **kwargs) in a daemon thread. Returns job_id."""
    job_id = _new_id()
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "name": name,
            "status": "running",
            "log": [],
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "result": None,
            "error": None,
        }

    def _run() -> None:
        try:
            _log(job_id, f"[START] {name}")
            result = fn(*args, **kwargs)
            _log(job_id, f"[DONE] {name}")
            with _lock:
                _jobs[job_id]["status"] = "completed"
                _jobs[job_id]["ended_at"] = datetime.now().isoformat()
                _jobs[job_id]["result"] = result
        except Exception as exc:  # noqa: BLE001
            _log(job_id, f"[ERROR] {exc}")
            with _lock:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["ended_at"] = datetime.now().isoformat()
                _jobs[job_id]["error"] = str(exc)

    threading.Thread(target=_run, daemon=True, name=f"job-{job_id}").start()
    return job_id


def get_status(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return {"status": "NOT_FOUND", "job_id": job_id}
    return {
        "job_id": job_id,
        "name": job["name"],
        "status": job["status"],
        "started_at": job["started_at"],
        "ended_at": job["ended_at"],
        "log_lines": len(job["log"]),
        "error": job.get("error"),
    }


def get_log(job_id: str, tail: int = 100) -> dict:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        return {"status": "NOT_FOUND", "job_id": job_id, "lines": []}
    lines = job["log"]
    return {
        "job_id": job_id,
        "status": job["status"],
        "lines": list(lines[-tail:]) if tail > 0 else list(lines),
    }


def cancel_job(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return {"status": "NOT_FOUND", "job_id": job_id}
        if job["status"] != "running":
            return {
                "status": "NOT_RUNNING",
                "job_id": job_id,
                "current_status": job["status"],
            }
        job["status"] = "cancelled"
        job["ended_at"] = datetime.now().isoformat()
        job["log"].append("[CANCELLED] Kullanıcı tarafından durduruldu")
    return {"status": "OK", "job_id": job_id, "message": "Job cancelled"}


def list_jobs() -> list:
    with _lock:
        return [
            {
                "job_id": jid,
                "name": j["name"],
                "status": j["status"],
                "started_at": j["started_at"],
                "ended_at": j["ended_at"],
            }
            for jid, j in _jobs.items()
        ]


# ── Browser-mode job functions (called by routes) ────────────────────────────

def _browser_render_labels(excel_path: str = "") -> dict:
    """Browser mode render — production pipeline without Qt/CorelDRAW."""
    from server import controller_proxy as proxy
    root = proxy._root()
    outputs = proxy._label_api().list_label_outputs(root)
    return {
        "status": "BROWSER_MODE",
        "message": "Render tamamlandı (browser modu — görsel render masaüstünde çalışır).",
        "excel_path": excel_path,
        "existing_outputs": len(outputs),
    }


def _browser_reanalyze_all(project_root_str: str = "", job_id: str = "") -> dict:
    """Browser mode: toplu Trendyol AI yeniden analiz."""
    from pathlib import Path
    from webui_backend import trendyol_api as _ta
    root = Path(project_root_str) if project_root_str else Path(__file__).resolve().parents[2]
    return _ta.reanalyze_all_trendyol_suggestions(root, delay_s=0.3, job_id=job_id)


def _browser_run_dry(excel_path: str = "") -> dict:
    """Browser mode dry-run — validation pass without real production."""
    from server import controller_proxy as proxy
    root = proxy._root()
    queue = proxy._print_queue_api().list_print_queue(root)
    return {
        "status": "BROWSER_MODE",
        "message": "Dry run tamamlandı (browser modu — üretim masaüstünde çalışır).",
        "excel_path": excel_path,
        "queue_items": len(queue),
    }
