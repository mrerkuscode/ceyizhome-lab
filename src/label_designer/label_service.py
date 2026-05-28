from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QApplication

from excel_reader import read_orders_excel
from models import BOTH, PRINT, AppSettings, Order, ValidationIssue
from validators import validate_and_build_orders

from .pdf_exporter import export_label_pdf, export_roll_batch_pdf
from .placeholder_resolver import resolve_placeholders
from .preview_exporter import export_label_png
from .renderer import measure_text_fit
from .settings_resolver import LabelSettingsError, resolve_label_settings
from .template_loader import LabelTemplateError, find_template
from .template_schema import LabelElement, LabelTemplate, ResolvedLabelSettings


_QAPP: QApplication | None = None


@dataclass(frozen=True)
class LabelRenderResult:
    report_path: Path
    report_paths: list[Path]
    rows: list[dict[str, str]]


def render_labels_from_excel(settings: AppSettings, input_excel: Path, run_date: date) -> LabelRenderResult:
    _ensure_qapplication()
    dataframe = read_orders_excel(input_excel)
    valid_orders, issues = validate_and_build_orders(dataframe, settings)
    rows: list[dict[str, str]] = [_issue_to_row(issue) for issue in issues]

    print_orders = [order for order in valid_orders if order.process_type in {PRINT, BOTH}]
    templates_dir = settings.project_root / "templates" / "designs"
    run_dir = settings.output_dir / run_date.strftime(settings.app.output_date_format)
    batch_groups: dict[tuple[str, str, str, str], list[tuple[Order, LabelTemplate, ResolvedLabelSettings, int]]] = {}

    for order in print_orders:
        row, batch_item = _render_order(order, templates_dir, run_dir, run_date, settings)
        rows.append(row)
        if batch_item is not None:
            template, label_settings, copies = batch_item
            key = (order.model_no, order.template_no, order.label_variant, str(template.source_file))
            batch_groups.setdefault(key, []).append((order, template, label_settings, copies))

    rows.extend(_write_roll_batches(batch_groups, run_dir, run_date))

    report_path = run_dir / "print" / "label_render_report.csv"
    _write_report(report_path, rows)
    report_paths = [report_path]
    report_paths.extend(_write_model_reports(run_dir, rows))
    _write_label_settings_report(run_dir / "reports" / "label_settings_report.csv", rows)
    return LabelRenderResult(report_path=report_path, report_paths=report_paths, rows=rows)


def _render_order(
    order: Order,
    templates_dir: Path,
    run_dir: Path,
    run_date: date,
    settings: AppSettings,
) -> tuple[dict[str, str], tuple[LabelTemplate, ResolvedLabelSettings, int] | None]:
    model_dir = run_dir / "print" / f"model_{order.model_no}" / "rendered"
    try:
        template = find_template(templates_dir, order.model_no, order.template_no, order.label_variant)
    except LabelTemplateError as exc:
        return _row(order, "", "", "", "ERROR", str(exc)), None

    if template is None:
        return _row(order, "", "", "", "ERROR", "Label design template bulunamadı veya birden fazla eşleşme var."), None

    missing_field_columns = _missing_field_columns(template, order)
    if missing_field_columns:
        return _row(
            order,
            str(template.source_file),
            "",
            "",
            "ERROR",
            "Etiket modelindeki alanlar Excel içinde bulunamadı: " + ", ".join(missing_field_columns),
        ), None

    try:
        label_settings = resolve_label_settings(template, settings)
    except LabelSettingsError as exc:
        return _row(order, str(template.source_file), "", "", "ERROR", str(exc)), None

    output_pdf = model_dir / f"order_{order.order_no}.pdf"
    output_png = model_dir / f"order_{order.order_no}.png"
    copies = _copies_for_order(order, label_settings)
    try:
        export_label_pdf(output_pdf, template, order, run_date, template.source_file.parent, label_settings)
        export_label_png(output_png, template, order, run_date, template.source_file.parent, label_settings)
    except Exception as exc:  # noqa: BLE001 - production-friendly render error.
        return _row(
            order,
            str(template.source_file),
            str(output_pdf),
            str(output_png),
            "ERROR",
            f"Label render hatası: {exc}",
            label_settings,
            copies=copies,
        ), None

    text_fit_status, final_font_size, render_warning = _text_fit_diagnostics(template, order, run_date, label_settings)
    combined_warning = _join_warnings(label_settings.warning, render_warning)
    return _row(
        order,
        str(template.source_file),
        str(output_pdf),
        str(output_png),
        "OK",
        combined_warning,
        label_settings,
        copies=copies,
        text_fit_status=text_fit_status,
        final_font_size=final_font_size,
        render_warning=render_warning,
    ), (template, label_settings, copies)


