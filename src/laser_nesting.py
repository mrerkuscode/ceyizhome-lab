from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models import BOTH, LASER_CUT, AppSettings, Order, ValidationIssue


CONNECTED_STATUS_OK = "OK_CONNECTED"
CONNECTED_STATUS_DOTS = "WARNING_HAS_SEPARATE_DOTS_OR_ACCENTS"
CONNECTED_STATUS_NOT_CONNECTED = "ERROR_LETTERS_NOT_CONNECTED"
CONNECTED_STATUS_FONT_MISSING = "ERROR_FONT_MISSING"
CONNECTED_STATUS_UNSUPPORTED_TURKISH = "ERROR_UNSUPPORTED_TURKISH_CHARACTER"
TURKISH_CHARACTERS = set("çÇğĞıIİöÖşŞüÜ")


@dataclass(frozen=True)
class LaserItem:
    order: Order
    copy_index: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    font_size: float
    font_name: str
    connected_status: str
    disconnected_parts_count: int
    warning: str = ""


@dataclass(frozen=True)
class LaserPlate:
    plate_index: int
    plate_file: Path
    items: list[LaserItem]


@dataclass(frozen=True)
class LaserNestingResult:
    plates: list[LaserPlate]
    issues: list[ValidationIssue]
    report_rows: list[dict[str, object]]


def nest_laser_orders(
    orders: list[Order],
    model_dir: Path,
    start_plate_index: int,
    settings: AppSettings,
) -> LaserNestingResult:
    plates: list[LaserPlate] = []
    issues: list[ValidationIssue] = []
    report_rows: list[dict[str, object]] = []

    current_items: list[LaserItem] = []
    plate_index = start_plate_index
    x = settings.laser.margin_mm
    y = settings.laser.margin_mm
    row_height = 0.0
    usable_width = settings.laser.plate_width_mm - settings.laser.margin_mm
    usable_height = settings.laser.plate_height_mm - settings.laser.margin_mm

    for order in orders:
        if not order.laser_text.strip():
            warning = "laser_text is empty; laser output skipped for this order."
            issues.append(
                ValidationIssue(
                    row_number=order.row_number,
                    order_no=order.order_no,
                    field="laser_text",
                    message=warning,
                )
            )
            report_rows.append(
                _error_report_row(
                    order=order,
                    status="EMPTY_LASER_TEXT",
                    warning=warning,
                    font_name=_font_name(settings),
                    connected_status=_connected_status_for_order(order),
                    disconnected_parts_count=_disconnected_parts_count(order),
                )
            )
            continue

        connected_error = validate_connected_cut_safety(order, settings)
        if connected_error is not None:
            connected_status, disconnected_parts_count, warning = connected_error
            issues.append(
                ValidationIssue(
                    row_number=order.row_number,
                    order_no=order.order_no,
                    field="laser_text",
                    message=warning,
                )
            )
            report_rows.append(
                _error_report_row(
                    order=order,
                    status=connected_status,
                    warning=warning,
                    font_name=_font_name(settings),
                    connected_status=connected_status,
                    disconnected_parts_count=disconnected_parts_count,
                )
            )
            continue

        for copy_index in range(1, order.quantity + 1):
            measurement = measure_laser_text(order.laser_text, settings)
            if measurement is None:
                warning = f"Laser text too large for plate: {order.laser_text}"
                issues.append(
                    ValidationIssue(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        field="laser_text",
                        message=warning,
                    )
                )
                report_rows.append(
                    _error_report_row(
                        order=order,
                        status="TEXT_TOO_LARGE",
                        warning=warning,
                        font_name=_font_name(settings),
                        connected_status=_connected_status_for_order(order),
                        disconnected_parts_count=_disconnected_parts_count(order),
                    )
                )
                continue

            width_mm, height_mm, font_size, warning = measurement
            warning = _combine_warnings(warning, _font_warning_for_order(order, settings))

            if x + width_mm > usable_width:
                x = settings.laser.margin_mm
                y += row_height + settings.laser.gap_y_mm
                row_height = 0.0

            if y + height_mm > usable_height:
                if current_items:
                    plates.append(_create_plate(model_dir, plate_index, current_items))
                    plate_index += 1
                    current_items = []
                x = settings.laser.margin_mm
                y = settings.laser.margin_mm
                row_height = 0.0

            if y + height_mm > usable_height:
                warning = f"Laser text does not fit vertically on a plate: {order.laser_text}"
                issues.append(
                    ValidationIssue(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        field="laser_text",
                        message=warning,
                    )
                )
                report_rows.append(
                    _error_report_row(
                        order=order,
                        status="TEXT_TOO_LARGE",
                        warning=warning,
                        font_name=_font_name(settings),
                        connected_status=_connected_status_for_order(order),
                        disconnected_parts_count=_disconnected_parts_count(order),
                    )
                )
                continue

            item = LaserItem(
                order=order,
                copy_index=copy_index,
                x_mm=round(x, 2),
                y_mm=round(y, 2),
                width_mm=round(width_mm, 2),
                height_mm=round(height_mm, 2),
                font_size=round(font_size, 2),
                font_name=_font_name(settings),
                connected_status=_connected_status_for_order(order),
                disconnected_parts_count=_disconnected_parts_count(order),
                warning=warning,
            )
            current_items.append(item)
            report_rows.append(_placement_report_row(order, item, "PLACED", warning))

            x += width_mm + settings.laser.gap_x_mm
            row_height = max(row_height, height_mm)

    if current_items:
        plates.append(_create_plate(model_dir, plate_index, current_items))

    report_rows = _attach_plate_files(report_rows, plates)
    return LaserNestingResult(plates=plates, issues=issues, report_rows=report_rows)


