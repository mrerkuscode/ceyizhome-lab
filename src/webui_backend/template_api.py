from __future__ import annotations

import copy
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import yaml
from PySide6.QtGui import QColor, QImage, QPainter

from desktop.label_template_editor import (
    add_variable_field,
    import_font_file,
    list_design_templates,
    load_template_data,
    remove_variable_field,
    save_template_with_backup,
)
from desktop.template_importer import ALLOWED_PRINT_TEMPLATE_SUFFIXES, safe_extract_template_pack
from webui_backend.file_api import to_web_file_url
from webui_backend.production_safety import model_health_for_template


METADATA_FILE = ".template_metadata.json"
METADATA_BACKUP_FILE = ".template_metadata.backup.json"
BACKUP_NOTES_FILE = ".backup_notes.json"
RASTER_PREVIEW_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VECTOR_PREVIEW_SUFFIXES = {".svg"}
DOCUMENT_PREVIEW_SUFFIXES = {".pdf"}
PREVIEW_IMAGE_SUFFIXES = {*RASTER_PREVIEW_SUFFIXES, *VECTOR_PREVIEW_SUFFIXES, *DOCUMENT_PREVIEW_SUFFIXES}
MODEL_SOURCE_SUFFIXES = {*ALLOWED_PRINT_TEMPLATE_SUFFIXES, *RASTER_PREVIEW_SUFFIXES}


def list_label_templates(project_root: Path) -> list[dict[str, str]]:
    templates: list[dict[str, str]] = []
    for path in list_design_templates(project_root):
        try:
            data = load_template_data(path)
        except Exception:
            data = {}
        label = (
            data.get("template_name")
            or f"{data.get('model_no', '')} {data.get('template_no', '')} {data.get('label_variant', '')}".strip()
            or path.stem
        )
        fields = data.get("fields") or _elements_to_fields(data.get("elements") or [])
        preview_relative = str(data.get("preview_image") or "")
        preview_path = normalize_project_path(project_root, preview_relative) if preview_relative else None
        preview_exists = bool(preview_path and preview_path.exists())
        has_preview = preview_exists
        health = model_health_for_template(project_root, path)
        templates.append(
            {
                "name": str(label),
                "path": str(path),
                "model_no": str(data.get("model_no", "")),
                "template_no": str(data.get("template_no", "")),
                "label_variant": str(data.get("label_variant", "")),
                "model_name": str(data.get("model_name") or data.get("template_name") or label),
                "preview_image": _asset_uri(project_root, preview_relative) if preview_exists else "",
                "preview_image_path": preview_relative,
                "preview_exists": preview_exists,
                "preview_missing_file": bool(preview_relative and not preview_exists),
                "preview_required": "false" if has_preview else "true",
                "preview_required_message": ""
                if has_preview
                else "Ger\u00e7ek tasar\u0131m \u00f6nizlemesi yok. AI/CDR dosyas\u0131ndan PNG/JPG/WebP export edip buraya ba\u011flay\u0131n.",
                "label_width_mm": str(data.get("label_width_mm") or data.get("canvas_width_mm") or ""),
                "label_height_mm": str(data.get("label_height_mm") or data.get("canvas_height_mm") or ""),
                "active": str(data.get("active", True)),
                "fields_count": str(len(fields)),
                "fields_summary": _fields_summary(fields),
                "duplicate_field_warnings": _duplicate_field_warnings(fields),
                "health_status": str(health.get("status") or ""),
                "health_class": str(health.get("class") or "warn"),
                "health_messages": health.get("messages") if isinstance(health.get("messages"), list) else [],
                "source_file": str(data.get("source_file") or ""),
                "source_file_type": Path(str(data.get("source_file") or "")).suffix.lower().lstrip(".").upper(),
                "source_preview_note": _source_preview_note(str(data.get("source_file") or "")),
            }
        )
    return templates


def list_label_model_gallery(project_root: Path) -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    for item in list_label_templates(project_root):
        title = item.get("model_name") or f"Model {item.get('model_no', '-')}"
        has_preview = bool(item.get("preview_image"))
        models.append(
            {
                **item,
                "title": title,
                "subtitle": f"Model {item.get('model_no') or '-'} · Şablon {item.get('template_no') or '-'} · {item.get('label_variant') or '-'}",
                "size_text": f"{item.get('label_width_mm') or '-'} x {item.get('label_height_mm') or '-'} mm",
                "preview_status": "VAR" if has_preview else "YOK",
                "preview_warning": ""
                if has_preview
                else "Ger\u00e7ek tasar\u0131m \u00f6nizlemesi yok. AI/CDR dosyas\u0131ndan PNG/JPG/WebP export edip buraya ba\u011flay\u0131n.",
                "design_position_status": "ONAYLI" if has_preview else "ONAYLANMADI",
                "design_position_warning": ""
                if has_preview
                else "Tasar\u0131m konumu onaylanmad\u0131. \u00dcretimi engellemez; ger\u00e7ek \u00f6nizleme g\u00f6rseli ba\u011fland\u0131ktan sonra alan konumlar\u0131n\u0131 kontrol edin.",
            }
        )
    return models


