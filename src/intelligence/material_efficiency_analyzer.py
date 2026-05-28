from __future__ import annotations

import csv
from pathlib import Path


def analyze_material_efficiency(run_dir: Path, plate_width_mm: float, plate_height_mm: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    laser_root = run_dir / "laser"
    if not laser_root.exists():
        return rows

    plate_area = plate_width_mm * plate_height_mm
    for report_path in laser_root.glob("model_*/plate_*_layout_report.csv"):
        placements = _read_layout_report(report_path)
        used_area = sum(float(row["width_mm"]) * float(row["height_mm"]) for row in placements if row.get("status") == "PLACED")
        usage_percent = round((used_area / plate_area) * 100, 2) if plate_area else 0
        rows.append(
            {
                "plate_file": str(report_path.with_name(report_path.name.replace("_layout_report.csv", ".svg"))),
                "model_no": report_path.parent.name.replace("model_", ""),
                "plates_used": 1,
                "plate_usage_percent": usage_percent,
                "estimated_wasted_area_mm2": round(max(plate_area - used_area, 0), 2),
                "long_names_count": sum(1 for row in placements if len(row.get("laser_text", "")) > 24),
                "optimization_note": _optimization_note(usage_percent, placements),
            }
        )
    return rows


def _read_layout_report(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _optimization_note(usage_percent: float, placements: list[dict[str, str]]) -> str:
    if not placements:
        return "No placed laser objects on this plate."
    if usage_percent < 35:
        return "Low material usage; future optimizer could combine compatible jobs."
    if any(len(row.get("laser_text", "")) > 24 for row in placements):
        return "Long names may reduce nesting efficiency."
    return "Row-based MVP layout looks acceptable."