def validate_connected_cut_safety(
    order: Order,
    settings: AppSettings,
) -> tuple[str, int, str] | None:
    if order.process_type not in {LASER_CUT, BOTH}:
        return None

    font_path = settings.laser_text.laser_font_path
    if not settings.laser_text.force_connected_letters:
        return (
            CONNECTED_STATUS_NOT_CONNECTED,
            0,
            "LASER_CUT requires force_connected_letters=true; output stopped for safety.",
        )

    if settings.laser_text.force_connected_letters and not font_path.exists():
        return (
            CONNECTED_STATUS_FONT_MISSING,
            0,
            f"Connected script font missing for LASER_CUT: {font_path}",
        )

    if _has_unsupported_turkish_character(order.laser_text, font_path):
        return (
            CONNECTED_STATUS_UNSUPPORTED_TURKISH,
            0,
            f"Font does not support required Turkish characters for LASER_CUT: {font_path}",
        )

    if not settings.laser_text.convert_text_to_paths:
        return (
            CONNECTED_STATUS_NOT_CONNECTED,
            0,
            "LASER_CUT requires convert_text_to_paths=true; editable text cut output stopped for safety.",
        )

    if settings.laser_text.convert_text_to_paths:
        return (
            CONNECTED_STATUS_NOT_CONNECTED,
            0,
            "Cannot guarantee connected cursive vector paths/welded cut shape in MVP; LASER_CUT output stopped for safety.",
        )

    return None


def measure_laser_text(
    laser_text: str,
    settings: AppSettings,
) -> tuple[float, float, float, str] | None:
    max_width = settings.laser.plate_width_mm - (2 * settings.laser.margin_mm)
    max_height = settings.laser.plate_height_mm - (2 * settings.laser.margin_mm)
    font_size = min(
        settings.laser_text.default_font_size_mm,
        settings.laser_text.max_font_size_mm,
    )
    warning = ""

    while font_size >= settings.laser_text.min_font_size_mm:
        width = _estimate_text_width_mm(laser_text, font_size)
        height = _estimate_text_height_mm(font_size)
        if width <= max_width and height <= max_height:
            if font_size < settings.laser_text.default_font_size_mm:
                warning = "Font size reduced to fit plate"
            return width, height, font_size, warning
        font_size -= 1

    return None


def _estimate_text_width_mm(text: str, font_size: float) -> float:
    wide_chars = sum(1 for char in text if char.upper() in {"M", "W", "Ş", "Ğ", "Ü", "Ö"})
    normal_chars = max(len(text) - wide_chars, 0)
    return (normal_chars * font_size * 0.58) + (wide_chars * font_size * 0.78)


