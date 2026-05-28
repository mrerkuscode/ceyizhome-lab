from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from label_designer.renderer import measure_text_fit
from label_designer.template_loader import load_template

from .pdf_preview_api import get_pdf_preview_payload


BASIC_COLUMNS = {"label_text", "date_text", "note_text"}


def preflight_manual_label(project_root: Path, template_path: Path, payload: dict[str, object], quantity: int) -> dict[str, object]:
    if QApplication.instance() is None:
        _ = QApplication([])
    errors: list[str] = []
    warnings: list[str] = []
    fixes: list[str] = []
    model_path = _safe_template_path(project_root, template_path)
    if not model_path or not model_path.exists():
        errors.append("Önce bir model seçin.")
        return _result("ERROR", errors, warnings, fixes)

    template = load_template(model_path)
    width = _safe_float(payload.get("_label_width_mm")) or template.label_width_mm or template.canvas_width_mm
    height = _safe_float(payload.get("_label_height_mm")) or template.label_height_mm or template.canvas_height_mm
    if not (10 <= width <= 300 and 10 <= height <= 300):
        errors.append("Etiket ölçüsü geçerli değil. Genişlik ve yükseklik 10-300 mm arasında olmalı.")

    background = _resolve_background(project_root, payload, template)
    if not background:
        errors.append("Bu model için tasarım görseli bağlı değil.")

    fields = _visible_fields(payload, template.fields)
    columns = [str(field.get("excel_column") or "") for field in fields]
    for column, label in [("label_text", "İsim"), ("date_text", "Tarih"), ("note_text", "Not")]:
        if column not in columns:
            errors.append(f"{label} yazı alanı görünür değil.")

    if columns.count("note_text") > 1:
        warnings.append("Bu modelde birden fazla Not alanı var. Çıktıda yalnızca ilk Not alanı kullanılacak.")
        fixes.append("Duplicate Not alanlarını temizleyin.")

    output_dir = project_root / "output" / datetime.now().strftime("%Y-%m-%d") / "print" / "manual"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception:
        errors.append("Çıktı klasörüne yazılamıyor.")

    if quantity <= 0:
        errors.append("Adet 1 veya daha büyük olmalı.")

    for field in fields:
        column = str(field.get("excel_column") or "")
        if column not in BASIC_COLUMNS:
            continue
        x = _safe_float(field.get("x_mm")) or 0
        y = _safe_float(field.get("y_mm")) or 0
        w = _safe_float(field.get("width_mm")) or 0
        h = _safe_float(field.get("height_mm")) or 0
        font_size = _safe_float(field.get("font_size")) or 0
        label = _column_label(column)
        if w < 2 or h < 2:
            errors.append(f"{label} yazı alanı çok küçük.")
        if x < 0 or y < 0 or x + w > width or y + h > height:
            errors.append(f"{label} yazı alanı etiket sınırının dışında.")
            fixes.append("Alanları etiket içine alın.")
        if font_size < 5:
            warnings.append(f"{label} yazı boyutu çok küçük görünebilir.")
        text = str(payload.get(column) or "").strip()
        if column == "label_text" and not text:
            errors.append("İsim metni boş. Çıktı oluşturmak için isim zorunludur.")
        elif column in {"date_text", "note_text"} and not text:
            warnings.append(f"{label} metni boş.")
        if text:
            fit_status, final_size, warning = measure_text_fit(field, text)
            if fit_status == "ERROR_TOO_SMALL":
                errors.append(f"{label} metni kutuya sığmıyor.")
                fixes.append("Fontu otomatik küçültün veya alanı genişletin.")
            elif fit_status == "SHRUNK":
                warnings.append(warning or f"{label} metni için font küçültme gerekebilir.")
                fixes.append("Fontu otomatik küçültün.")

    status = "ERROR" if errors else "WARNING" if warnings else "OK"
    return _result(status, errors, warnings, fixes)


def validate_manual_output(project_root: Path, render_result: dict[str, object], payload: dict[str, object]) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    started_at = _safe_float(payload.get("_render_started_at")) or 0

    png_path = _safe_output_path(project_root, str(render_result.get("png_path") or ""))
    pdf_path = _safe_output_path(project_root, str(render_result.get("batch_pdf_path") or render_result.get("pdf_path") or ""))
    if not png_path or not png_path.exists():
        errors.append("PNG dosyası oluşturulamadı.")
    if not pdf_path or not pdf_path.exists():
        errors.append("PDF dosyası oluşturulamadı.")

    fields = _visible_fields(payload, [])
    png_validation = _validate_image_file(png_path, fields, payload) if png_path and png_path.exists() else {}
    if png_validation.get("status") == "ERROR":
        errors.extend(png_validation.get("errors", []))

    pdf_validation: dict[str, object] = {}
    if pdf_path and pdf_path.exists():
        pdf_payload = get_pdf_preview_payload(project_root, pdf_path)
        pages = pdf_payload.get("preview_pages") if isinstance(pdf_payload, dict) else []
        if pages:
            first = pages[0]
            preview_path = _safe_output_path(project_root, str(first.get("preview_png_path") or ""))
            pdf_validation = _validate_image_file(preview_path, fields, payload, label_prefix="PDF")
            if pdf_validation.get("status") == "ERROR":
                errors.extend(pdf_validation.get("errors", []))
        else:
            errors.append("PDF program içi önizleme sayfası üretilemedi.")

    for path in [png_path, pdf_path]:
        if path and path.exists() and started_at and path.stat().st_mtime < started_at:
            errors.append(f"{path.name} eski/stale çıktı gibi görünüyor.")

    status = "ERROR" if errors else "OK"
    return {
        "status": status,
        "message": "Çıktı canvas ile uyumlu görünüyor." if status == "OK" else "Çıktı canvas ile eşleşmedi. Lütfen tekrar oluşturun veya model görselini kontrol edin.",
        "errors": errors,
        "warnings": warnings,
        "png": png_validation,
        "pdf": pdf_validation,
    }


