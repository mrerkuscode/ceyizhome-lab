from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


BACKUP_RELATIVE_FILES = [
    "data/name_cut_queue.json",
    "data/name_cut_transfer_history.json",
    "data/name_cut_export_history.json",
    "data/print_queue.json",
    "data/production_audit_log.json",
    "data/customer_orders.json",
    "data/production_history.json",
    "data/printer_profiles.json",
    # NOTE: data/trendyol_settings.json INTENTIONALLY excluded.
    # Contains api_key / api_secret / ai_api_key in plain text; backups can be
    # shared off-machine (support, cloud sync) which would leak credentials.
    # Operators must re-enter Trendyol credentials after a restore.
    "data/trendyol_questions_context.json",
    "data/trendyol_product_mappings.json",
    "data/trendyol_mapping_suggestions.json",
    "data/trendyol_production_suggestions.json",
    "data/trendyol_ai_extraction_cache.json",
    "data/trendyol_extraction_learning_examples.json",
    "assets/references/corel_name_reference_library.json",
    "config/settings.yaml",
]


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backups_root(project_root: Path) -> Path:
    path = project_root / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_project_relative(project_root: Path, relative_path: str) -> Path:
    cleaned = str(relative_path or "").replace("\\", "/").lstrip("/")
    if not cleaned or ".." in Path(cleaned).parts:
        raise ValueError("Geçersiz proje içi dosya yolu.")
    target = (project_root / cleaned).resolve()
    target.relative_to(project_root.resolve())
    return target


def _resolve_backup_dir(project_root: Path, raw_path: str | Path) -> Path:
    if not raw_path:
        raise ValueError("Yedek yolu boş.")
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    resolved = path.resolve()
    root = backups_root(project_root).resolve()
    resolved.relative_to(root)
    if resolved.is_file() and resolved.name == "manifest.json":
        resolved = resolved.parent
    if not (resolved / "manifest.json").exists():
        raise ValueError("Manifest dosyası bulunamadı.")
    return resolved


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest JSON bozuk: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Manifest formatı geçersiz.")
    return data


def _file_entry(project_root: Path, backup_dir: Path, relative_path: str) -> dict[str, Any] | None:
    source = project_root / relative_path
    if not source.exists() or not source.is_file():
        return None
    dest = backup_dir / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {
        "relative_path": relative_path,
        "size": dest.stat().st_size,
        "sha256": _sha256(dest),
    }


def create_backup(project_root: Path, reason: str = "manual") -> dict[str, Any]:
    created_at = _now_text()
    backup_id = f"ceyizhome_lab_backup_{_stamp()}_{uuid.uuid4().hex[:8]}"
    backup_dir = backups_root(project_root) / datetime.now().strftime("%Y-%m-%d") / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    files = []
    missing = []
    for relative_path in BACKUP_RELATIVE_FILES:
        entry = _file_entry(project_root, backup_dir, relative_path)
        if entry:
            files.append(entry)
        else:
            missing.append(relative_path)
    manifest = {
        "backup_id": backup_id,
        "created_at": created_at,
        "reason": reason,
        "project": "CeyizHome Lab",
        "file_count": len(files),
        "missing_files": missing,
        "files": files,
        "safety": {
            "auto_print_started": False,
            "laser_started": False,
            "rdworks_started": False,
            "trendyol_live_action": False,
        },
    }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "message": f"Yedek oluşturuldu: {backup_id}",
        "backup_id": backup_id,
        "backup_path": str(backup_dir.relative_to(project_root)),
        "manifest_path": str(manifest_path.relative_to(project_root)),
        "file_count": len(files),
        "missing_files": missing,
        "created_at": created_at,
        "manifest": manifest,
        "auto_print_started": False,
        "laser_started": False,
        "rdworks_started": False,
        "trendyol_live_action": False,
    }