def _estimate_text_height_mm(font_size: float) -> float:
    return font_size * 1.2


def _create_plate(model_dir: Path, plate_index: int, items: list[LaserItem]) -> LaserPlate:
    plate_file = model_dir / f"plate_{plate_index:03d}.svg"
    return LaserPlate(plate_index=plate_index, plate_file=plate_file, items=list(items))


def _placement_report_row(
    order: Order,
    item: LaserItem,
    status: str,
    warning: str,
) -> dict[str, object]:
    return {
        "plate_file": "",
        "order_no": order.order_no,
        "buyer_name": order.buyer_name,
        "product_name": order.product_name,
        "laser_text": order.laser_text,
        "model_no": order.model_no,
        "process_type": order.process_type,
        "material_type": order.material_type,
        "material_thickness_mm": order.material_thickness_mm,
        "x_mm": item.x_mm,
        "y_mm": item.y_mm,
        "width_mm": item.width_mm,
        "height_mm": item.height_mm,
        "font_name": item.font_name,
        "font_size": item.font_size,
        "connected_status": item.connected_status,
        "disconnected_parts_count": item.disconnected_parts_count,
        "status": status,
        "warning": warning,
    }


def _error_report_row(
    order: Order,
    status: str,
    warning: str,
    font_name: str,
    connected_status: str,
    disconnected_parts_count: int,
) -> dict[str, object]:
    return {
        "plate_file": "",
        "order_no": order.order_no,
        "buyer_name": order.buyer_name,
        "product_name": order.product_name,
        "laser_text": order.laser_text,
        "model_no": order.model_no,
        "process_type": order.process_type,
        "material_type": order.material_type,
        "material_thickness_mm": order.material_thickness_mm,
        "x_mm": "",
        "y_mm": "",
        "width_mm": "",
        "height_mm": "",
        "font_name": font_name,
        "font_size": "",
        "connected_status": connected_status,
        "disconnected_parts_count": disconnected_parts_count,
        "status": status,
        "warning": warning,
    }


def _attach_plate_files(
    report_rows: list[dict[str, object]],
    plates: list[LaserPlate],
) -> list[dict[str, object]]:
    placed_rows = [row for row in report_rows if row["status"] == "PLACED"]
    placed_index = 0

    for plate in plates:
        for _item in plate.items:
            placed_rows[placed_index]["plate_file"] = str(plate.plate_file)
            placed_index += 1

    return report_rows


def _font_name(settings: AppSettings) -> str:
    return settings.laser_text.laser_font_path.stem


def _connected_status_for_order(order: Order) -> str:
    if order.process_type not in {LASER_CUT, BOTH}:
        return CONNECTED_STATUS_OK
    disconnected_count = _disconnected_parts_count(order)
    if disconnected_count:
        return CONNECTED_STATUS_DOTS
    return CONNECTED_STATUS_OK


def _disconnected_parts_count(order: Order) -> int:
    if order.process_type not in {LASER_CUT, BOTH}:
        return 0
    return sum(1 for char in order.laser_text if char in {"i", "j", "İ", "ö", "Ö", "ü", "Ü", "ğ", "Ğ"})


def _has_unsupported_turkish_character(text: str, font_path: Path) -> bool:
    if not any(char in TURKISH_CHARACTERS for char in text):
        return False
    if not font_path.exists():
        return False
    return not _font_supports_characters(font_path, TURKISH_CHARACTERS)


def _font_supports_characters(font_path: Path, characters: set[str]) -> bool:
    try:
        from fontTools.ttLib import TTFont
    except ModuleNotFoundError:
        return False

    try:
        font = TTFont(font_path)
        codepoints = set()
        for table in font["cmap"].tables:
            codepoints.update(table.cmap.keys())
        return all(ord(char) in codepoints for char in characters)
    except Exception:
        return False


def _font_warning_for_order(order: Order, settings: AppSettings) -> str:
    if order.process_type in {LASER_CUT, BOTH}:
        return ""
    if not settings.laser_text.laser_font_path.exists():
        return f"Font file missing; RDWorks may substitute font: {settings.laser_text.laser_font_path}"
    return ""


def _combine_warnings(*warnings: str) -> str:
    return " | ".join(warning for warning in warnings if warning)
