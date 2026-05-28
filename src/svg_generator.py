from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from laser_nesting import LaserPlate
from models import BOTH, LASER_CUT, LASER_ENGRAVE, AppSettings


def write_laser_plate_svg(path: Path, plate: LaserPlate, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = "\n".join(
        [
            '<xml version="1.0" encoding="UTF-8">',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{settings.laser.plate_width_mm}mm" '
                f'height="{settings.laser.plate_height_mm}mm" '
                f'viewBox="0 0 {settings.laser.plate_width_mm} {settings.laser.plate_height_mm}">'
            ),
            f"<title>Laser plate {plate.plate_index:03d}</title>",
            _plate_boundary_group(settings),
            _engrave_text_group(plate),
            _cut_lines_group(plate),
            _order_guide_group(plate, settings),
            "</svg>",
        ]
    )
    path.write_text(svg, encoding="utf-8")


def _plate_boundary_group(settings: AppSettings) -> str:
    return "\n".join(
        [
            '<g id="PLATE_BOUNDARY_GUIDE_DO_NOT_CUT" data-layer-purpose="guide-non-cutting">',
            (
                f'<rect x="0" y="0" width="{settings.laser.plate_width_mm}" '
                f'height="{settings.laser.plate_height_mm}" fill="none" '
                'stroke="#0080ff" stroke-width="0.2" stroke-dasharray="4 2" />'
            ),
            "</g>",
        ]
    )


def _engrave_text_group(plate: LaserPlate) -> str:
    elements = ['<g id="ENGRAVE_TEXT" data-layer-purpose="engrave">']
    for item in plate.items:
        if item.order.process_type not in {LASER_ENGRAVE, BOTH}:
            continue
        elements.append(
            (
                f'<text x="{item.x_mm}" y="{item.y_mm + item.font_size}" '
                f'font-size="{item.font_size}" font-family="{escape(item.font_name)}" '
                f'fill="#000000">{escape(item.order.laser_text)}</text>'
            )
        )
    elements.append("</g>")
    return "\n".join(elements)


def _cut_lines_group(plate: LaserPlate) -> str:
    elements = ['<g id="CUT_LINES" data-layer-purpose="cut">']
    for item in plate.items:
        if item.order.process_type not in {LASER_CUT, BOTH}:
            continue
        # LASER_CUT requires connected vector paths. Editable SVG text is deliberately
        # not emitted here because it can produce separated letters in production.
        continue
    elements.append("</g>")
    return "\n".join(elements)


def _order_guide_group(plate: LaserPlate, settings: AppSettings) -> str:
    elements = ['<g id="ORDER_GUIDE_DO_NOT_CUT" data-layer-purpose="guide-non-cutting">']
    if settings.laser.include_order_number_guide:
        for item in plate.items:
            elements.append(
                (
                    f'<text x="{item.x_mm}" y="{max(item.y_mm - 1, 1)}" '
                    'font-size="3" font-family="Arial" fill="#0080ff">'
                    f'{escape(item.order.order_no)}</text>'
                )
            )
    elements.append("</g>")
    return "\n".join(elements)