def append_production_history(
    project_root: Path,
    template_path: Path,
    payload: dict[str, object],
    quantity: int,
    render_result: dict[str, object],
    preflight: dict[str, object],
    validation: dict[str, object],
    queue_result: dict[str, object] | None = None,
) -> dict[str, object]:
    history_path = project_root / "data" / "production_history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_json_list(history_path)
    template = load_template(_safe_template_path(project_root, template_path) or template_path)
    record = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_name": getattr(template, "template_name", "") or getattr(template, "model_name", "") or template.template_id,
        "model_id": template.template_id,
        "model_path": _relative(_safe_template_path(project_root, template_path) or template_path, project_root),
        "label_text": str(payload.get("label_text") or ""),
        "date_text": str(payload.get("date_text") or ""),
        "note_text": str(payload.get("note_text") or ""),
        "quantity": str(quantity),
        "width_mm": str(payload.get("_label_width_mm") or template.label_width_mm),
        "height_mm": str(payload.get("_label_height_mm") or template.label_height_mm),
        "pdf_path": str(render_result.get("batch_pdf_path") or render_result.get("pdf_path") or ""),
        "png_path": str(render_result.get("png_path") or ""),
        "queue_status": str((queue_result or {}).get("status") or "NOT_QUEUED"),
        "preflight_status": str(preflight.get("status") or ""),
        "output_validation_status": str(validation.get("status") or ""),
    }
    rows.append(record)
    history_path.write_text(json.dumps(rows[-500:], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "OK", "message": "Üretim geçmişine kaydedildi.", "record": record, "path": _relative(history_path, project_root)}


def list_production_history(project_root: Path) -> list[dict[str, object]]:
    return list(reversed(_read_json_list(project_root / "data" / "production_history.json")))[0:100]


def model_health_for_template(project_root: Path, template_path: Path) -> dict[str, object]:
    path = _safe_template_path(project_root, template_path)
    if not path or not path.exists():
        return {"status": "Taslak", "class": "warn", "messages": ["Model dosyası bulunamadı."]}
    template = load_template(path)
    messages: list[str] = []
    fields = template.fields
    columns = [str(field.get("excel_column") or "") for field in fields]
    background = _resolve_background(project_root, {}, template)
    if not background:
        messages.append("Görsel eksik")
    for column, label in [("label_text", "İsim"), ("date_text", "Tarih"), ("note_text", "Not")]:
        if column not in columns:
            messages.append(f"{label} alanı eksik")
    if len(columns) != len(set(columns)):
        messages.append("Duplicate alan var")
    if template.label_width_mm <= 0 or template.label_height_mm <= 0:
        messages.append("Ölçü uyuşmazlığı var")
    status = "Hazır" if not messages else messages[0]
    return {"status": status, "class": "ok" if not messages else "warn", "messages": messages}


def _result(status: str, errors: list[str], warnings: list[str], fixes: list[str]) -> dict[str, object]:
    return {
        "status": status,
        "can_render": status != "ERROR",
        "message": "Çıktı hazır." if status == "OK" else "Kontrol gereken noktalar var." if status == "WARNING" else "Çıktı oluşturulmadan önce düzeltilmesi gereken sorunlar var.",
        "errors": errors,
        "warnings": warnings,
        "auto_fixes": list(dict.fromkeys(fixes)),
    }


def _validate_image_file(path: Path | None, fields: list[dict], payload: dict[str, object], label_prefix: str = "PNG") -> dict[str, object]:
    errors: list[str] = []
    if not path or not path.exists():
        return {"status": "ERROR", "errors": [f"{label_prefix} önizleme dosyası bulunamadı."]}
    if path.stat().st_size < 2048:
        errors.append(f"{label_prefix} dosya boyutu çok küçük.")
    image = QImage(str(path))
    if image.isNull():
        return {"status": "ERROR", "errors": [f"{label_prefix} görüntüsü okunamadı."]}
    colorful = 0
    dark = 0
    step_x = max(1, image.width() // 90)
    step_y = max(1, image.height() // 60)
    for x in range(0, image.width(), step_x):
        for y in range(0, image.height(), step_y):
            color = QColor(image.pixel(x, y))
            if max(color.red(), color.green(), color.blue()) - min(color.red(), color.green(), color.blue()) > 55:
                colorful += 1
            if color.red() < 115 and color.green() < 115 and color.blue() < 115:
                dark += 1
    if colorful < 20:
        errors.append(f"{label_prefix} içinde tasarım/background görünmüyor.")
    if dark < 8:
        errors.append(f"{label_prefix} içinde etiket yazıları görünmüyor.")
    field_dark: dict[str, int] = {}
    width_mm = _safe_float(payload.get("_label_width_mm")) or 50
    height_mm = _safe_float(payload.get("_label_height_mm")) or 30
    for field in fields:
        column = str(field.get("excel_column") or "")
        text = str(payload.get(column) or "").strip()
        if column not in BASIC_COLUMNS or not text:
            continue
        margin_x = max(6, image.width() // 80)
        margin_y = max(4, image.height() // 80)
        x0 = max(0, int((_safe_float(field.get("x_mm")) or 0) / width_mm * image.width()) - margin_x)
        y0 = max(0, int((_safe_float(field.get("y_mm")) or 0) / height_mm * image.height()) - margin_y)
        x1 = min(image.width(), int(((_safe_float(field.get("x_mm")) or 0) + (_safe_float(field.get("width_mm")) or 1)) / width_mm * image.width()) + margin_x)
        y1 = min(image.height(), int(((_safe_float(field.get("y_mm")) or 0) + (_safe_float(field.get("height_mm")) or 1)) / height_mm * image.height()) + margin_y)
        count = _dark_pixels_for_rect(image, x0, y0, x1, y1)
        field_dark[column] = count
        if count <= 0:
            errors.append(f"{label_prefix} içinde {_column_label(column)} metni görünmüyor.")
    return {
        "status": "ERROR" if errors else "OK",
        "errors": errors,
        "path": str(path),
        "size": path.stat().st_size,
        "width": image.width(),
        "height": image.height(),
        "colorful_pixels": colorful,
        "dark_pixels": dark,
        "field_dark_pixels": field_dark,
    }


def _dark_pixels_for_rect(image: QImage, x0: int, y0: int, x1: int, y1: int) -> int:
    if x1 <= x0 or y1 <= y0:
        return 0
    count = 0
    step_x = max(1, (x1 - x0) // 35)
    step_y = max(1, (y1 - y0) // 18)
    for x in range(x0, x1, step_x):
        for y in range(y0, y1, step_y):
            color = QColor(image.pixel(x, y))
            if color.red() < 130 and color.green() < 130 and color.blue() < 130:
                count += 1
    return count


def _visible_fields(payload: dict[str, object], fallback_fields: list[dict]) -> list[dict]:
    raw = payload.get("_fields")
    source = raw if isinstance(raw, list) and raw else fallback_fields
    fields: list[dict] = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, dict):
            continue
        column = str(item.get("excel_column") or "")
        if column not in BASIC_COLUMNS:
            continue
        if column in seen:
            continue
        seen.add(column)
        if item.get("visible", True) is False:
            continue
        fields.append(dict(item))
    return fields


def _resolve_background(project_root: Path, payload: dict[str, object], template) -> Path | None:
    value = str(payload.get("_background_image") or payload.get("_preview_image") or template.preview_image or template.background_image or "")
    if not value:
        return None
    path = _resolve_project_or_file_path(project_root, value)
    return path if path.exists() and path.is_file() else None


def _safe_template_path(project_root: Path, template_path: Path) -> Path | None:
    candidate = template_path if template_path.is_absolute() else project_root / template_path
    try:
        resolved = candidate.resolve()
        resolved.relative_to((project_root / "templates" / "designs").resolve())
        return resolved
    except Exception:
        return None


def _safe_output_path(project_root: Path, value: str) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = project_root / value
    try:
        resolved = candidate.resolve()
        resolved.relative_to((project_root / "output").resolve())
        return resolved
    except Exception:
        return None


def _resolve_project_or_file_path(project_root: Path, value: str) -> Path:
    raw = unquote(str(value or "").strip())
    if raw.startswith("file:///"):
        raw = raw[8:]
        if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
        raw = raw.replace("/", "\\")
    path = Path(raw)
    if not path.is_absolute():
        path = project_root / raw
    return path.resolve()


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _column_label(column: str) -> str:
    return {"label_text": "İsim", "date_text": "Tarih", "note_text": "Not"}.get(column, "Yazı")


def _read_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.name


def safe_output_stem(run_date: datetime, model_name: str, label_text: str, width_mm: float, height_mm: float, quantity: int) -> str:
    raw = f"{run_date:%Y-%m-%d}_{model_name}_{label_text}_{width_mm:g}x{height_mm:g}_{quantity}adet"
    translit = str.maketrans("çÇöÖüÜıİğĞşŞ", "cCoOuUiIgGsS")
    safe = raw.translate(translit)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", safe).strip("-")
    return safe[:95] or "etiket"
