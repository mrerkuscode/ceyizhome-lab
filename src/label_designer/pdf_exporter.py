from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter

from models import Order

from .renderer import MM_PER_INCH, create_preview_image
from .template_schema import LabelTemplate, ResolvedLabelSettings


def export_label_pdf(
    path: Path,
    template: LabelTemplate,
    order: Order,
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width_mm = label_settings.label_width_mm if label_settings else template.canvas_width_mm
    height_mm = label_settings.label_height_mm if label_settings else template.canvas_height_mm
    dpi = label_settings.printer_dpi if label_settings else 300
    writer = QPdfWriter(str(path))
    writer.setResolution(dpi)
    writer.setPageSize(QPageSize(QSizeF(width_mm, height_mm), QPageSize.Unit.Millimeter))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    painter.scale(writer.resolution() / MM_PER_INCH, writer.resolution() / MM_PER_INCH)
    _draw_preview_image_page(painter, template, order, run_date, base_dir, label_settings, width_mm, height_mm)
    painter.end()
    return path


def export_roll_batch_pdf(
    path: Path,
    template: LabelTemplate,
    order_copies: list[tuple[Order, int]],
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(path))
    writer.setResolution(label_settings.printer_dpi)
    writer.setPageSize(
        QPageSize(
            QSizeF(label_settings.label_width_mm, label_settings.label_height_mm),
            QPageSize.Unit.Millimeter,
        )
    )
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    painter.scale(writer.resolution() / MM_PER_INCH, writer.resolution() / MM_PER_INCH)

    is_first_page = True
    for order, copies in order_copies:
        for _copy_index in range(max(1, copies)):
            if not is_first_page:
                writer.newPage()
            _draw_preview_image_page(
                painter,
                template,
                order,
                run_date,
                base_dir,
                label_settings,
                label_settings.label_width_mm,
                label_settings.label_height_mm,
            )
            is_first_page = False

    painter.end()
    return path


def _draw_preview_image_page(
    painter: QPainter,
    template: LabelTemplate,
    order: Order,
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None,
    width_mm: float,
    height_mm: float,
) -> None:
    image = create_preview_image(template, order, run_date, base_dir, label_settings)
    painter.drawImage(QRectF(0, 0, width_mm, height_mm), image)
