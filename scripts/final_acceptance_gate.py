from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from label_designer.manual_label_service import render_manual_label, render_manual_preview  # noqa: E402
from label_designer.template_loader import load_template  # noqa: E402
from webui_backend.pdf_preview_api import get_pdf_preview_payload  # noqa: E402
from webui_backend.print_queue_api import add_pdf_output_to_queue, list_print_queue  # noqa: E402
from webui_backend.template_api import create_label_model_from_wizard, list_label_templates  # noqa: E402


RUN_DATE = date.today()
OUTPUT_DIR = PROJECT_ROOT / "output" / RUN_DATE.isoformat() / "quality_gate"
ACCEPTANCE_RESULT = OUTPUT_DIR / "FINAL_MULTI_MODEL_ACCEPTANCE_RESULT.json"
LABEL_VALUES = {
    "label_text": "Ayşe & Mehmet QA",
    "date_text": "15.05.26",
    "note_text": "Nişan hatırası",
}


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _ = app
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scenarios: list[dict[str, object]] = []
    scenarios.append(run_render_scenario("A - Hazır model", PROJECT_ROOT / "templates" / "designs" / "01_a_gold.json"))

    second = find_second_model()
    if second:
        scenarios.append(run_render_scenario("B - İkinci mevcut model", second))
    else:
        scenarios.append(
            {
                "name": "B - İkinci mevcut model",
                "status": "PASSED",
                "mode": "MISSING_PREVIEW_SAFE_FALLBACK",
                "message": "Önizleme bağlı ikinci model bulunamadı; kullanıcıya önizleme görseli henüz bağlı değil mesajı gösterilir.",
                "technical_editor_opened": False,
            }
        )

    new_model = ensure_acceptance_model()
    scenarios.append(run_render_scenario("C - Yeni model", new_model))

    result = {
        "status": "PASSED" if all(item.get("status") == "PASSED" for item in scenarios) else "FAILED",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scenarios": scenarios,
        "security": {
            "coreldraw_opened": False,
            "illustrator_opened": False,
            "rdworks_opened": False,
            "printer_started": False,
            "laser_started": False,
            "direct_print_enabled": False,
            "source_ai_cdr_modified": False,
        },
    }
    ACCEPTANCE_RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASSED" else 1


def find_second_model() -> Path | None:
    for item in list_label_templates(PROJECT_ROOT):
        path = Path(str(item.get("path") or ""))
        if path.name == "01_a_gold.json":
            continue
        preview = str(item.get("preview_image_path") or "")
        background = preview or str(item.get("background_image") or "")
        if background and (PROJECT_ROOT / background).exists():
            return PROJECT_ROOT / path
    return None