def list_backups(project_root: Path) -> list[dict[str, Any]]:
    rows = []
    for manifest_path in sorted(backups_root(project_root).glob("20??-??-??/ceyizhome_lab_backup_*/manifest.json"), reverse=True):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        backup_dir = manifest_path.parent
        rows.append({
            "backup_id": manifest.get("backup_id") or backup_dir.name,
            "created_at": manifest.get("created_at") or datetime.fromtimestamp(manifest_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "reason": manifest.get("reason") or "",
            "file_count": manifest.get("file_count") or 0,
            "backup_path": str(backup_dir.relative_to(project_root)),
            "manifest_path": str(manifest_path.relative_to(project_root)),
            "size_kb": max(1, round(sum(path.stat().st_size for path in backup_dir.rglob("*") if path.is_file()) / 1024)),
        })
    return rows


def validate_backup(project_root: Path, raw_path: str | Path) -> dict[str, Any]:
    try:
        backup_dir = _resolve_backup_dir(project_root, raw_path)
        manifest = _load_manifest(backup_dir)
    except Exception as exc:
        return {"status": "ERROR", "message": str(exc), "valid": False}
    errors = []
    warnings = []
    for entry in manifest.get("files", []):
        if not isinstance(entry, dict):
            errors.append("Geçersiz manifest satırı.")
            continue
        relative_path = str(entry.get("relative_path") or "")
        try:
            _safe_project_relative(project_root, relative_path)
        except Exception as exc:
            errors.append(f"{relative_path}: {exc}")
            continue
        backup_file = backup_dir / relative_path
        if not backup_file.exists():
            errors.append(f"{relative_path}: yedek dosyası bulunamadı.")
            continue
        if entry.get("sha256") and _sha256(backup_file) != entry.get("sha256"):
            errors.append(f"{relative_path}: checksum uyuşmuyor.")
        if backup_file.suffix.lower() == ".json":
            try:
                json.loads(backup_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{relative_path}: JSON bozuk ({exc}).")
    if not manifest.get("files"):
        warnings.append("Manifest içinde dosya yok.")
    return {
        "status": "OK" if not errors else "ERROR",
        "message": "Yedek doğrulandı." if not errors else "Yedek doğrulanamadı.",
        "valid": not errors,
        "backup_path": str(backup_dir.relative_to(project_root)),
        "manifest_path": str((backup_dir / "manifest.json").relative_to(project_root)),
        "file_count": len(manifest.get("files", [])),
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest,
    }


def restore_backup(project_root: Path, raw_path: str | Path, dry_run: bool = True) -> dict[str, Any]:
    validation = validate_backup(project_root, raw_path)
    if validation.get("status") != "OK":
        return {**validation, "restore_status": "BLOCKED", "dry_run": dry_run}
    backup_dir = _resolve_backup_dir(project_root, raw_path)
    manifest = validation["manifest"]
    changes = []
    for entry in manifest.get("files", []):
        relative_path = str(entry.get("relative_path") or "")
        target = _safe_project_relative(project_root, relative_path)
        backup_file = backup_dir / relative_path
        current_checksum = _sha256(target) if target.exists() and target.is_file() else ""
        changes.append({
            "relative_path": relative_path,
            "target_exists": target.exists(),
            "current_sha256": current_checksum,
            "backup_sha256": entry.get("sha256") or "",
            "will_change": current_checksum != (entry.get("sha256") or ""),
        })
    if dry_run:
        return {
            "status": "DRY_RUN",
            "message": f"Geri yükleme önizlendi: {len(changes)} dosya kontrol edildi.",
            "dry_run": True,
            "changes": changes,
            "backup_path": validation.get("backup_path"),
            "snapshot": None,
            "auto_print_started": False,
            "laser_started": False,
            "rdworks_started": False,
            "trendyol_live_action": False,
        }
    snapshot = create_backup(project_root, reason="pre_restore_snapshot")
    restored = []
    for entry in manifest.get("files", []):
        relative_path = str(entry.get("relative_path") or "")
        target = _safe_project_relative(project_root, relative_path)
        source = backup_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored.append(relative_path)
    return {
        "status": "OK",
        "message": f"Geri yükleme tamamlandı: {len(restored)} dosya.",
        "dry_run": False,
        "restored_files": restored,
        "changes": changes,
        "backup_path": validation.get("backup_path"),
        "snapshot": snapshot,
        "auto_print_started": False,
        "laser_started": False,
        "rdworks_started": False,
        "trendyol_live_action": False,
    }


def export_backup_manifest(project_root: Path, raw_path: str | Path = "") -> dict[str, Any]:
    backups = list_backups(project_root)
    if not raw_path:
        if not backups:
            return {"status": "MISSING", "message": "Dışa aktarılacak yedek bulunamadı."}
        raw_path = backups[0]["backup_path"]
    validation = validate_backup(project_root, raw_path)
    if validation.get("status") != "OK":
        return validation
    return {
        "status": "OK",
        "message": "Manifest hazır.",
        "manifest_path": validation.get("manifest_path"),
        "manifest": validation.get("manifest"),
        "file_count": validation.get("file_count"),
    }