def list_label_model_backups(project_root: Path, template_path: Path, limit: int = 12) -> list[dict[str, str]]:
    path = _safe_design_template_path(project_root, template_path)
    backup_dir = path.parent / "backups"
    if not backup_dir.exists():
        return []
    notes = _load_backup_notes(backup_dir)
    prefix = f"{path.stem}_"
    rows: list[dict[str, str]] = []
    for item in sorted(backup_dir.glob(f"{prefix}*.json"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
        stat = item.stat()
        rows.append(
            {
                "file_name": item.name,
                "relative_path": _relative(item, project_root),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(stat.st_size / 1024))),
                "note": str(notes.get(item.name, "")),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _load_backup_notes(backup_dir: Path) -> dict[str, str]:
    notes_path = backup_dir / BACKUP_NOTES_FILE
    if not notes_path.exists():
        return {}
    try:
        raw = json.loads(notes_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _write_backup_notes(backup_dir: Path, notes: dict[str, str]) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    filtered = {str(key): str(value)[:240] for key, value in notes.items() if str(value).strip()}
    (backup_dir / BACKUP_NOTES_FILE).write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_backup_path_for_model(project_root: Path, template_path: Path, backup_relative_path: str) -> tuple[Path, Path]:
    path = _safe_design_template_path(project_root, template_path)
    backup_dir = (path.parent / "backups").resolve()
    backup_path = normalize_project_path(project_root, backup_relative_path)
    try:
        backup_path.relative_to(backup_dir)
    except ValueError as exc:
        raise ValueError("Geçersiz backup yolu.") from exc
    if not backup_path.exists() or backup_path.suffix.lower() != ".json":
        raise FileNotFoundError("Backup dosyası bulunamadı.")
    return backup_dir, backup_path


def set_label_model_backup_note(project_root: Path, template_path: Path, backup_relative_path: str, note: str) -> dict[str, object]:
    backup_dir, backup_path = _safe_backup_path_for_model(project_root, template_path, backup_relative_path)
    clean_note = re.sub(r"\s+", " ", str(note or "")).strip()[:240]
    notes = _load_backup_notes(backup_dir)
    if clean_note:
        notes[backup_path.name] = clean_note
    else:
        notes.pop(backup_path.name, None)
    _write_backup_notes(backup_dir, notes)
    return {
        "status": "OK",
        "message": "Backup notu kaydedildi.",
        "backup": _relative(backup_path, project_root),
        "note": clean_note,
    }


def compare_label_model_backup(project_root: Path, template_path: Path, backup_relative_path: str) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    backup_dir = (path.parent / "backups").resolve()
    backup_path = normalize_project_path(project_root, backup_relative_path)
    try:
        backup_path.relative_to(backup_dir)
    except ValueError as exc:
        raise ValueError("Geçersiz backup yolu.") from exc
    if not backup_path.exists() or backup_path.suffix.lower() != ".json":
        raise FileNotFoundError("Backup dosyası bulunamadı.")

    current = load_template_data(path)
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    current_fields = current.get("fields") if isinstance(current.get("fields"), list) else []
    backup_fields = backup.get("fields") if isinstance(backup.get("fields"), list) else []
    current_columns = [str(field.get("excel_column") or "") for field in current_fields if isinstance(field, dict)]
    backup_columns = [str(field.get("excel_column") or "") for field in backup_fields if isinstance(field, dict)]
    added_columns = sorted(set(current_columns) - set(backup_columns))
    removed_columns = sorted(set(backup_columns) - set(current_columns))

    watched_keys = [
        "template_name",
        "model_no",
        "template_no",
        "label_variant",
        "label_width_mm",
        "label_height_mm",
        "preview_image",
        "background_image",
        "background_enabled",
        "active",
    ]
    changed_keys = [key for key in watched_keys if str(current.get(key, "")) != str(backup.get(key, ""))]
    setting_labels = {
        "template_name": "Model adı",
        "model_no": "Model no",
        "template_no": "Şablon no",
        "label_variant": "Varyant",
        "label_width_mm": "Genişlik",
        "label_height_mm": "Yükseklik",
        "preview_image": "Önizleme görseli",
        "background_image": "Tasarım görseli",
        "background_enabled": "Tasarım görseli aktif",
        "active": "Aktif/Pasif",
    }
    setting_diffs = [
        {
            "key": key,
            "label": setting_labels.get(key, key),
            "current": str(current.get(key, "")),
            "backup": str(backup.get(key, "")),
        }
        for key in changed_keys
    ]
    field_labels = {
        "label_text": "İsim",
        "date_text": "Tarih",
        "note_text": "Not",
        "custom_text": "Ek yazı",
    }
    field_watch_keys = {
        "x_mm": "Konum X",
        "y_mm": "Konum Y",
        "width_mm": "Genişlik",
        "height_mm": "Yükseklik",
        "font_size": "Yazı boyutu",
        "line_height": "Satır aralığı",
        "font_family": "Font",
        "color": "Renk",
        "align": "Hizalama",
        "vertical_align": "Dikey hizalama",
        "visible": "Görünürlük",
        "excel_column": "Alan türü",
    }
    current_by_column = {
        str(field.get("excel_column") or f"index_{index}"): field
        for index, field in enumerate(current_fields)
        if isinstance(field, dict)
    }
    backup_by_column = {
        str(field.get("excel_column") or f"index_{index}"): field
        for index, field in enumerate(backup_fields)
        if isinstance(field, dict)
    }
    field_diffs: list[dict[str, object]] = []
    for column in sorted(set(current_by_column) | set(backup_by_column)):
        current_field = current_by_column.get(column) or {}
        backup_field = backup_by_column.get(column) or {}
        changes = []
        for key, label in field_watch_keys.items():
            current_value = str(current_field.get(key, ""))
            backup_value = str(backup_field.get(key, ""))
            if current_value != backup_value:
                changes.append({"key": key, "label": label, "current": current_value, "backup": backup_value})
        if changes:
            field_diffs.append(
                {
                    "column": column,
                    "label": field_labels.get(column, current_field.get("field_name") or backup_field.get("field_name") or column),
                    "changes": changes,
                }
            )
    changed_fields = 0
    for index in range(max(len(current_fields), len(backup_fields))):
        current_field = current_fields[index] if index < len(current_fields) else None
        backup_field = backup_fields[index] if index < len(backup_fields) else None
        if json.dumps(current_field, sort_keys=True, ensure_ascii=False) != json.dumps(backup_field, sort_keys=True, ensure_ascii=False):
            changed_fields += 1

    summary: list[str] = []
    if changed_keys:
        summary.append(f"{len(changed_keys)} model ayarı değişmiş.")
    if added_columns:
        summary.append(f"Yeni alanlar: {', '.join(added_columns)}.")
    if removed_columns:
        summary.append(f"Backup içinde olup mevcut modelde olmayan alanlar: {', '.join(removed_columns)}.")
    if changed_fields:
        summary.append(f"{changed_fields} yazı alanında konum/stil farkı var.")
    if not summary:
        summary.append("Mevcut model ile backup arasında önemli fark görünmüyor.")

    return {
        "status": "OK",
        "backup": _relative(backup_path, project_root),
        "current_field_count": len(current_fields),
        "backup_field_count": len(backup_fields),
        "changed_keys": changed_keys,
        "setting_diffs": setting_diffs,
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "changed_field_count": changed_fields,
        "field_diffs": field_diffs,
        "summary": summary,
        "message": "Backup mevcut modelle karşılaştırıldı.",
    }


def compare_label_model_backup_pair(project_root: Path, template_path: Path, first_backup_relative_path: str, second_backup_relative_path: str) -> dict[str, object]:
    _first_dir, first_path = _safe_backup_path_for_model(project_root, template_path, first_backup_relative_path)
    _second_dir, second_path = _safe_backup_path_for_model(project_root, template_path, second_backup_relative_path)
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second = json.loads(second_path.read_text(encoding="utf-8"))
    first_fields = first.get("fields") if isinstance(first.get("fields"), list) else []
    second_fields = second.get("fields") if isinstance(second.get("fields"), list) else []
    watched_keys = [
        "template_name",
        "model_no",
        "template_no",
        "label_variant",
        "label_width_mm",
        "label_height_mm",
        "preview_image",
        "background_image",
        "active",
    ]
    setting_labels = {
        "template_name": "Model adı",
        "model_no": "Model no",
        "template_no": "Şablon no",
        "label_variant": "Varyant",
        "label_width_mm": "Genişlik",
        "label_height_mm": "Yükseklik",
        "preview_image": "Önizleme görseli",
        "background_image": "Tasarım görseli",
        "active": "Aktif/Pasif",
    }
    setting_diffs = [
        {"key": key, "label": setting_labels.get(key, key), "current": str(first.get(key, "")), "backup": str(second.get(key, ""))}
        for key in watched_keys
        if str(first.get(key, "")) != str(second.get(key, ""))
    ]
    field_watch_keys = {
        "x_mm": "Konum X",
        "y_mm": "Konum Y",
        "width_mm": "Genişlik",
        "height_mm": "Yükseklik",
        "font_size": "Yazı boyutu",
        "line_height": "Satır aralığı",
        "font_family": "Font",
        "color": "Renk",
        "align": "Hizalama",
        "visible": "Görünürlük",
        "excel_column": "Alan türü",
    }
    field_labels = {"label_text": "İsim", "date_text": "Tarih", "note_text": "Not", "custom_text": "Ek yazı"}
    first_by_column = {str(field.get("excel_column") or f"index_{index}"): field for index, field in enumerate(first_fields) if isinstance(field, dict)}
    second_by_column = {str(field.get("excel_column") or f"index_{index}"): field for index, field in enumerate(second_fields) if isinstance(field, dict)}
    field_diffs: list[dict[str, object]] = []
    for column in sorted(set(first_by_column) | set(second_by_column)):
        first_field = first_by_column.get(column) or {}
        second_field = second_by_column.get(column) or {}
        changes = []
        for key, label in field_watch_keys.items():
            first_value = str(first_field.get(key, ""))
            second_value = str(second_field.get(key, ""))
            if first_value != second_value:
                changes.append({"key": key, "label": label, "current": first_value, "backup": second_value})
        if changes:
            field_diffs.append({"column": column, "label": field_labels.get(column, first_field.get("field_name") or second_field.get("field_name") or column), "changes": changes})
    summary: list[str] = []
    if setting_diffs:
        summary.append(f"{len(setting_diffs)} model ayarı farklı.")
    if field_diffs:
        summary.append(f"{len(field_diffs)} yazı alanında fark var.")
    if not summary:
        summary.append("İki backup arasında önemli fark görünmüyor.")
    return {
        "status": "OK",
        "first_backup": _relative(first_path, project_root),
        "second_backup": _relative(second_path, project_root),
        "setting_diffs": setting_diffs,
        "field_diffs": field_diffs,
        "summary": summary,
        "message": "İki backup karşılaştırıldı.",
    }


def restore_label_model_backup(project_root: Path, template_path: Path, backup_relative_path: str) -> dict[str, object]:
    """Restore a design template from a known backup after saving the current version.

    The backup source is constrained to the same model's `templates/designs/backups`
    folder. This keeps the operation limited to JSON model config and avoids source
    AI/CDR assets entirely.
    """

    path = _safe_design_template_path(project_root, template_path)
    backup_dir = (path.parent / "backups").resolve()
    backup_path = normalize_project_path(project_root, backup_relative_path)
    try:
        backup_path.relative_to(backup_dir)
    except ValueError as exc:
        raise ValueError("Geçersiz backup yolu.") from exc
    if not backup_path.exists() or backup_path.suffix.lower() != ".json":
        raise FileNotFoundError("Backup dosyası bulunamadı.")
    backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
    if not isinstance(backup_data, dict):
        raise ValueError("Backup içeriği geçerli bir model JSON dosyası değil.")

    backup_current = ""
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup_path = backup_dir / f"{path.stem}_before_restore_{stamp}{path.suffix}"
        shutil.copy2(path, current_backup_path)
        backup_current = _relative(current_backup_path, project_root)
    path.write_text(json.dumps(backup_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "message": "Model backup dosyasından geri yüklendi.",
        "path": _relative(path, project_root),
        "restored_from": _relative(backup_path, project_root),
        "backup_current": backup_current,
    }

def list_print_templates(project_root: Path) -> list[dict[str, str]]:
    templates_dir = project_root / "templates" / "print"
    templates_dir.mkdir(parents=True, exist_ok=True)
    metadata = _load_print_metadata(project_root)
    rows: list[dict[str, str]] = []
    for path in sorted(templates_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
            continue
        relative = _relative(path, project_root)
        item = metadata.get(relative, {})
        inferred = _infer_print_template_fields(path)
        model_no = str(item.get("model_no") or inferred.get("model_no") or "")
        template_no = str(item.get("template_no") or inferred.get("template_no") or "")
        label_variant = str(item.get("label_variant") or inferred.get("label_variant") or "")
        linked_design = _linked_design_path(project_root, model_no, template_no, label_variant)
        rows.append(
            {
                "file_name": path.name,
                "relative_path": relative,
                "file_type": path.suffix.lower().lstrip(".").upper(),
                "model_no": model_no,
                "template_no": template_no,
                "label_variant": label_variant,
                "status": str(item.get("status") or "AKTİF"),
                "active": str(item.get("active", True)),
                "notes": str(item.get("notes") or ""),
                "linked_label_design": _relative(linked_design, project_root) if linked_design and linked_design.exists() else "",
                "linked_label_design_status": "VAR" if linked_design and linked_design.exists() else "YOK",
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_kb": str(max(1, round(path.stat().st_size / 1024))),
            }
        )
    return rows


def infer_label_model_fields(source_path: Path) -> dict[str, str]:
    inferred = _infer_print_template_fields(source_path)
    return {
        "model_name": source_path.stem.replace("_", " ").replace("-", " ").title(),
        "model_no": inferred.get("model_no", ""),
        "template_no": inferred.get("template_no", "") or "A",
        "label_variant": inferred.get("label_variant", "") or "GOLD",
    }


def get_print_template_detail(project_root: Path, relative_path: str) -> dict[str, str]:
    path = _safe_print_template_path(project_root, relative_path)
    metadata = _load_print_metadata(project_root).get(_relative(path, project_root), {})
    inferred = _infer_print_template_fields(path)
    model_no = str(metadata.get("model_no") or inferred.get("model_no") or "")
    template_no = str(metadata.get("template_no") or inferred.get("template_no") or "")
    label_variant = str(metadata.get("label_variant") or inferred.get("label_variant") or "")
    linked_design = _linked_design_path(project_root, model_no, template_no, label_variant)
    return {
        "file_name": path.name,
        "relative_path": _relative(path, project_root),
        "file_type": path.suffix.lower().lstrip(".").upper(),
        "short_path": _relative(path, project_root),
        "size_kb": str(max(1, round(path.stat().st_size / 1024))),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        "model_no": model_no,
        "template_no": template_no,
        "label_variant": label_variant,
        "active": str(metadata.get("active", True)),
        "notes": str(metadata.get("notes") or ""),
        "linked_label_design": _relative(linked_design, project_root) if linked_design and linked_design.exists() else "",
        "linked_label_design_status": "VAR" if linked_design and linked_design.exists() else "YOK",
    }


def save_print_template_metadata(project_root: Path, relative_path: str, data: dict[str, object]) -> dict[str, str]:
    path = _safe_print_template_path(project_root, relative_path)
    metadata_path = project_root / "templates" / "print" / METADATA_FILE
    metadata = _load_print_metadata(project_root)
    if metadata_path.exists():
        backup_path = project_root / "templates" / "print" / METADATA_BACKUP_FILE
        shutil.copy2(metadata_path, backup_path)
    key = _relative(path, project_root)
    metadata[key] = {
        "model_no": str(data.get("model_no") or "").strip(),
        "template_no": str(data.get("template_no") or "").strip(),
        "label_variant": str(data.get("label_variant") or "").strip().upper(),
        "active": bool(data.get("active", True)),
        "status": "AKTİF" if bool(data.get("active", True)) else "PASİF",
        "notes": str(data.get("notes") or "").strip(),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "OK", "message": "Baskı şablonu bilgileri kaydedildi.", "relative_path": key}


def create_linked_label_design(project_root: Path, relative_path: str) -> dict[str, str]:
    detail = get_print_template_detail(project_root, relative_path)
    model_no = detail.get("model_no", "").strip()
    template_no = detail.get("template_no", "").strip()
    label_variant = detail.get("label_variant", "").strip()
    if not model_no or not template_no or not label_variant:
        return {
            "status": "ERROR",
            "message": "Bağlı etiket tasarımı için önce Model No, Şablon No ve Varyant bilgisini kaydedin.",
        }
    target = _linked_design_path(project_root, model_no, template_no, label_variant)
    if target.exists():
        return {
            "status": "EXISTS",
            "message": "Bağlı etiket tasarımı zaten var.",
            "path": _relative(target, project_root),
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    defaults = _load_label_defaults(project_root)
    width = float(defaults.get("label_width_mm") or 50)
    height = float(defaults.get("label_height_mm") or 30)
    payload = {
        "template_id": f"{model_no}_{template_no}_{label_variant}".lower(),
        "template_name": f"{model_no} {template_no} {label_variant} Rulo Etiket",
        "model_no": model_no,
        "template_no": template_no,
        "label_variant": label_variant,
        "media_type": "ROLL",
        "label_width_mm": width,
        "label_height_mm": height,
        "roll_gap_mm": float(defaults.get("roll_gap_mm") or 3),
        "printer_dpi": int(defaults.get("printer_dpi") or 300),
        "background_image": "",
        "show_order_number_on_label": bool(defaults.get("show_order_number_on_label", False)),
        "fields": [
            {
                "field_name": "İsim",
                "placeholder": "{{LABEL_TEXT}}",
                "excel_column": "label_text",
                "x_mm": 4,
                "y_mm": max((height - 10) / 2, 1),
                "width_mm": max(width - 8, 1),
                "height_mm": 10,
                "font_family": "Segoe UI",
                "font_size": 13,
                "color": "#1F2933",
                "bold": True,
                "italic": False,
                "align": "center",
                "vertical_align": "middle",
            },
        ],
        "elements": [
            {
                "type": "rectangle",
                "id": "border",
                "x_mm": 1,
                "y_mm": 1,
                "width_mm": max(width - 2, 1),
                "height_mm": max(height - 2, 1),
                "stroke_color": "#B9973E",
                "stroke_width": 0.25,
                "fill_color": "#FFFFFF",
                "visible": True,
            },
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "CREATED", "message": "Bağlı etiket tasarımı oluşturuldu.", "path": _relative(target, project_root)}


def set_label_model_preview(project_root: Path, template_path: Path, source_image: Path) -> dict[str, str]:
    suffix = source_image.suffix.lower()
    if suffix in {".cdr", ".ai"}:
        raise ValueError(
            "Bu dosya kaynak tasar\u0131md\u0131r, \u00f6nizleme g\u00f6rseli de\u011fildir. "
            "L\u00fctfen CorelDRAW/Illustrator'dan PNG/JPG/WebP/PDF/SVG olarak d\u0131\u015fa aktar\u0131lm\u0131\u015f \u00f6nizleme dosyas\u0131n\u0131 se\u00e7in."
        )
    if suffix not in PREVIEW_IMAGE_SUFFIXES:
        raise ValueError("\u00d6nizleme i\u00e7in PNG, JPG, JPEG, WEBP, PDF veya SVG se\u00e7in.")
    if not source_image.exists() or not source_image.is_file():
        raise FileNotFoundError("\u00d6nizleme g\u00f6rseli bulunamad\u0131.")
    template_path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(template_path)
    target_dir = project_root / "assets" / "label_backgrounds"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = f"{data.get('model_no', 'model')}_{data.get('template_no', 'template')}_{data.get('label_variant', 'variant')}_preview".lower()
    target_path = target_dir / f"{safe_stem}{source_image.suffix.lower()}"
    if source_image.resolve() != target_path.resolve():
        shutil.copy2(source_image, target_path)
    relative_preview = _relative(target_path, project_root)
    data["preview_image"] = relative_preview
    data["background_image"] = relative_preview
    data["background_enabled"] = suffix in {*RASTER_PREVIEW_SUFFIXES, *VECTOR_PREVIEW_SUFFIXES}
    data["preview_usage"] = "production_background" if data["background_enabled"] else "placement_guide_only"
    data.pop("preview_missing_warning", None)
    data.pop("source_preview_note", None)
    ratio_warning = _preview_quality_warning(
        target_path,
        float(data.get("label_width_mm") or data.get("canvas_width_mm") or 0),
        float(data.get("label_height_mm") or data.get("canvas_height_mm") or 0),
        int(data.get("printer_dpi") or 300),
    )
    _write_template_json_with_backup(template_path, data)
    message = "\u00d6nizleme g\u00f6rseli modele ba\u011fland\u0131."
    if ratio_warning:
        message += f" {ratio_warning}"
    return {
        "status": "OK",
        "message": message,
        "preview_image": relative_preview,
        "background_image": relative_preview,
        "background_enabled": "true" if data["background_enabled"] else "false",
        "preview_usage": str(data.get("preview_usage") or ""),
        "ratio_warning": ratio_warning,
    }


def validate_model_preview(project_root: Path, template_path: Path) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    preview_rel = str(data.get("preview_image") or "")
    background_rel = str(data.get("background_image") or "")
    background_enabled = bool(data.get("background_enabled", False))
    label_width = float(data.get("label_width_mm") or data.get("canvas_width_mm") or 0)
    label_height = float(data.get("label_height_mm") or data.get("canvas_height_mm") or 0)
    expected_ratio = label_width / label_height if label_width > 0 and label_height > 0 else 0
    warnings: list[str] = []
    preview_path = normalize_project_path(project_root, preview_rel) if preview_rel else None
    preview_exists = bool(preview_path and preview_path.exists() and preview_path.is_file())
    image_width = 0
    image_height = 0
    image_ratio = 0.0
    ratio_status = "MISSING"
    preview_url = ""
    image_status = "MISSING"

    if not preview_rel:
        warnings.append(
            "Ger\u00e7ek tasar\u0131m \u00f6nizlemesi yok. AI/CDR dosyas\u0131ndan PNG/JPG/WebP export edip buraya ba\u011flay\u0131n."
        )
    elif not preview_exists:
        warnings.append("\u00d6nizleme dosyas\u0131 bulunamad\u0131.")
    elif preview_path.suffix.lower() not in PREVIEW_IMAGE_SUFFIXES:
        warnings.append("\u00d6nizleme i\u00e7in PNG/JPG/JPEG/WEBP/PDF/SVG se\u00e7in.")
    else:
        preview_url = to_web_file_url(preview_path, project_root)
        if preview_path.suffix.lower() in DOCUMENT_PREVIEW_SUFFIXES:
            ratio_status = "WARNING"
            image_status = "DOCUMENT"
            warnings.append("PDF program i\u00e7inde kaynak/yerle\u015fim rehberi olarak tutulur; bask\u0131 arka plan\u0131 i\u00e7in PNG/JPG/WebP tercih edin.")
        else:
            image_width, image_height, image_status = read_image_size(preview_path)
            if image_status == "VECTOR":
                ratio_status = "OK"
            elif image_status == "UNREADABLE":
                ratio_status = "WARNING"
                warnings.append("\u00d6nizleme g\u00f6rseli okunamad\u0131. Dosya bozuk veya desteklenmiyor olabilir.")
        if image_width > 0 and image_height > 0:
            image_ratio = image_width / image_height
            if expected_ratio > 0 and abs(image_ratio - expected_ratio) / expected_ratio > 0.08:
                ratio_status = "WARNING"
                warnings.append("G\u00f6rsel oran\u0131 etiket \u00f6l\u00e7\u00fcs\u00fcyle tam uyu\u015fmuyor. Yaz\u0131 konumlar\u0131 bask\u0131da kayabilir.")
            else:
                ratio_status = "OK"
            min_width = round((label_width / 25.4) * 300) if label_width > 0 else 0
            min_height = round((label_height / 25.4) * 300) if label_height > 0 else 0
            if min_width and min_height and (image_width < min_width or image_height < min_height):
                warnings.append("Bu g\u00f6rsel bask\u0131 i\u00e7in d\u00fc\u015f\u00fck \u00e7\u00f6z\u00fcn\u00fcrl\u00fckl\u00fc olabilir.")

    if background_enabled and background_rel != preview_rel:
        warnings.append("Arka plan g\u00f6rseli ile \u00f6nizleme g\u00f6rseli farkl\u0131; model ayarlar\u0131n\u0131 kontrol edin.")
    if preview_rel and not background_enabled:
        warnings.append("Arka plan kapal\u0131. Ger\u00e7ek tasar\u0131m\u0131 render i\u00e7in background_enabled a\u00e7\u0131k olmal\u0131.")

    return {
        "status": "OK",
        "has_preview_image": bool(preview_rel),
        "preview_path": preview_rel,
        "preview_exists": preview_exists,
        "preview_url": preview_url,
        "background_enabled": background_enabled,
        "background_image": background_rel,
        "preview_usage": str(data.get("preview_usage") or ("production_background" if background_enabled else "placement_guide_only")),
        "image_width_px": image_width,
        "image_height_px": image_height,
        "image_ratio": round(image_ratio, 4) if image_ratio else 0,
        "expected_ratio": round(expected_ratio, 4) if expected_ratio else 0,
        "image_status": image_status,
        "ratio_status": ratio_status,
        "warnings": warnings,
    }

def cleanup_duplicate_label_text_fields(project_root: Path, template_path: Path) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    fields = data.get("fields") or []
    label_fields = [
        (index, field)
        for index, field in enumerate(fields)
        if str(field.get("excel_column") or "") == "label_text"
    ]
    if len(label_fields) <= 1:
        return {
            "status": "NOOP",
            "message": "Bu modelde tek İsim alanı var; silinecek tekrar alan bulunmadı.",
            "kept_index": label_fields[0][0] if label_fields else -1,
            "deleted_fields": [],
        }

    label_width = float(data.get("label_width_mm") or data.get("canvas_width_mm") or 50)
    label_height = float(data.get("label_height_mm") or data.get("canvas_height_mm") or 30)

    def score(item: tuple[int, dict]) -> tuple[int, float, int]:
        index, field = item
        x = float(field.get("x_mm") or 0)
        y = float(field.get("y_mm") or 0)
        w = float(field.get("width_mm") or 0)
        h = float(field.get("height_mm") or 0)
        in_bounds = x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= label_width and y + h <= label_height
        return (0 if in_bounds else 1, w * h, index)

    kept_index, kept_field = sorted(label_fields, key=score)[0]
    deleted_fields: list[dict[str, object]] = []
    next_fields: list[dict] = []
    for index, field in enumerate(fields):
        if str(field.get("excel_column") or "") == "label_text" and index != kept_index:
            deleted_fields.append(
                {
                    "index": index,
                    "field_name": field.get("field_name", "İsim"),
                    "excel_column": field.get("excel_column", "label_text"),
                    "x_mm": field.get("x_mm"),
                    "y_mm": field.get("y_mm"),
                    "width_mm": field.get("width_mm"),
                    "height_mm": field.get("height_mm"),
                }
            )
            continue
        next_fields.append(field)
    data["fields"] = next_fields
    result = save_template_with_backup(project_root, data, overwrite=True)
    return {
        "status": "OK",
        "message": "Önerilen İsim alanı tutuldu, diğer tekrar İsim alanları silindi.",
        "kept_index": kept_index,
        "kept_field": {
            "field_name": kept_field.get("field_name", "İsim"),
            "excel_column": kept_field.get("excel_column", "label_text"),
            "x_mm": kept_field.get("x_mm"),
            "y_mm": kept_field.get("y_mm"),
            "width_mm": kept_field.get("width_mm"),
            "height_mm": kept_field.get("height_mm"),
        },
        "deleted_fields": deleted_fields,
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
    }


def cleanup_duplicate_note_fields(project_root: Path, template_path: Path) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    fields = data.get("fields") or []
    note_fields = [
        (index, field)
        for index, field in enumerate(fields)
        if str(field.get("excel_column") or "") == "note_text"
    ]
    if len(note_fields) <= 1:
        return {
            "status": "NOOP",
            "message": "Bu modelde tek Not alanı var; silinecek tekrar alan bulunmadı.",
            "kept_index": note_fields[0][0] if note_fields else -1,
            "deleted_fields": [],
        }

    label_width = float(data.get("label_width_mm") or data.get("canvas_width_mm") or 50)
    label_height = float(data.get("label_height_mm") or data.get("canvas_height_mm") or 30)

    def score(item: tuple[int, dict]) -> tuple[int, float, float, int]:
        index, field = item
        x = float(field.get("x_mm") or 0)
        y = float(field.get("y_mm") or 0)
        w = float(field.get("width_mm") or 0)
        h = float(field.get("height_mm") or 0)
        in_bounds = x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= label_width and y + h <= label_height
        center_x = x + (w / 2)
        center_y = y + (h / 2)
        center_distance = abs(center_x - (label_width / 2)) + abs(center_y - (label_height * 0.78))
        return (0 if in_bounds else 1, center_distance, w * h, index)

    kept_index, kept_field = sorted(note_fields, key=score)[0]
    deleted_fields: list[dict[str, object]] = []
    next_fields: list[dict] = []
    for index, field in enumerate(fields):
        if str(field.get("excel_column") or "") == "note_text" and index != kept_index:
            deleted_fields.append(
                {
                    "index": index,
                    "field_name": field.get("field_name", "Not"),
                    "excel_column": field.get("excel_column", "note_text"),
                    "x_mm": field.get("x_mm"),
                    "y_mm": field.get("y_mm"),
                    "width_mm": field.get("width_mm"),
                    "height_mm": field.get("height_mm"),
                }
            )
            continue
        next_fields.append(field)
    data["fields"] = next_fields
    result = save_template_with_backup(project_root, data, overwrite=True)
    return {
        "status": "OK",
        "message": "Önerilen Not alanı tutuldu, diğer tekrar Not alanları silindi.",
        "kept_index": kept_index,
        "kept_field": {
            "field_name": kept_field.get("field_name", "Not"),
            "excel_column": kept_field.get("excel_column", "note_text"),
            "x_mm": kept_field.get("x_mm"),
            "y_mm": kept_field.get("y_mm"),
            "width_mm": kept_field.get("width_mm"),
            "height_mm": kept_field.get("height_mm"),
        },
        "deleted_fields": deleted_fields,
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
    }


def normalize_label_model_preview(project_root: Path, template_path: Path) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    preview_rel = str(data.get("preview_image") or data.get("background_image") or "")
    if not preview_rel:
        return {"status": "ERROR", "message": "Bu modelde normalize edilecek önizleme görseli yok."}
    source = normalize_project_path(project_root, preview_rel)
    if not source.exists() or not source.is_file():
        return {"status": "ERROR", "message": "Önizleme görseli bulunamadı.", "preview_path": preview_rel}
    if source.suffix.lower() not in RASTER_PREVIEW_SUFFIXES:
        return {"status": "ERROR", "message": "Görseli etikete uydurma aracı PNG/JPG/WebP için çalışır."}

    label_width = float(data.get("label_width_mm") or data.get("canvas_width_mm") or 50)
    label_height = float(data.get("label_height_mm") or data.get("canvas_height_mm") or 30)
    dpi = int(data.get("printer_dpi") or 300)
    target_width = max(1, round((label_width / 25.4) * dpi))
    target_height = max(1, round((label_height / 25.4) * dpi))

    image = QImage(str(source))
    if image.isNull():
        return {"status": "ERROR", "message": "Önizleme görseli okunamadı. Dosya bozuk veya desteklenmiyor olabilir."}
    source_width = image.width()
    source_height = image.height()
    scale = min(target_width / source_width, target_height / source_height)
    scaled_width = max(1, round(source_width * scale))
    scaled_height = max(1, round(source_height * scale))
    scaled = image.scaled(scaled_width, scaled_height)

    canvas = QImage(target_width, target_height, QImage.Format.Format_ARGB32)
    canvas.fill(QColor("#ffffff"))
    painter = QPainter(canvas)
    painter.drawImage((target_width - scaled_width) // 2, (target_height - scaled_height) // 2, scaled)
    painter.end()

    normalized_dir = project_root / "assets" / "label_backgrounds" / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    target = normalized_dir / f"{path.stem}_preview_{int(label_width)}x{int(label_height)}.png"
    if not canvas.save(str(target), "PNG"):
        return {"status": "ERROR", "message": "Normalize edilmiş önizleme görseli kaydedilemedi."}

    relative = _relative(target, project_root)
    data["preview_image"] = relative
    data["background_image"] = relative
    data["background_enabled"] = True
    data["preview_usage"] = "production_background"
    result = save_template_with_backup(project_root, data, overwrite=True)
    validation = validate_model_preview(project_root, result.target_path)
    return {
        "status": "OK",
        "message": "Görsel etikete uyduruldu ve modele bağlandı.",
        "normalized_preview": relative,
        "background_enabled": True,
        "source_width_px": source_width,
        "source_height_px": source_height,
        "target_width_px": target_width,
        "target_height_px": target_height,
        "image_ratio": validation.get("image_ratio", 0),
        "expected_ratio": validation.get("expected_ratio", 0),
        "ratio_status": validation.get("ratio_status", ""),
        "warnings": validation.get("warnings", []),
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
        "preview_url": validation.get("preview_url", ""),
    }


def create_label_model_from_source(
    project_root: Path,
    source_path: Path,
    data: dict[str, object],
    preview_image: Path | None = None,
    overwrite: bool = False,
) -> dict[str, str]:
    if not source_path.exists():
        raise FileNotFoundError(f"Kaynak dosya bulunamadı: {source_path}")
    if source_path.suffix.lower() not in MODEL_SOURCE_SUFFIXES:
        raise ValueError("Etiket modeli için CDR, AI, PDF, SVG, PNG, JPG, JPEG veya WEBP dosyası seçin.")

    model_no = str(data.get("model_no") or "").strip()
    template_no = str(data.get("template_no") or "").strip().upper()
    label_variant = str(data.get("label_variant") or "").strip().upper()
    model_name = str(data.get("model_name") or "").strip() or f"Model {model_no}"
    if not model_no or not template_no or not label_variant:
        raise ValueError("Model No, Şablon No ve Varyant zorunludur.")

    defaults = _load_label_defaults(project_root)
    width = float(data.get("label_width_mm") or defaults.get("label_width_mm") or 50)
    height = float(data.get("label_height_mm") or defaults.get("label_height_mm") or 30)
    if width <= 0 or height <= 0:
        raise ValueError("Etiket genişliği ve yüksekliği 0'dan büyük olmalıdır.")

    source_relative = _store_model_source(project_root, source_path, overwrite=overwrite)
    preview_relative = _store_or_find_preview(project_root, source_path, preview_image)
    target = _linked_design_path(project_root, model_no, template_no, label_variant)
    if target.exists() and not overwrite:
        return {
            "status": "EXISTS",
            "message": "Bu model JSON dosyası zaten var. Üzerine yazmak için onay gerekir.",
            "path": _relative(target, project_root),
        }

    payload = _default_label_model_payload(
        model_no=model_no,
        template_no=template_no,
        label_variant=label_variant,
        model_name=model_name,
        source_file=source_relative,
        preview_image=preview_relative,
        width=width,
        height=height,
        active=bool(data.get("active", True)),
        defaults=defaults,
    )
    _write_template_json_with_backup(target, payload)
    if source_path.suffix.lower() in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
        save_print_template_metadata(
            project_root,
            source_relative,
            {
                "model_no": model_no,
                "template_no": template_no,
                "label_variant": label_variant,
                "active": bool(data.get("active", True)),
                "notes": "Etiket Model Kütüphanesi üzerinden eklendi.",
            },
        )
    return {
        "status": "CREATED",
        "message": "Etiket modeli oluşturuldu. CDR/AI kaynak dosyası değiştirilmedi.",
        "path": _relative(target, project_root),
        "source_file": source_relative,
        "preview_image": preview_relative,
    }


def create_label_model_from_wizard(project_root: Path, data: dict[str, object], design_visual: Path) -> dict[str, str]:
    if not design_visual.exists() or not design_visual.is_file():
        raise FileNotFoundError("Tasarım görseli bulunamadı.")
    suffix = design_visual.suffix.lower()
    if suffix in {".cdr", ".ai"}:
        raise ValueError("Bu dosya kaynak tasarımdır, önizleme görseli değildir. Lütfen PNG/JPG/WebP/SVG/PDF seçin.")
    if suffix not in PREVIEW_IMAGE_SUFFIXES:
        raise ValueError("Tasarım görseli için PNG, JPG, JPEG, WebP, SVG veya PDF seçin.")

    defaults = _load_label_defaults(project_root)
    width = float(data.get("label_width_mm") or defaults.get("label_width_mm") or 50)
    height = float(data.get("label_height_mm") or defaults.get("label_height_mm") or 30)
    width = max(10.0, min(300.0, width))
    height = max(10.0, min(300.0, height))
    model_name = str(data.get("model_name") or "").strip()
    if not model_name:
        raise ValueError("Model adı yazın.")
    label_variant = str(data.get("label_variant") or "GOLD").strip().upper() or "GOLD"
    template_no = "A"
    model_no = _next_model_no(project_root)
    target = _linked_design_path(project_root, model_no, template_no, label_variant)
    preview_relative = _store_wizard_design_visual(project_root, design_visual, model_no, template_no, label_variant)
    payload = _default_label_model_payload(
        model_no=model_no,
        template_no=template_no,
        label_variant=label_variant,
        model_name=model_name,
        source_file="",
        preview_image=preview_relative,
        width=width,
        height=height,
        active=bool(data.get("active", True)),
        defaults=defaults,
    )
    payload["background_enabled"] = suffix in {*RASTER_PREVIEW_SUFFIXES, *VECTOR_PREVIEW_SUFFIXES}
    payload["preview_usage"] = "production_background" if payload["background_enabled"] else "placement_guide_only"
    _write_template_json_with_backup(target, payload)
    return {
        "status": "CREATED",
        "message": "Yeni etiket modeli oluşturuldu. İsim, Tarih ve Not alanları hazır eklendi.",
        "path": _relative(target, project_root),
        "preview_image": preview_relative,
    }


def clone_label_model_variant(project_root: Path, template_path: Path, data: dict[str, object]) -> dict[str, str]:
    source_path = _safe_design_template_path(project_root, template_path)
    source = load_template_data(source_path)
    defaults = _load_label_defaults(project_root)

    model_name = str(data.get("model_name") or f"{source.get('model_name') or source.get('template_name') or 'Etiket Modeli'} Kopya").strip()
    if not model_name:
        raise ValueError("Model adı yazın.")

    model_no = str(data.get("model_no") or "").strip() or _next_model_no(project_root)
    template_no = str(data.get("template_no") or source.get("template_no") or "A").strip() or "A"
    label_variant = str(data.get("label_variant") or source.get("label_variant") or "CUSTOM").strip().upper() or "CUSTOM"
    model_no = re.sub(r"[^0-9A-Za-z_-]+", "", model_no) or _next_model_no(project_root)
    template_no = re.sub(r"[^0-9A-Za-z_-]+", "", template_no) or "A"
    label_variant = re.sub(r"[^0-9A-Za-z_-]+", "_", label_variant).strip("_").upper() or "CUSTOM"

    use_source_size = bool(data.get("use_source_size", True))
    width = float(source.get("label_width_mm") or defaults.get("label_width_mm") or 50) if use_source_size else float(data.get("label_width_mm") or 50)
    height = float(source.get("label_height_mm") or defaults.get("label_height_mm") or 30) if use_source_size else float(data.get("label_height_mm") or 30)
    width = max(10.0, min(300.0, width))
    height = max(10.0, min(300.0, height))

    target = _linked_design_path(project_root, model_no, template_no, label_variant)
    if target.exists():
        raise FileExistsError("Bu model no/varyant için güvenli JSON zaten var. Farklı model no veya varyant seçin.")

    payload = copy.deepcopy(source)
    payload.update(
        {
            "template_id": f"{model_no}_{template_no}_{label_variant}".lower(),
            "template_name": model_name,
            "model_name": model_name,
            "model_no": model_no,
            "template_no": template_no,
            "label_variant": label_variant,
            "label_width_mm": width,
            "label_height_mm": height,
            "active": bool(data.get("active", True)),
        }
    )
    payload["fields"] = copy.deepcopy(source.get("fields") or _default_basic_fields(width, height))
    payload["elements"] = copy.deepcopy(source.get("elements") or [])
    payload["source_clone_of"] = _relative(source_path, project_root)
    payload["clone_created_at"] = datetime.now().isoformat(timespec="seconds")
    design_visual_value = str(data.get("design_visual_path") or "").strip()
    if design_visual_value:
        design_visual = Path(design_visual_value)
        suffix = design_visual.suffix.lower()
        if suffix in {".cdr", ".ai"}:
            raise ValueError("Kaynak AI/CDR dosyası varyant görseli olarak bağlanamaz. PNG/JPG/WebP/SVG/PDF seçin.")
        if suffix not in PREVIEW_IMAGE_SUFFIXES:
            raise ValueError("Varyant görseli için PNG, JPG, JPEG, WebP, SVG veya PDF seçin.")
        if not design_visual.exists() or not design_visual.is_file():
            raise FileNotFoundError("Seçilen varyant görseli bulunamadı.")
        preview_relative = _store_wizard_design_visual(project_root, design_visual, model_no, template_no, label_variant)
        payload["preview_image"] = preview_relative
        payload["background_image"] = preview_relative
        payload["background_enabled"] = True
        payload["preview_usage"] = "design_background"

    _write_template_json_with_backup(target, payload)
    return {
        "status": "CREATED",
        "message": "Model varyantı güvenli şekilde oluşturuldu. Kaynak AI/CDR ve görsel dosyaları değiştirilmedi.",
        "path": _relative(target, project_root),
        "source_path": _relative(source_path, project_root),
        "preview_image": str(payload.get("preview_image") or payload.get("background_image") or ""),
    }


def save_label_template(project_root: Path, data: dict, overwrite: bool = False):
    return save_template_with_backup(project_root, data, overwrite=overwrite)


def save_label_model_field(project_root: Path, template_path: Path, index: int, field_data: dict[str, object]) -> dict[str, str]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    fields = data.setdefault("fields", [])
    if index < 0 or index >= len(fields):
        raise ValueError("Düzenlenecek yazı alanı bulunamadı.")
    current = fields[index]
    current.update(
        {
            "x_mm": float(field_data.get("x_mm") or 0),
            "y_mm": float(field_data.get("y_mm") or 0),
            "width_mm": float(field_data.get("width_mm") or 0),
            "height_mm": float(field_data.get("height_mm") or 0),
            "font_family": str(field_data.get("font_family") or "Segoe UI"),
            "font_path": str(field_data.get("font_path") or ""),
            "font_size": float(field_data.get("font_size") or 1),
            "line_height": float(field_data.get("line_height") or current.get("line_height") or 1.18),
            "color": str(field_data.get("color") or "#111111"),
            "align": str(field_data.get("align") or "center"),
            "vertical_align": str(field_data.get("vertical_align") or "middle"),
            "bold": bool(field_data.get("bold", False)),
            "italic": bool(field_data.get("italic", False)),
        }
    )
    font_warning = check_font_turkish_support(project_root, str(current.get("font_path") or ""))
    result = save_template_with_backup(project_root, data, overwrite=True)
    return {
        "status": "OK",
        "message": "Yazı alanı kaydedildi.",
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
        "font_warning": font_warning,
    }


def add_label_model_field(project_root: Path, template_path: Path, field_type: str) -> dict[str, object]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    normalized = {
        "label_text": "name",
        "date_text": "date",
        "note_text": "note",
        "custom_text_1": "custom",
        "name": "name",
        "date": "date",
        "note": "note",
        "custom": "custom",
    }.get(field_type, field_type)
    if normalized not in {"name", "date", "note", "custom"}:
        raise ValueError("Eklenebilecek alan tipi bulunamad\u0131.")
    field = add_variable_field(data, normalized)
    result = save_template_with_backup(project_root, data, overwrite=True)
    return {
        "status": "OK",
        "message": "Yaz\u0131 alan\u0131 eklendi.",
        "field": field,
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
    }


def remove_label_model_field(project_root: Path, template_path: Path, index: int) -> dict[str, str]:
    path = _safe_design_template_path(project_root, template_path)
    data = load_template_data(path)
    remove_variable_field(data, index)
    result = save_template_with_backup(project_root, data, overwrite=True)
    return {
        "status": "OK",
        "message": "Yaz\u0131 alan\u0131 silindi.",
        "path": _relative(result.target_path, project_root),
        "backup_path": _relative(result.backup_path, project_root) if result.backup_path else "",
    }


def import_label_font(project_root: Path, source_font: Path) -> dict[str, str]:
    relative_path = import_font_file(project_root, source_font, overwrite=False)
    warning = check_font_turkish_support(project_root, relative_path)
    return {
        "status": "OK",
        "message": "Font y\u00fcklendi.",
        "font_path": relative_path,
        "font_family": source_font.stem.replace("_", " ").replace("-", " ").title(),
        "font_warning": warning,
    }


def check_font_turkish_support(project_root: Path, font_path: str) -> str:
    if not font_path:
        return ""
    path = (project_root / font_path).resolve()
    try:
        path.relative_to((project_root / "assets" / "fonts").resolve())
    except ValueError:
        return "Font dosyası assets/fonts içinde değil; güvenli fallback font kullanılabilir."
    if not path.exists():
        return "Font dosyası bulunamadı; güvenli fallback font kullanılabilir."
    turkish_chars = "çÇğĞıİöÖşŞüÜ"
    try:
        from fontTools.ttLib import TTFont  # type: ignore

        font = TTFont(str(path))
        codepoints: set[int] = set()
        for table in font["cmap"].tables:
            codepoints.update(table.cmap.keys())
        missing = [char for char in turkish_chars if ord(char) not in codepoints]
        if missing:
            return "Seçilen font bazı Türkçe karakterleri desteklemeyebilir: " + " ".join(missing)
        return ""
    except Exception:
        return "Seçilen font bazı Türkçe karakterleri desteklemeyebilir. Test önizlemesini kontrol edin."


def import_template_pack(project_root: Path, zip_path: Path):
    return safe_extract_template_pack(zip_path, project_root)


def import_print_template_file(project_root: Path, source_path: Path, overwrite: bool = False) -> dict[str, str]:
    if not source_path.exists():
        raise FileNotFoundError(f"Şablon dosyası bulunamadı: {source_path}")
    if source_path.suffix.lower() not in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
        raise ValueError("Baskı şablonu için sadece .cdr, .ai, .pdf veya .svg kabul edilir.")

    target_dir = project_root / "templates" / "print"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source_path.name
    if target_path.exists() and not overwrite:
        return {
            "status": "SKIPPED_EXISTS",
            "source_path": str(source_path),
            "target_path": str(target_path),
            "warning": "Dosya zaten var, atlandı.",
        }

    shutil.copy2(source_path, target_path)
    return {
        "status": "IMPORTED",
        "source_path": str(source_path),
        "target_path": str(target_path),
        "warning": "",
    }


def _store_model_source(project_root: Path, source_path: Path, overwrite: bool = False) -> str:
    suffix = source_path.suffix.lower()
    if suffix in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
        result = import_print_template_file(project_root, source_path, overwrite=overwrite)
        if result["status"] == "SKIPPED_EXISTS":
            return _relative(project_root / "templates" / "print" / source_path.name, project_root)
        return _relative(Path(result["target_path"]), project_root)
    target_dir = project_root / "assets" / "label_backgrounds"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source_path.name
    if target_path.exists() and not overwrite:
        return _relative(target_path, project_root)
    if source_path.resolve() != target_path.resolve():
        shutil.copy2(source_path, target_path)
    return _relative(target_path, project_root)


def _store_or_find_preview(project_root: Path, source_path: Path, preview_image: Path | None) -> str:
    target_dir = project_root / "assets" / "label_backgrounds"
    target_dir.mkdir(parents=True, exist_ok=True)
    if preview_image:
        if preview_image.suffix.lower() not in PREVIEW_IMAGE_SUFFIXES:
            raise ValueError("Önizleme için PNG, JPG, JPEG, WEBP, PDF veya SVG seçin.")
        target_path = target_dir / f"{source_path.stem}_preview{preview_image.suffix.lower()}"
        if preview_image.resolve() != target_path.resolve():
            shutil.copy2(preview_image, target_path)
        return _relative(target_path, project_root)
    if source_path.suffix.lower() in PREVIEW_IMAGE_SUFFIXES:
        return _relative(project_root / _store_model_source(project_root, source_path, overwrite=False), project_root)
    for suffix in PREVIEW_IMAGE_SUFFIXES:
        candidate = target_dir / f"{source_path.stem}_preview{suffix}"
        if candidate.exists():
            return _relative(candidate, project_root)
    return ""


def _store_wizard_design_visual(project_root: Path, source_path: Path, model_no: str, template_no: str, label_variant: str) -> str:
    target_dir = project_root / "assets" / "label_backgrounds"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = f"{model_no}_{template_no}_{label_variant}_preview".lower().replace(" ", "_")
    target_path = target_dir / f"{safe_stem}{source_path.suffix.lower()}"
    if source_path.resolve() != target_path.resolve():
        shutil.copy2(source_path, target_path)
    return _relative(target_path, project_root)


def _next_model_no(project_root: Path) -> str:
    numbers: list[int] = []
    for item in list_label_templates(project_root):
        raw = str(item.get("model_no") or "").strip()
        if raw.isdigit():
            numbers.append(int(raw))
    next_number = (max(numbers) + 1) if numbers else 1
    return f"{next_number:02d}"


def _default_label_model_payload(
    *,
    model_no: str,
    template_no: str,
    label_variant: str,
    model_name: str,
    source_file: str,
    preview_image: str,
    width: float,
    height: float,
    active: bool,
    defaults: dict[str, object],
) -> dict[str, object]:
    return {
        "template_id": f"{model_no}_{template_no}_{label_variant}".lower(),
        "template_name": model_name,
        "model_name": model_name,
        "model_no": model_no,
        "template_no": template_no,
        "label_variant": label_variant,
        "source_file": source_file,
        "preview_image": preview_image,
        "media_type": "ROLL",
        "label_width_mm": width,
        "label_height_mm": height,
        "roll_gap_mm": float(defaults.get("roll_gap_mm") or 3),
        "printer_dpi": int(defaults.get("printer_dpi") or 300),
        "background_image": preview_image,
        "background_enabled": bool(preview_image),
        "show_order_number_on_label": bool(defaults.get("show_order_number_on_label", False)),
        "active": active,
        "fields": _default_basic_fields(width, height),
        "elements": [],
    }


def _default_basic_fields(width: float, height: float) -> list[dict[str, object]]:
    return [
        {
            "field_name": "İsim",
            "placeholder": "{{LABEL_TEXT}}",
            "excel_column": "label_text",
            "x_mm": round(width * 0.2, 2),
            "y_mm": round(height * 0.28, 2),
            "width_mm": round(width * 0.6, 2),
            "height_mm": max(4.0, round(height * 0.2, 2)),
            "font_family": "Segoe UI",
            "font_size": 14,
            "line_height": 1.18,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
        {
            "field_name": "Tarih",
            "placeholder": "{{DATE_TEXT}}",
            "excel_column": "date_text",
            "x_mm": round(width * 0.34, 2),
            "y_mm": round(height * 0.56, 2),
            "width_mm": round(width * 0.32, 2),
            "height_mm": max(3.0, round(height * 0.13, 2)),
            "font_family": "Segoe UI",
            "font_size": 8,
            "line_height": 1.18,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
        {
            "field_name": "Not",
            "placeholder": "{{NOTE_TEXT}}",
            "excel_column": "note_text",
            "x_mm": round(width * 0.24, 2),
            "y_mm": round(height * 0.7, 2),
            "width_mm": round(width * 0.52, 2),
            "height_mm": max(3.0, round(height * 0.13, 2)),
            "font_family": "Segoe UI",
            "font_size": 8,
            "line_height": 1.18,
            "color": "#111111",
            "align": "center",
            "vertical_align": "middle",
            "bold": False,
            "italic": False,
        },
    ]


def _safe_print_template_path(project_root: Path, relative_path: str) -> Path:
    base = (project_root / "templates" / "print").resolve()
    path = (project_root / relative_path).resolve() if not Path(relative_path).is_absolute() else Path(relative_path).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Geçersiz baskı şablonu yolu.")
    if not path.exists() or path.suffix.lower() not in ALLOWED_PRINT_TEMPLATE_SUFFIXES:
        raise FileNotFoundError("Baskı şablonu bulunamadı.")
    return path


def _safe_design_template_path(project_root: Path, template_path: Path) -> Path:
    base = (project_root / "templates" / "designs").resolve()
    path = template_path.resolve() if template_path.is_absolute() else (project_root / template_path).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Geçersiz etiket modeli yolu.")
    if not path.exists() or path.suffix.lower() != ".json":
        raise FileNotFoundError("Etiket modeli JSON dosyası bulunamadı.")
    return path


def _load_print_metadata(project_root: Path) -> dict[str, dict[str, object]]:
    metadata_path = project_root / "templates" / "print" / METADATA_FILE
    if not metadata_path.exists():
        return {}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _load_label_defaults(project_root: Path) -> dict[str, object]:
    settings_path = project_root / "config" / "settings.yaml"
    try:
        data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}
    defaults = data.get("label_defaults") if isinstance(data, dict) else {}
    return defaults if isinstance(defaults, dict) else {}


def _infer_print_template_fields(path: Path) -> dict[str, str]:
    stem = path.stem
    normalized = stem.lower().replace("-", " ").replace("_", " ")
    parts = normalized.split()
    model_no = next((part for part in parts if part.isdigit()), "")
    variant = ""
    for key in ("gold", "silver", "white", "red", "custom"):
        if key in parts or key in normalized:
            variant = key.upper()
            break
    template_no = ""
    for part in parts:
        if len(part) == 1 and part.isalpha():
            template_no = part.upper()
            break
    return {"model_no": model_no, "template_no": template_no, "label_variant": variant}


def _elements_to_fields(elements: list[object]) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    for element in elements:
        if isinstance(element, dict) and element.get("type") == "text":
            fields.append(element)
    return fields


def _asset_uri(project_root: Path, relative_path: str) -> str:
    if not relative_path:
        return ""
    return to_web_file_url(normalize_project_path(project_root, relative_path), project_root)


def _preview_ratio_warning(image_path: Path, label_width_mm: float, label_height_mm: float) -> str:
    return _preview_quality_warning(image_path, label_width_mm, label_height_mm, 300)


def _preview_quality_warning(image_path: Path, label_width_mm: float, label_height_mm: float, dpi: int = 300) -> str:
    if label_width_mm <= 0 or label_height_mm <= 0:
        return ""
    if image_path.suffix.lower() in DOCUMENT_PREVIEW_SUFFIXES:
        return "PDF önizleme yerleşim rehberi olarak bağlandı; baskı arka planı için PNG/JPG/WebP tercih edin."
    width_px, height_px, status = read_image_size(image_path)
    if status in {"VECTOR", "DOCUMENT"}:
        return ""
    if status == "UNREADABLE":
        return ""
    if width_px <= 0 or height_px <= 0:
        return ""
    image_ratio = width_px / height_px
    label_ratio = label_width_mm / label_height_mm
    if abs(image_ratio - label_ratio) / label_ratio > 0.08:
        return "Görsel oranı etiket ölçüsüyle tam uyuşmuyor."
    min_width = round((label_width_mm / 25.4) * dpi)
    min_height = round((label_height_mm / 25.4) * dpi)
    if width_px < min_width or height_px < min_height:
        return "Bu görsel baskı için düşük çözünürlüklü olabilir."
    return ""


def _source_preview_note(source_file: str) -> str:
    suffix = Path(source_file).suffix.lower()
    if suffix in {".ai", ".cdr"}:
        return "Bu dosya türü program içinde doğrudan önizlenemiyor. Önizleme için aynı tasarımın PNG/JPG/PDF görselini seçin."
    return ""


def _fields_summary(fields: list[dict]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in fields:
        excel_column = str(field.get("excel_column") or "")
        rows.append(
            {
                "field_name": str(field.get("field_name") or field.get("id") or "Yazı alanı"),
                "field_type": _field_type_for_column(excel_column),
                "excel_column": excel_column,
                "x_mm": str(field.get("x_mm") or ""),
                "y_mm": str(field.get("y_mm") or ""),
                "width_mm": str(field.get("width_mm") or ""),
                "height_mm": str(field.get("height_mm") or ""),
                "font_family": str(field.get("font_family") or ""),
                "font_path": str(field.get("font_path") or ""),
                "font_size": str(field.get("font_size") or ""),
                "line_height": str(field.get("line_height") or ""),
                "color": str(field.get("color") or ""),
            }
        )
    return rows


def normalize_project_path(project_root: Path, value: str | Path) -> Path:
    raw = unquote(str(value or "")).strip()
    if raw.startswith("file:///"):
        raw = raw[8:]
        if re.match(r"^[A-Za-z]:", raw):
            raw = raw.replace("/", "\\")
    path = Path(raw)
    if not path.is_absolute():
        path = project_root / raw
    return path.resolve()


def read_image_size(path: Path) -> tuple[int, int, str]:
    suffix = path.suffix.lower()
    if suffix in DOCUMENT_PREVIEW_SUFFIXES:
        return 0, 0, "DOCUMENT"
    if suffix in VECTOR_PREVIEW_SUFFIXES:
        width, height = _read_svg_size(path)
        return width, height, "VECTOR"
    if not path.exists() or not path.is_file():
        return 0, 0, "MISSING"
    try:
        width, height = _read_raster_header_size(path)
        if width > 0 and height > 0:
            return width, height, "OK"
    except Exception:
        pass
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as image:
            width, height = image.size
        if width > 0 and height > 0:
            return int(width), int(height), "OK"
    except Exception:
        pass
    try:
        from PySide6.QtGui import QImage  # type: ignore

        image = QImage(str(path))
        if not image.isNull():
            return int(image.width()), int(image.height()), "OK"
    except Exception:
        pass
    return 0, 0, "UNREADABLE"


def _read_raster_header_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            length = int.from_bytes(data[index:index + 2], "big")
            if length < 2:
                break
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and index + 7 < len(data):
                height = int.from_bytes(data[index + 3:index + 5], "big")
                width = int.from_bytes(data[index + 5:index + 7], "big")
                return width, height
            index += length
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if chunk == b"VP8 " and len(data) >= 30:
            return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
        if chunk == b"VP8L" and len(data) >= 25:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return 0, 0


def _read_svg_size(path: Path) -> tuple[int, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:2000]
    except Exception:
        return 0, 0
    width_match = re.search(r'\bwidth=["\']([0-9.]+)', text)
    height_match = re.search(r'\bheight=["\']([0-9.]+)', text)
    if width_match and height_match:
        return int(float(width_match.group(1))), int(float(height_match.group(1)))
    view_box = re.search(r'\bviewBox=["\']\s*[-0-9.]+\s+[-0-9.]+\s+([0-9.]+)\s+([0-9.]+)', text)
    if view_box:
        return int(float(view_box.group(1))), int(float(view_box.group(2)))
    return 0, 0


def _duplicate_field_warnings(fields: list[dict]) -> list[str]:
    counts: dict[str, int] = {}
    for field in fields:
        column = str(field.get("excel_column") or "")
        if column:
            counts[column] = counts.get(column, 0) + 1
    warnings: list[str] = []
    for column, count in counts.items():
        if count > 1:
            warnings.append(f"Bu modelde birden fazla {_field_type_for_column(column)} alanı var. Gereksiz olanı silebilirsiniz.")
    return warnings


def _field_type_for_column(column: str) -> str:
    return {
        "label_text": "İsim",
        "date_text": "Tarih",
        "note_text": "Not",
        "custom_text_1": "Özel Metin 1",
        "custom_text_2": "Özel Metin 2",
        "custom_text_3": "Özel Metin 3",
    }.get(column, "Yazı Alanı")


def _linked_design_path(project_root: Path, model_no: str, template_no: str, label_variant: str) -> Path:
    safe_name = f"{model_no}_{template_no}_{label_variant}".strip("_").lower()
    return project_root / "templates" / "designs" / f"{safe_name}.json"


def _relative(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except Exception:
        return path.name


def _write_template_json_with_backup(template_path: Path, data: dict[str, object]) -> None:
    backup_dir = template_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if template_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(template_path, backup_dir / f"{template_path.stem}_{stamp}{template_path.suffix}")
    template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