def _write_roll_batches(
    batch_groups: dict[tuple[str, str, str, str], list[tuple[Order, LabelTemplate, ResolvedLabelSettings, int]]],
    run_dir: Path,
    run_date: date,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (model_no, template_no, label_variant, _template_file), items in batch_groups.items():
        if not items:
            continue
        first_order, template, label_settings, _copies = items[0]
        model_dir = run_dir / "print" / f"model_{model_no}" / "rendered"
        batch_pdf = model_dir / f"roll_batch_{model_no}_{template_no}_{label_variant}.pdf"
        order_copies = [(order, copies) for order, _template, _settings, copies in items]
        try:
            export_roll_batch_pdf(batch_pdf, template, order_copies, run_date, template.source_file.parent, label_settings)
        except Exception as exc:  # noqa: BLE001
            rows.append(_row(first_order, str(template.source_file), "", "", "ERROR", f"Roll batch PDF hatası: {exc}", label_settings))
            continue

        page = 1
        for order, _template, _settings, copies in items:
            rows.append(
                _row(
                    order,
                    str(template.source_file),
                    "",
                    "",
                    "OK_BATCH",
                    label_settings.warning,
                    label_settings,
                    roll_batch_pdf=str(batch_pdf),
                    page_number=page,
                    copies=copies,
                )
            )
            page += copies
    return rows


def _write_report(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=_fieldnames())
        writer.writeheader()
        writer.writerows(rows)


def _write_model_reports(run_dir: Path, rows: list[dict[str, str]]) -> list[Path]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        model_no = row.get("model_no", "").strip()
        if not model_no:
            continue
        grouped.setdefault(model_no, []).append(row)

    report_paths: list[Path] = []
    for model_no, model_rows in grouped.items():
        report_path = run_dir / "print" / f"model_{model_no}" / "rendered" / "label_render_report.csv"
        _write_report(report_path, model_rows)
        report_paths.append(report_path)
    return report_paths


def _write_label_settings_report(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    settings_rows: list[dict[str, str]] = []
    if rows:
        first = next((row for row in rows if row.get("media_type")), None)
        if first:
            for key in (
                "media_type",
                "label_width_mm",
                "label_height_mm",
                "roll_gap_mm",
                "printer_dpi",
                "horizontal_offset_mm",
                "vertical_offset_mm",
                "scale_percent",
            ):
                settings_rows.append(
                    {
                        "setting_name": key,
                        "value": first.get(key, ""),
                        "source": first.get("used_settings_source", ""),
                        "status": "OK",
                        "warning": first.get("warning", ""),
                    }
                )
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["setting_name", "value", "source", "status", "warning"])
        writer.writeheader()
        writer.writerows(settings_rows)


def _issue_to_row(issue: ValidationIssue) -> dict[str, str]:
    empty_order = Order(
        row_number=0,
        order_no=issue.order_no,
        buyer_name="",
        product_name="",
        model_no="",
        template_no="",
        process_type="",
        personalization_type="",
        label_variant="",
        label_text="",
        laser_text="",
        quantity=1,
        material_type="",
        material_thickness_mm="",
        extra_chocolate_qty=0,
        extra_madlen_qty=0,
        production_note="",
        needs_review="",
        status="",
        source={},
    )
    return _row(empty_order, "", "", "", "ERROR", issue.message)


def _row(
    order: Order,
    template_file: str,
    output_pdf: str,
    output_png: str,
    status: str,
    warning: str,
    label_settings: ResolvedLabelSettings | None = None,
    roll_batch_pdf: str = "",
    page_number: int | str = "",
    copies: int | str = "",
    text_fit_status: str = "",
    final_font_size: float | str = "",
    render_warning: str = "",
) -> dict[str, str]:
    return {
        "order_no": order.order_no,
        "model_no": order.model_no,
        "template_no": order.template_no,
        "label_variant": order.label_variant,
        "label_text": order.label_text,
        "template_file": template_file,
        "output_pdf": output_pdf,
        "output_png": output_png,
        "media_type": str(getattr(label_settings, "media_type", "")),
        "label_width_mm": str(getattr(label_settings, "label_width_mm", "")),
        "label_height_mm": str(getattr(label_settings, "label_height_mm", "")),
        "roll_gap_mm": str(getattr(label_settings, "roll_gap_mm", "")),
        "printer_dpi": str(getattr(label_settings, "printer_dpi", "")),
        "horizontal_offset_mm": str(getattr(label_settings, "horizontal_offset_mm", "")),
        "vertical_offset_mm": str(getattr(label_settings, "vertical_offset_mm", "")),
        "scale_percent": str(getattr(label_settings, "scale_percent", "")),
        "show_order_number_on_label": str(getattr(label_settings, "show_order_number_on_label", "")),
        "used_settings_source": str(getattr(label_settings, "used_settings_source", "")),
        "roll_batch_pdf": roll_batch_pdf,
        "page_number": str(page_number),
        "copies": str(copies),
        "text_fit_status": text_fit_status,
        "final_font_size": str(final_font_size),
        "render_warning": render_warning,
        "status": status,
        "warning": warning,
    }


def _copies_for_order(order: Order, label_settings: ResolvedLabelSettings) -> int:
    return max(1, int(order.quantity) * int(label_settings.copies_per_order))


def _fieldnames() -> list[str]:
    return [
        "order_no",
        "model_no",
        "template_no",
        "label_variant",
        "label_text",
        "template_file",
        "output_pdf",
        "output_png",
        "media_type",
        "label_width_mm",
        "label_height_mm",
        "roll_gap_mm",
        "printer_dpi",
        "horizontal_offset_mm",
        "vertical_offset_mm",
        "scale_percent",
        "show_order_number_on_label",
        "used_settings_source",
        "roll_batch_pdf",
        "page_number",
        "copies",
        "text_fit_status",
        "final_font_size",
        "render_warning",
        "status",
        "warning",
    ]


def _ensure_qapplication() -> None:
    global _QAPP
    if QApplication.instance() is None:
        _QAPP = QApplication(sys.argv)


def _text_fit_diagnostics(
    template: LabelTemplate,
    order: Order,
    run_date: date,
    label_settings: ResolvedLabelSettings,
) -> tuple[str, float | str, str]:
    statuses: list[str] = []
    sizes: list[float] = []
    warnings: list[str] = []
    for element in template.elements:
        if element.type != "text":
            continue
        if _is_order_number_element(element) and not label_settings.show_order_number_on_label:
            continue
        text = resolve_placeholders(str(element.raw.get("placeholder", "")), order, run_date)
        status, final_size, warning = measure_text_fit(element.raw, text)
        statuses.append(status)
        sizes.append(final_size)
        if warning:
            warnings.append(f"{element.raw.get('id', 'text')}: {warning}")
    if not statuses:
        return "NO_TEXT", "", ""
    if "ERROR_TOO_SMALL" in statuses:
        status = "ERROR_TEXT_TOO_SMALL"
    elif "SHRUNK" in statuses:
        status = "SHRUNK_TO_FIT"
    else:
        status = "OK"
    return status, min(sizes) if sizes else "", " | ".join(warnings)


def _join_warnings(*values: str) -> str:
    return " | ".join(value for value in values if value)


def _is_order_number_element(element: LabelElement) -> bool:
    raw = element.raw
    element_id = str(raw.get("id", "")).lower()
    placeholder = str(raw.get("placeholder", "")).upper()
    return element.type == "text" and ("order" in element_id or "{{ORDER_NO}}" in placeholder)


def _missing_field_columns(template: LabelTemplate, order: Order) -> list[str]:
    missing: list[str] = []
    for field in template.fields:
        excel_column = str(field.get("excel_column", "") or "").strip()
        if excel_column and excel_column not in order.source:
            missing.append(excel_column)
    return sorted(set(missing))
