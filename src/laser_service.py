from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from laser_nesting import LaserNestingResult, nest_laser_orders
from models import AppSettings, Order, ValidationIssue
from svg_generator import write_laser_plate_svg
from text_utils import safe_filename


LASER_REPORT_COLUMNS = [
    "plate_file",
    "order_no",
    "buyer_name",
    "product_name",
    "laser_text",
    "model_no",
    "process_type",
    "material_type",
    "material_thickness_mm",
    "x_mm",
    "y_mm",
    "width_mm",
    "height_mm",
    "font_name",
    "font_size",
    "connected_status",
    "disconnected_parts_count",
    "status",
    "warning",
]


def generate_laser_jobs(
    orders: list[Order],
    run_dir: Path,
    settings: AppSettings,
) -> tuple[list[Path], list[ValidationIssue]]:
    written_files: list[Path] = []
    issues: list[ValidationIssue] = []
    model_report_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    next_plate_index_by_model: dict[str, int] = defaultdict(lambda: 1)

    for group_orders in _group_laser_orders(orders).values():
        model_no = group_orders[0].model_no
        model_dir = run_dir / "laser" / f"model_{safe_filename(model_no)}"
        model_dir.mkdir(parents=True, exist_ok=True)

        start_plate_index = next_plate_index_by_model[model_no]
        result = nest_laser_orders(group_orders, model_dir, start_plate_index, settings)
        next_plate_index_by_model[model_no] = start_plate_index + len(result.plates)

        _write_plates(result, settings)
        written_files.extend(plate.plate_file for plate in result.plates)
        if settings.reports.generate_layout_report:
            written_files.extend(_write_plate_reports(result))
        written_files.extend(_write_plate_job_infos(result, settings))
        model_report_rows[model_no].extend(result.report_rows)
        issues.extend(result.issues)

    if settings.reports.generate_layout_report:
        for model_no, rows in model_report_rows.items():
            model_dir = run_dir / "laser" / f"model_{safe_filename(model_no)}"
            report_path = model_dir / "model_level_layout_report.csv"
            _write_report(report_path, rows)
            written_files.append(report_path)

    return written_files, issues


def _group_laser_orders(orders: list[Order]) -> dict[tuple[str, str, str, str], list[Order]]:
    groups: dict[tuple[str, str, str, str], list[Order]] = defaultdict(list)
    for order in orders:
        key = (
            order.model_no,
            order.material_type,
            order.material_thickness_mm,
            order.process_type,
        )
        groups[key].append(order)
    return groups


def _write_plates(result: LaserNestingResult, settings: AppSettings) -> None:
    for plate in result.plates:
        write_laser_plate_svg(plate.plate_file, plate, settings)


def _write_plate_reports(result: LaserNestingResult) -> list[Path]:
    written_files: list[Path] = []
    rows_by_plate: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in result.report_rows:
        plate_file = str(row.get("plate_file", ""))
        if not plate_file:
            continue
        rows_by_plate[plate_file].append(row)

    for plate_file, rows in rows_by_plate.items():
        plate_path = Path(plate_file)
        report_path = plate_path.with_name(f"{plate_path.stem}_layout_report.csv")
        _write_report(report_path, rows)
        written_files.append(report_path)

    return written_files


def _write_plate_job_infos(result: LaserNestingResult, settings: AppSettings) -> list[Path]:
    written_files: list[Path] = []
    for plate in result.plates:
        job_info_path = plate.plate_file.with_name(f"{plate.plate_file.stem}_job_info.txt")
        lines = [
            "LASER PLATE JOB INFO",
            "",
            "Safety:",
            "- RDWorks was not opened.",
            "- Laser was not started.",
            "- Inspect the SVG manually before production.",
            "",
            f"Plate file: {plate.plate_file}",
            f"Plate size mm: {settings.laser.plate_width_mm} x {settings.laser.plate_height_mm}",
            f"Object count: {len(plate.items)}",
            "",
            "Orders:",
        ]
        for item in plate.items:
            lines.append(
                (
                    f"- {item.order.order_no} | {item.order.buyer_name} | "
                    f"{item.order.process_type} | {item.order.laser_text} | "
                    f"x={item.x_mm} y={item.y_mm} w={item.width_mm} h={item.height_mm} | "
                    f"{item.connected_status}"
                )
            )
        job_info_path.write_text("\n".join(lines), encoding="utf-8")
        written_files.append(job_info_path)
    return written_files


def _write_report(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=LASER_REPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in LASER_REPORT_COLUMNS})
