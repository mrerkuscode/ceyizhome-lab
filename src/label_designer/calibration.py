from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

from models import LabelDefaults

from .renderer import MM_PER_INCH

_QAPP: QApplication | None = None


def export_roll_label_calibration_pdf(path: Path, defaults: LabelDefaults) -> Path:
    _ensure_qapplication()
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(path))
    writer.setResolution(defaults.printer_dpi)
    writer.setPageSize(QPageSize(QSizeF(defaults.label_width_mm, defaults.label_height_mm), QPageSize.Unit.Millimeter))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    painter = QPainter(writer)
    scale = writer.resolution() / MM_PER_INCH
    painter.scale(scale, scale)
    painter.fillRect(QRectF(0, 0, defaults.label_width_mm, defaults.label_height_mm), QColor("#FFFFFF"))
    painter.setPen(QColor("#111111"))
    painter.drawRect(QRectF(0.4, 0.4, defaults.label_width_mm - 0.8, defaults.label_height_mm - 0.8))
    painter.setPen(QColor("#B42318"))
    painter.drawLine(QPointF(defaults.label_width_mm / 2, 0), QPointF(defaults.label_width_mm / 2, defaults.label_height_mm))
    painter.drawLine(QPointF(0, defaults.label_height_mm / 2), QPointF(defaults.label_width_mm, defaults.label_height_mm / 2))
    painter.setPen(QColor("#157A3B"))
    painter.drawLine(QPointF(4, defaults.label_height_mm - 5), QPointF(14, defaults.label_height_mm - 5))
    painter.drawLine(QPointF(4, defaults.label_height_mm - 6), QPointF(4, defaults.label_height_mm - 4))
    painter.drawLine(QPointF(14, defaults.label_height_mm - 6), QPointF(14, defaults.label_height_mm - 4))
    painter.setFont(_scaled_font(6, scale))
    painter.setPen(QColor("#17202A"))
    painter.drawText(QRectF(2, 2, defaults.label_width_mm - 4, 5), Qt.AlignCenter, f"{defaults.label_width_mm:g} x {defaults.label_height_mm:g} mm")
    painter.setFont(_scaled_font(5, scale))
    painter.drawText(QRectF(2, 8, defaults.label_width_mm - 4, 6), Qt.AlignCenter, "Yazdırırken ölçek %100 olmalıdır.")
    painter.drawText(QRectF(4, defaults.label_height_mm - 11, 18, 5), Qt.AlignLeft, "10 mm")
    painter.end()
    return path


def _ensure_qapplication() -> None:
    global _QAPP
    if QApplication.instance() is None:
        _QAPP = QApplication(sys.argv)


def _scaled_font(point_size: float, device_scale: float) -> QFont:
    font = QFont("Segoe UI")
    font.setPointSizeF(point_size / max(0.1, device_scale))
    return font