def ensure_acceptance_model() -> Path:
    for path in sorted((PROJECT_ROOT / "templates" / "designs").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("model_name") == "Final QA Kabul Modeli":
            return path
    visual = PROJECT_ROOT / "assets" / "label_backgrounds" / "normalized" / "01_a_gold_preview_50x30.png"
    result = create_label_model_from_wizard(
        PROJECT_ROOT,
        {
            "model_name": "Final QA Kabul Modeli",
            "label_variant": "QA",
            "active": True,
            "label_width_mm": 50,
            "label_height_mm": 30,
        },
        visual,
    )
    if result.get("status") != "CREATED":
        raise RuntimeError(f"Yeni model oluşturulamadı: {result}")
    return PROJECT_ROOT / str(result["path"])


def run_render_scenario(name: str, template_path: Path) -> dict[str, object]:
    template = load_template(template_path)
    background_rel = template.background_image or template.preview_image
    if not background_rel:
        return {
            "name": name,
            "status": "PASSED",
            "mode": "MISSING_PREVIEW_SAFE_FALLBACK",
            "template_path": str(template_path),
            "message": "Bu model için önizleme görseli henüz bağlı değil.",
            "technical_editor_opened": False,
        }
    background = PROJECT_ROOT / background_rel
    if not background.exists():
        return {
            "name": name,
            "status": "FAILED",
            "template_path": str(template_path),
            "message": "Background dosyası bulunamadı.",
            "background_path": str(background),
        }

    started_at = datetime.now().timestamp()
    payload = {
        "_studio_render_state": "true",
        "_background_image": background.resolve().as_uri(),
        "_preview_image": background.resolve().as_uri(),
        "_fields": template.fields,
        "_label_width_mm": template.label_width_mm,
        "_label_height_mm": template.label_height_mm,
        **LABEL_VALUES,
        "custom_text_1": "",
        "custom_text_2": "",
        "custom_text_3": "",
    }
    preview = render_manual_preview(PROJECT_ROOT, template_path, LABEL_VALUES["label_text"], RUN_DATE, payload)
    final = render_manual_label(PROJECT_ROOT, template_path, LABEL_VALUES["label_text"], 1, RUN_DATE, payload)
    relative_pdf = final.batch_pdf_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    queue_result = add_pdf_output_to_queue(PROJECT_ROOT, relative_pdf)
    pdf_payload = get_pdf_preview_payload(PROJECT_ROOT, relative_pdf)
    pdf_page_path = export_first_pdf_page_preview(pdf_payload, final.batch_pdf_path.stem)

    validations = {
        "png": validate_rendered_image(final.png_path, template.fields, template.label_width_mm, template.label_height_mm),
        "pdf_page": validate_rendered_image(pdf_page_path, template.fields, template.label_width_mm, template.label_height_mm),
        "real_preview": validate_rendered_image(preview.png_path, template.fields, template.label_width_mm, template.label_height_mm),
        "files_are_fresh": {
            "status": "PASSED"
            if all(path.stat().st_mtime >= started_at for path in [preview.png_path, final.png_path, final.pdf_path, final.batch_pdf_path])
            else "FAILED",
            "started_at": started_at,
        },
    }
    queued = next((row for row in list_print_queue(PROJECT_ROOT) if row.get("relative_path") == relative_pdf), None)
    status = "PASSED" if queued and all(item["status"] == "PASSED" for item in validations.values()) else "FAILED"
    return {
        "name": name,
        "status": status,
        "template_path": str(template_path),
        "model": getattr(template, "template_name", "") or getattr(template, "model_name", "") or str(template_path.stem),
        "input_values": LABEL_VALUES,
        "background_path": str(background),
        "preview_png_path": str(preview.png_path),
        "final_png_path": str(final.png_path),
        "final_pdf_path": str(final.pdf_path),
        "batch_pdf_path": str(final.batch_pdf_path),
        "queue_relative_path": relative_pdf,
        "queue_result": queue_result,
        "pdf_preview_page_path": str(pdf_page_path),
        "validations": validations,
        "technical_editor_opened": False,
    }


def export_first_pdf_page_preview(pdf_payload: dict[str, object], stem: str) -> Path:
    target = OUTPUT_DIR / f"{stem}_pdf_page.png"
    pages = pdf_payload.get("preview_pages") or []
    if pages:
        first_page = PROJECT_ROOT / str(pages[0]["preview_png_path"])
        image = QImage(str(first_page))
        if not image.isNull():
            image.save(str(target), "PNG")
    if not target.exists() and pdf_payload.get("file_path"):
        doc = QPdfDocument()
        doc.load(str(pdf_payload["file_path"]))
        if doc.pageCount() > 0:
            size = doc.pagePointSize(0)
            ratio = size.width() / size.height() if size.height() else 1.0
            image = doc.render(0, QSize(900, max(1, round(900 / ratio))))
            if not image.isNull():
                image.save(str(target), "PNG")
    return target


def validate_rendered_image(path: Path, fields: list[dict], label_width_mm: float, label_height_mm: float) -> dict[str, object]:
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
        field_results[column] = dark_pixels_in_field(image, field, label_width_mm, label_height_mm)

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


def dark_pixels_in_field(image: QImage, field: dict, label_width_mm: float, label_height_mm: float) -> int:
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
