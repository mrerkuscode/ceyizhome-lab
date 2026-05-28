from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
import re
import sys

from PySide6.QtWidgets import QApplication

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from config_loader import load_settings
from models import Order, PRINT

from .pdf_exporter import export_label_pdf, export_roll_batch_pdf
from .preview_exporter import export_label_png
from .settings_resolver import resolve_label_settings
from .template_loader import load_template
from .template_schema import LabelElement


@dataclass(frozen=True)
class ManualLabelResult:
    output_dir: Path
    pdf_path: Path
    png_path: Path
    batch_pdf_path: Path
    quantity: int


@dataclass(frozen=True)
class ManualPreviewResult:
    output_dir: Path
    png_path: Path


def render_manual_label(
    project_root: Path,
    template_path: Path,
    label_text: str,
    quantity: int,
    run_date: date | None = None,
    field_values: dict[str, str] | None = None,
) -> ManualLabelResult:
    if QApplication.instance() is None:
        _ = QApplication([])
    run_date = run_date or date.today()
    if quantity <= 0:
        raise ValueError("Adet 0'dan büyük olmalıdır.")
    if not label_text.strip():
        raise ValueError("Etiket yazısı boş olamaz.")

    settings = load_settings(project_root / "config" / "settings.yaml")
    template = load_template(template_path)
    template = _apply_studio_render_overrides(project_root, template, field_values or {})
    label_settings = resolve_label_settings(template, settings)
    label_settings = _apply_label_size_override(label_settings, field_values or {})
    output_dir = project_root / "output" / run_date.strftime(settings.app.output_date_format) / "print" / "manual"
    output_dir.mkdir(parents=True, exist_ok=True)

    order = _manual_order(template, label_text.strip(), quantity, field_values or {})
    safe_name = _manual_output_stem(run_date, template, label_text, label_settings.label_width_mm, label_settings.label_height_mm, quantity)
    pdf_path = _unique_output_path(output_dir / f"{safe_name}.pdf")
    png_path = _unique_output_path(output_dir / f"{safe_name}.png")
    batch_pdf_path = _unique_output_path(output_dir / f"{safe_name}_batch.pdf")

    export_label_pdf(pdf_path, template, order, run_date, template.source_file.parent, label_settings)
    export_label_png(png_path, template, order, run_date, template.source_file.parent, label_settings)
    export_roll_batch_pdf(batch_pdf_path, template, [(order, quantity)], run_date, template.source_file.parent, label_settings)

    return ManualLabelResult(
        output_dir=output_dir,
        pdf_path=pdf_path,
        png_path=png_path,
        batch_pdf_path=batch_pdf_path,
        quantity=quantity,
    )


def render_manual_preview(
    project_root: Path,
    template_path: Path,
    label_text: str,
    run_date: date | None = None,
    field_values: dict[str, str] | None = None,
) -> ManualPreviewResult:
    if QApplication.instance() is None:
        _ = QApplication([])
    run_date = run_date or date.today()

    settings = load_settings(project_root / "config" / "settings.yaml")
    template = load_template(template_path)
    template = _apply_studio_render_overrides(project_root, template, field_values or {})
    label_settings = resolve_label_settings(template, settings)
    label_settings = _apply_label_size_override(label_settings, field_values or {})
    output_dir = project_root / "output" / run_date.strftime(settings.app.output_date_format) / "preview" / "manual_label"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_text = label_text.strip() or "Ayse_Mehmet"
    order = _manual_order(template, safe_text, 1, field_values or {})
    png_path = output_dir / f"manual_preview_{template.template_id}_{_safe_file_name(safe_text)}.png"
    export_label_png(png_path, template, order, run_date, template.source_file.parent, label_settings)

    return ManualPreviewResult(output_dir=output_dir, png_path=png_path)


def _manual_order(template, label_text: str, quantity: int, field_values: dict[str, str]) -> Order:
    source = {
        "label_text": label_text,
        "date_text": field_values.get("date_text", ""),
        "note_text": field_values.get("note_text", ""),
        "custom_text_1": field_values.get("custom_text_1", ""),
        "custom_text_2": field_values.get("custom_text_2", ""),
        "custom_text_3": field_values.get("custom_text_3", ""),
    }
    return Order(
        row_number=0,
        order_no="MANUAL",
        buyer_name="Manuel",
        product_name="Manuel Rulo Etiket",
        model_no=template.model_no,
        template_no=template.template_no,
        process_type=PRINT,
        personalization_type="LABEL",
        label_variant=template.label_variant,
        label_text=label_text,
        laser_text="",
        quantity=quantity,
        material_type="",
        material_thickness_mm="",
        extra_chocolate_qty=0,
        extra_madlen_qty=0,
        production_note="",
        needs_review="",
        status="NEW",
        source=source,
    )


