from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from label_designer.manual_label_service import render_manual_label, render_manual_preview  # noqa: E402
from label_designer.template_loader import load_template  # noqa: E402
from webui_backend.pdf_preview_api import get_pdf_preview_payload  # noqa: E402
from webui_backend.print_queue_api import add_pdf_output_to_queue, list_print_queue  # noqa: E402


LABEL_TEXT = "Ayşe & Mehmet QA"
DATE_TEXT = "15.05.26"
NOTE_TEXT = "Nişan hatırası"
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "designs" / "01_a_gold.json"
RUN_DATE = date.today()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _ = app

    template = load_template(TEMPLATE_PATH)
    background = PROJECT_ROOT / (template.background_image or template.preview_image)
    started_at = datetime.now().timestamp()
    payload = {
        "_studio_render_state": "true",
        "_background_image": background.resolve().as_uri(),
        "_preview_image": background.resolve().as_uri(),
        "_fields": template.fields,
        "_label_width_mm": template.label_width_mm,
        "_label_height_mm": template.label_height_mm,
        "label_text": LABEL_TEXT,
        "date_text": DATE_TEXT,
        "note_text": NOTE_TEXT,
        "custom_text_1": "",
        "custom_text_2": "",
        "custom_text_3": "",
    }

    preview = render_manual_preview(PROJECT_ROOT, TEMPLATE_PATH, LABEL_TEXT, RUN_DATE, payload)
    final = render_manual_label(PROJECT_ROOT, TEMPLATE_PATH, LABEL_TEXT, 1, RUN_DATE, payload)
    relative_pdf = final.batch_pdf_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    queue_result = add_pdf_output_to_queue(PROJECT_ROOT, relative_pdf)
    pdf_payload = get_pdf_preview_payload(PROJECT_ROOT, relative_pdf)

    evidence_dir = PROJECT_ROOT / "output" / RUN_DATE.isoformat() / "quality_gate"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf_page_path = evidence_dir / "quality_gate_pdf_page.png"
    pdf_preview_pages = pdf_payload.get("preview_pages") or []
    if pdf_preview_pages:
        first_page = PROJECT_ROOT / str(pdf_preview_pages[0]["preview_png_path"])
        image = QImage(str(first_page))
        if not image.isNull():
            image.save(str(pdf_page_path), "PNG")

    png_validation = validate_rendered_image(final.png_path, template.fields)
    pdf_validation = validate_rendered_image(pdf_page_path, template.fields) if pdf_page_path.exists() else {"status": "FAILED", "reason": "PDF page preview missing"}
    preview_validation = validate_rendered_image(preview.png_path, template.fields)

    queue_rows = list_print_queue(PROJECT_ROOT)
    queued = next((row for row in queue_rows if row.get("relative_path") == relative_pdf), None)
    result = {
        "status": "PASSED" if all(item["status"] == "PASSED" for item in [png_validation, pdf_validation, preview_validation]) and queued else "FAILED",
        "model": "01 A Gold Rulo Etiket",
        "template_path": str(TEMPLATE_PATH),
        "input_values": {
            "label_text": LABEL_TEXT,
            "date_text": DATE_TEXT,
            "note_text": NOTE_TEXT,
        },
        "background_path": str(background),
        "live_canvas_screenshot": str(PROJECT_ROOT / "output" / RUN_DATE.isoformat() / "ui_screenshots" / "manuel_etiket.png"),
        "render_preview_png_path": str(preview.png_path),
        "final_png_path": str(final.png_path),
        "final_pdf_path": str(final.pdf_path),
        "batch_pdf_path": str(final.batch_pdf_path),
        "pdf_preview_page_path": str(pdf_page_path),
        "queue_relative_path": relative_pdf if queued else "",
        "queue_result": queue_result,
        "pdf_preview_payload": {
            "status": pdf_payload.get("status"),
            "page_count": pdf_payload.get("page_count"),
            "preview_pages": pdf_preview_pages,
        },
        "validations": {
            "png": png_validation,
            "pdf_page": pdf_validation,
            "real_preview": preview_validation,
            "files_are_fresh": {
                "status": "PASSED" if all(path.stat().st_mtime >= started_at for path in [preview.png_path, final.png_path, final.pdf_path, final.batch_pdf_path]) else "FAILED",
                "started_at": started_at,
            },
        },
    }

    result_path = evidence_dir / "REAL_PRODUCTION_QUALITY_GATE_RESULT.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASSED" else 1


def validate_rendered_image(path: Path, fields: list[dict]) -> dict[str, object]:
    if not path.exists():
        return {"status": "FAILED", "reason": "file missing", "path": str(path)}
    if path.stat().st_size < 10_000:
        return {"status": "FAILED", "reason": "file too small", "path": str(path), "size": path.stat().st_size}
    image = QImage(str(path))
    if image.isNull():
        return {"status": "FAILED", "reason": "image unreadable", "path": str(path)}

    colorful_pixels = 0
    dark_pixels = 0
    total = 0
    for x in range(0, image.width(), max(1, image.width() // 90)):
        for y in range(0, image.height(), max(1, image.height() // 60)):
            color = QColor(image.pixel(x, y))
            total += 1
            if max(color.red(), color.green(), color.blue()) - min(color.red(), color.green(), color.blue()) > 45:
                colorful_pixels += 1
            if color.red() < 95 and color.green() < 95 and color.blue() < 95:
                dark_pixels += 1

    field_results = {}
    for field in fields:
        column = str(field.get("excel_column") or "")
        if column not in {"label_text", "date_text", "note_text"}:
            continue
        field_results[column] = dark_pixels_in_field(image, field)

    min_field_dark = min(field_results.values()) if field_results else 0
    status = "PASSED"
    reason = ""
    if colorful_pixels < max(10, total * 0.01):
        status = "FAILED"
        reason = "background image/color detail missing"
    elif dark_pixels < 5:
        status = "FAILED"
        reason = "text-like dark pixels missing"
    elif min_field_dark < 1:
        status = "FAILED"
        reason = "one or more text fields missing"

    return {
        "status": status,
        "reason": reason,
        "path": str(path),
        "size": path.stat().st_size,
        "width": image.width(),
        "height": image.height(),
        "colorful_pixels": colorful_pixels,
        "dark_pixels": dark_pixels,
        "field_dark_pixels": field_results,
    }


def dark_pixels_in_field(image: QImage, field: dict) -> int:
    label_width_mm = 50.0
    label_height_mm = 30.0
    x0 = max(0, int(float(field.get("x_mm", 0)) / label_width_mm * image.width()))
    y0 = max(0, int(float(field.get("y_mm", 0)) / label_height_mm * image.height()))
    x1 = min(image.width(), int((float(field.get("x_mm", 0)) + float(field.get("width_mm", 0))) / label_width_mm * image.width()))
    y1 = min(image.height(), int((float(field.get("y_mm", 0)) + float(field.get("height_mm", 0))) / label_height_mm * image.height()))
    count = 0
    step_x = max(1, (x1 - x0) // 40)
    step_y = max(1, (y1 - y0) // 20)
    for x in range(x0, x1, step_x):
        for y in range(y0, y1, step_y):
            color = QColor(image.pixel(x, y))
            if color.red() < 120 and color.green() < 120 and color.blue() < 120:
                count += 1
    return count


if __name__ == "__main__":
    raise SystemExit(main())
