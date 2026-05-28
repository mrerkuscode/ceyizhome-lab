from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from intelligence.production_analyzer import IntelligenceFinding
from models import BOTH, LASER_CUT, LASER_ENGRAVE, NONE, PRINT, Order, ValidationIssue


def write_intelligence_reports(
    reports_dir: Path,
    warnings: list[IntelligenceFinding],
    review_reasons: list[dict[str, str]],
    material_efficiency_rows: list[dict[str, object]],
    valid_orders: list[Order],
    issues: list[ValidationIssue],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_findings(reports_dir / "smart_warnings_report.csv", warnings)
    _write_review_reasons(reports_dir / "needs_review_report.csv", review_reasons)
    _write_material_efficiency(reports_dir / "material_efficiency_report.csv", material_efficiency_rows)
    _write_human_summary(
        reports_dir / "production_summary_human_readable.txt",
        valid_orders,
        issues,
        warnings,
        review_reasons,
        material_efficiency_rows,
    )


def _write_findings(path: Path, findings: list[IntelligenceFinding]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["row_number", "order_no", "severity", "category", "field", "message", "suggestion"],
        )
        writer.writeheader()
        for finding in findings:
            writer.writerow(finding.__dict__)


def _write_review_reasons(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["row_number", "order_no", "reason", "why_it_matters", "what_to_fix"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_material_efficiency(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "plate_file",
                "model_no",
                "plates_used",
                "plate_usage_percent",
                "estimated_wasted_area_mm2",
                "long_names_count",
                "optimization_note",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_human_summary(
    path: Path,
    valid_orders: list[Order],
    issues: list[ValidationIssue],
    warnings: list[IntelligenceFinding],
    review_reasons: list[dict[str, str]],
    material_efficiency_rows: list[dict[str, object]],
) -> None:
    counts = Counter(order.process_type for order in valid_orders)
    lines = [
        "CYZELLA PRODUCTION SUMMARY",
        "",
        "Safety:",
        "- CorelDRAW was not opened.",
        "- Nothing was sent to the printer.",
        "- RDWorks was not opened.",
        "- Laser was not started.",
        "- Intelligence reports are advisory only; deterministic rules remain the source of truth.",
        "",
        f"Valid orders: {len(valid_orders)}",
        f"Deterministic issues: {len(issues)}",
        f"Warnings/recommendations: {len(warnings)}",
        f"Needs review rows: {len(review_reasons)}",
        "",
        "Process counts:",
        f"- PRINT: {counts.get(PRINT, 0)}",
        f"- LASER_ENGRAVE: {counts.get(LASER_ENGRAVE, 0)}",
        f"- LASER_CUT: {counts.get(LASER_CUT, 0)}",
        f"- BOTH: {counts.get(BOTH, 0)}",
        f"- NONE: {counts.get(NONE, 0)}",
        "",
        "Material efficiency:",
    ]
    if material_efficiency_rows:
        for row in material_efficiency_rows:
            lines.append(
                f"- {row['plate_file']}: {row['plate_usage_percent']}% used, "
                f"wasted {row['estimated_wasted_area_mm2']} mm2"
            )
    else:
        lines.append("- No laser plates generated.")

    path.write_text("\n".join(lines), encoding="utf-8")
