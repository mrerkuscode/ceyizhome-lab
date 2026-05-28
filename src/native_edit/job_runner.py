from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _today_dir(project_root: Path) -> Path:
    # Existing UI reports historically use output/YYYY-MM-DD. Keep this PoC current-date based.
    return project_root / "output" / date.today().isoformat()


def create_job_dir(project_root: str | Path, prefix: str) -> Path:
    root = Path(project_root)
    job_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job_dir = _today_dir(root) / "native_edit_poc" / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _resolve_source(project_root: Path, source_path: str | Path) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def prepare_input_copy(project_root: str | Path, source_path: str | Path, prefix: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    source = _resolve_source(root, source_path)
    if not source.exists():
        raise FileNotFoundError(f"Kaynak dosya bulunamadı: {source}")
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ValueError("Proje dışındaki kaynak dosya bu PoC için işlenemez.") from exc
    job_dir = create_job_dir(root, prefix)
    input_copy = job_dir / f"input_copy{source.suffix.lower()}"
    source_hash_before = sha256_file(source)
    shutil.copy2(source, input_copy)
    return {
        "project_root": root,
        "source": source,
        "job_dir": job_dir,
        "job_id": job_dir.name,
        "input_copy": input_copy,
        "source_hash_before": source_hash_before,
    }


def _base_failure(source: Path, status: str, message: str, *, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "source_path": str(source),
        "source_unchanged": True,
        "warnings": warnings or [],
        "errors": [] if status != "FAILED" else [message],
    }


def run_native_edit_poc(
    project_root: str | Path,
    source_path: str | Path,
    *,
    edit: bool = True,
    allow_engine: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    source = _resolve_source(root, source_path)
    suffix = source.suffix.lower()
    if suffix == ".ai":
        from .illustrator_worker import run_ai_poc

        return run_ai_poc(root, source, edit=edit, allow_engine=allow_engine)
    if suffix == ".cdr":
        from .coreldraw_worker import run_cdr_poc

        return run_cdr_poc(root, source, edit=edit, allow_engine=allow_engine)
    return _base_failure(
        source,
        "FAILED",
        "Bu dosya native AI/CDR düzenleme testi için uygun değil.",
        warnings=["Sadece .ai ve .cdr kaynak dosyaları desteklenir."],
    )


def run_native_edit_poc_for_template(
    project_root: str | Path,
    template_path: str | Path,
    *,
    edit: bool = True,
    allow_engine: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    template = _resolve_source(root, template_path)
    data = json.loads(template.read_text(encoding="utf-8"))
    source_file = data.get("source_file")
    if not source_file:
        return _base_failure(template, "FAILED", "Bu modelde kaynak AI/CDR dosyası belirtilmemiş.")
    return run_native_edit_poc(root, source_file, edit=edit, allow_engine=allow_engine)