def _apply_studio_render_overrides(project_root: Path, template, field_values: dict[str, object]):
    if str(field_values.get("_studio_render_state", "")).lower() != "true":
        return template
    background = str(field_values.get("_background_image") or field_values.get("_preview_image") or template.preview_image or template.background_image or "")
    background = _background_value_for_renderer(project_root, background)
    if not background:
        raise ValueError("Tasarım görseli bulunamadı. Lütfen bu model için tasarım görseli bağlayın.")
    fields = _studio_fields(field_values.get("_fields"), template.fields)
    if not fields:
        raise ValueError("Etiket yazıları çıktıya aktarılamadı. Modelde İsim, Tarih veya Not alanı bulunamadı.")
    width = _safe_float(field_values.get("_label_width_mm")) or template.label_width_mm or template.canvas_width_mm
    height = _safe_float(field_values.get("_label_height_mm")) or template.label_height_mm or template.canvas_height_mm
    return replace(
        template,
        canvas_width_mm=width,
        canvas_height_mm=height,
        label_width_mm=width,
        label_height_mm=height,
        background_enabled=True,
        background_image=background,
        preview_image=background,
        fields=fields,
        elements=_fields_to_text_elements(fields),
    )


def _background_value_for_renderer(project_root: Path, value: str) -> str:
    if not value:
        return ""
    path = _resolve_project_or_file_path(project_root, value)
    if not path.exists() or not path.is_file():
        return ""
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _resolve_project_or_file_path(project_root: Path, value: str) -> Path:
    raw = str(value or "").strip()
    if raw.startswith("file:///"):
        from urllib.parse import unquote

        raw = unquote(raw[8:])
        if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]
        raw = raw.replace("/", "\\")
    path = Path(raw)
    if not path.is_absolute():
        path = project_root / raw
    return path.resolve()


def _studio_fields(raw_fields, fallback_fields: list[dict]) -> list[dict]:
    source = raw_fields if isinstance(raw_fields, list) and raw_fields else fallback_fields
    fields: list[dict] = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, dict):
            continue
        column = str(item.get("excel_column") or "").strip()
        if column not in {"label_text", "date_text", "note_text"}:
            continue
        if column in seen:
            continue
        seen.add(column)
        field = dict(item)
        if not str(field.get("placeholder") or "").strip():
            field["placeholder"] = "{{" + column.upper() + "}}"
        if not str(field.get("field_name") or "").strip():
            field["field_name"] = {"label_text": "İsim", "date_text": "Tarih", "note_text": "Not"}[column]
        field["visible"] = field.get("visible", True) is not False
        fields.append(field)
    return fields


def _fields_to_text_elements(fields: list[dict]) -> list[LabelElement]:
    elements: list[LabelElement] = []
    for index, field in enumerate(fields, start=1):
        raw = {
            "type": "text",
            "id": str(field.get("id") or field.get("field_name") or f"field_{index}"),
            "placeholder": str(field.get("placeholder") or "{{" + str(field.get("excel_column") or "label_text").upper() + "}}"),
            "x_mm": field.get("x_mm", 0),
            "y_mm": field.get("y_mm", 0),
            "width_mm": field.get("width_mm", 10),
            "height_mm": field.get("height_mm", 5),
            "font_family": field.get("font_family", "Segoe UI"),
            "font_path": field.get("font_path", ""),
            "font_size": field.get("font_size", 10),
            "line_height": field.get("line_height", 1.18),
            "color": field.get("color", "#111111"),
            "bold": field.get("bold", False),
            "italic": field.get("italic", False),
            "align": field.get("align", "center"),
            "vertical_align": field.get("vertical_align", "middle"),
            "rotation": field.get("rotation", 0),
            "visible": field.get("visible", True),
            "excel_column": field.get("excel_column", ""),
            "field_name": str(field.get("field_name", "")),
        }
        elements.append(LabelElement(type="text", raw=raw))
    return elements


def _apply_label_size_override(label_settings, field_values: dict[str, str]):
    width = _safe_float(field_values.get("_label_width_mm"))
    height = _safe_float(field_values.get("_label_height_mm"))
    if width is None or height is None:
        return label_settings
    if not (10 <= width <= 300 and 10 <= height <= 300):
        return label_settings
    return replace(
        label_settings,
        label_width_mm=width,
        label_height_mm=height,
        used_settings_source="STUDIO_OVERRIDE",
        warning=(label_settings.warning + " Etiket Studio geçici ölçü kullanıldı.").strip(),
    )


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_file_name(value: str) -> str:
    safe = value.strip().translate(str.maketrans("çÇöÖüÜıİğĞşŞ", "cCoOuUiIgGsS"))
    safe = "".join(char if char.isalnum() else "_" for char in safe)
    safe = "_".join(part for part in safe.split("_") if part)
    return safe[:60] or "etiket"


def _manual_output_stem(run_date: date, template, label_text: str, width_mm: float, height_mm: float, quantity: int) -> str:
    model_name = getattr(template, "template_name", "") or getattr(template, "model_name", "") or f"{template.model_no}_{template.template_no}_{template.label_variant}"
    raw = f"{run_date:%Y-%m-%d}_{model_name}_{label_text}_{width_mm:g}x{height_mm:g}_{quantity}adet"
    safe = raw.translate(str.maketrans("çÇöÖüÜıİğĞşŞ", "cCoOuUiIgGsS"))
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", safe).strip("-")
    return safe[:100] or "etiket"


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Benzersiz çıktı dosyası adı üretilemedi: {path.name}")
