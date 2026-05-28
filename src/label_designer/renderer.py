from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QImage, QPainter, QPen, QTextOption

from models import Order

from .placeholder_resolver import resolve_placeholders
from .template_schema import LabelElement, LabelTemplate, ResolvedLabelSettings


MM_PER_INCH = 25.4
POINTS_PER_INCH = 72
MIN_RENDER_FONT_PT = 3.5


def mm_to_points(value_mm: float) -> float:
    return value_mm * POINTS_PER_INCH / MM_PER_INCH


def points_to_mm(value_points: float) -> float:
    return value_points * MM_PER_INCH / POINTS_PER_INCH


def render_template_to_painter(
    painter: QPainter,
    template: LabelTemplate,
    order: Order,
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None = None,
) -> list[str]:
    warnings: list[str] = []
    _apply_label_transform(painter, label_settings)
    _draw_background(painter, template, base_dir, label_settings)
    for element in template.elements:
        if element.raw.get("visible") is False:
            continue
        if _is_order_number_element(element) and label_settings is not None and not label_settings.show_order_number_on_label:
            continue
        warning = _draw_element(painter, element, order, run_date, base_dir)
        if warning:
            warnings.append(warning)
    return warnings


def create_preview_image(
    template: LabelTemplate,
    order: Order,
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None = None,
    dpi: int = 300,
) -> QImage:
    width_mm = label_settings.label_width_mm if label_settings else template.canvas_width_mm
    height_mm = label_settings.label_height_mm if label_settings else template.canvas_height_mm
    dpi = label_settings.printer_dpi if label_settings else dpi
    px_per_mm = dpi / MM_PER_INCH
    width_px = max(1, round(width_mm * px_per_mm))
    height_px = max(1, round(height_mm * px_per_mm))
    image = QImage(width_px, height_px, QImage.Format_ARGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    painter.scale(px_per_mm, px_per_mm)
    render_template_to_painter(painter, template, order, run_date, base_dir, label_settings)
    painter.end()
    return image


def _draw_background(
    painter: QPainter,
    template: LabelTemplate,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None,
) -> None:
    width_mm = label_settings.label_width_mm if label_settings else template.canvas_width_mm
    height_mm = label_settings.label_height_mm if label_settings else template.canvas_height_mm
    if label_settings is not None and not label_settings.background_enabled:
        painter.fillRect(QRectF(0, 0, width_mm, height_mm), QColor("#FFFFFF"))
        return
    if not template.background_image:
        painter.fillRect(QRectF(0, 0, width_mm, height_mm), QColor("#FFFFFF"))
        return
    image_path = _resolve_asset_path(base_dir, template.background_image)
    image = QImage(str(image_path))
    if image.isNull():
        painter.fillRect(QRectF(0, 0, width_mm, height_mm), QColor("#FFFFFF"))
        return
    painter.drawImage(QRectF(0, 0, width_mm, height_mm), image)


def _apply_label_transform(painter: QPainter, label_settings: ResolvedLabelSettings | None) -> None:
    if label_settings is None:
        return
    painter.translate(label_settings.horizontal_offset_mm, label_settings.vertical_offset_mm)
    if label_settings.scale_percent != 100:
        factor = label_settings.scale_percent / 100
        painter.scale(factor, factor)


def _draw_element(
    painter: QPainter,
    element: LabelElement,
    order: Order,
    run_date: date,
    base_dir: Path,
) -> str:
    raw = element.raw
    if element.type == "text":
        return _draw_text(painter, raw, order, run_date, base_dir)
    elif element.type == "rectangle":
        _draw_rectangle(painter, raw)
    elif element.type == "line":
        _draw_line(painter, raw)
    elif element.type == "image":
        _draw_image(painter, raw, base_dir)
    return ""


def _draw_text(painter: QPainter, raw: dict, order: Order, run_date: date, base_dir: Path) -> str:
    text = resolve_placeholders(str(raw.get("placeholder", "")), order, run_date)
    rect = _rect(raw)
    painter.save()
    _apply_rotation(painter, raw, rect)
    requested_size = float(raw.get("font_size", 18))
    font = _make_font(raw, base_dir, requested_size, _device_scale(painter))
    final_size, fit_status = _fit_font_to_rect(painter, font, text, rect, requested_size)
    font = _make_font(raw, base_dir, final_size, _device_scale(painter))
    font.setBold(bool(raw.get("bold", False)))
    font.setItalic(bool(raw.get("italic", False)))
    painter.setFont(font)
    painter.setPen(QColor(str(raw.get("color", "#111111"))))

    option = QTextOption()
    option.setAlignment(_alignment(str(raw.get("align", "center")), str(raw.get("vertical_align", "center"))))
    option.setWrapMode(QTextOption.WordWrap)
    painter.drawText(rect, text, option)
    painter.restore()
    if fit_status != "OK":
        return f"{raw.get('id', 'text')} metni kutuya sığması için {requested_size:g} pt -> {final_size:g} pt küçültüldü."
    return ""


def measure_text_fit(raw: dict, text: str) -> tuple[str, float, str]:
    font = _make_font(raw, Path("."), float(raw.get("font_size", 18)))
    rect = _rect(raw)
    final_size, fit_status = _fit_font_to_rect(None, font, text, rect, float(raw.get("font_size", 18)))
    warning = ""
    if fit_status == "SHRUNK":
        warning = f"Metin kutuya sığması için {float(raw.get('font_size', 18)):g} pt -> {final_size:g} pt küçültüldü."
    elif fit_status == "ERROR_TOO_SMALL":
        warning = "Metin kutuya güvenli şekilde sığdırılamadı."
    return fit_status, final_size, warning


def _make_font(raw: dict, base_dir: Path, point_size: float, device_scale: float = 1.0) -> QFont:
    font = QFont(str(raw.get("font_family", "Segoe UI")))
    font_path = str(raw.get("font_path", "") or "")
    if font_path:
        loaded_id = QFontDatabase.addApplicationFont(str(_resolve_asset_path(base_dir, font_path)))
        families = QFontDatabase.applicationFontFamilies(loaded_id)
        if families:
            font = QFont(families[0])
    font.setPointSizeF(max(0.1, point_size))
    font.setBold(bool(raw.get("bold", False)))
    font.setItalic(bool(raw.get("italic", False)))
    return font


def _fit_font_to_rect(
    painter: QPainter | None,
    font: QFont,
    text: str,
    rect: QRectF,
    requested_size: float,
) -> tuple[float, str]:
    available_w_pt = mm_to_points(max(0.1, rect.width()))
    available_h_pt = mm_to_points(max(0.1, rect.height()))
    final_size = requested_size
    status = "OK"
    while final_size >= MIN_RENDER_FONT_PT:
        test_font = QFont(font)
        test_font.setPointSizeF(max(0.1, final_size))
        metrics = QFontMetricsF(test_font)
        text_rect = metrics.boundingRect(QRectF(0, 0, available_w_pt, 1000), Qt.TextWordWrap, text)
        if text_rect.width() <= available_w_pt * 1.02 and text_rect.height() <= available_h_pt * 1.02:
            return final_size, status
        final_size -= 0.5
        status = "SHRUNK"
    return MIN_RENDER_FONT_PT, "ERROR_TOO_SMALL"


def _device_scale(painter: QPainter | None) -> float:
    if painter is None:
        return 1.0
    scale = abs(painter.transform().m11())
    return scale if scale > 0 else 1.0


def _draw_rectangle(painter: QPainter, raw: dict) -> None:
    painter.save()
    pen = QPen(QColor(str(raw.get("stroke_color", "#111111"))), float(raw.get("stroke_width", 0.2)))
    painter.setPen(pen)
    fill = QColor(str(raw.get("fill_color", "transparent")))
    painter.setBrush(fill)
    painter.drawRect(_rect(raw))
    painter.restore()


def _draw_line(painter: QPainter, raw: dict) -> None:
    painter.save()
    pen = QPen(QColor(str(raw.get("color", "#111111"))), float(raw.get("stroke_width", 0.2)))
    painter.setPen(pen)
    painter.drawLine(
        QPointF(float(raw.get("x1_mm", 0)), float(raw.get("y1_mm", 0))),
        QPointF(float(raw.get("x2_mm", 0)), float(raw.get("y2_mm", 0))),
    )
    painter.restore()


def _draw_image(painter: QPainter, raw: dict, base_dir: Path) -> None:
    image_path = _resolve_asset_path(base_dir, str(raw.get("path", "")))
    image = QImage(str(image_path))
    if image.isNull():
        return
    painter.drawImage(_rect(raw), image)


def _rect(raw: dict) -> QRectF:
    return QRectF(
        float(raw.get("x_mm", 0)),
        float(raw.get("y_mm", 0)),
        float(raw.get("width_mm", 0)),
        float(raw.get("height_mm", 0)),
    )


def _alignment(horizontal: str, vertical: str) -> Qt.AlignmentFlag:
    h_map = {
        "left": Qt.AlignLeft,
        "center": Qt.AlignHCenter,
        "right": Qt.AlignRight,
    }
    v_map = {
        "top": Qt.AlignTop,
        "center": Qt.AlignVCenter,
        "bottom": Qt.AlignBottom,
    }
    return h_map.get(horizontal.lower(), Qt.AlignHCenter) | v_map.get(vertical.lower(), Qt.AlignVCenter)


def _apply_rotation(painter: QPainter, raw: dict, rect: QRectF) -> None:
    rotation = float(raw.get("rotation", 0) or 0)
    if not rotation:
        return
    center = rect.center()
    painter.translate(center)
    painter.rotate(rotation)
    painter.translate(-center)


def _resolve_asset_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    template_relative = base_dir / path
    if template_relative.exists():
        return template_relative
    project_relative = base_dir.parent.parent / path
    if path.parts and path.parts[0] == "assets" and project_relative.exists():
        return project_relative
    return template_relative


def _is_order_number_element(element: LabelElement) -> bool:
    raw = element.raw
    element_id = str(raw.get("id", "")).lower()
    placeholder = str(raw.get("placeholder", "")).upper()
    return element.type == "text" and ("order" in element_id or "{{ORDER_NO}}" in placeholder)
