from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from models import BOTH, LASER_CUT, LASER_ENGRAVE, NONE, PRINT, Order, ValidationIssue


def write_errors_report(path: Path, issues: list[ValidationIssue]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["row_number", "order_no", "field", "message"],
        )
        writer.writeheader()
        for issue in issues:
            writer.writerow(
                {
                    "row_number": issue.row_number,
                    "order_no": issue.order_no,
                    "field": issue.field,
                    "message": issue.message,
                }
            )


def write_summary_report(
    path: Path,
    total_rows: int,
    valid_orders: list[Order],
    issues: list[ValidationIssue],
) -> None:
    invalid_rows = {
        issue.row_number
        for issue in issues
        if isinstance(issue.row_number, int)
    }
    counts = Counter(order.process_type for order in valid_orders)

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "total_rows",
                "valid_rows",
                "invalid_rows",
                "print_jobs_count",
                "laser_engrave_jobs_count",
                "laser_cut_jobs_count",
                "both_jobs_count",
                "none_jobs_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "total_rows": total_rows,
                "valid_rows": len(valid_orders),
                "invalid_rows": len(invalid_rows),
                "print_jobs_count": counts.get(PRINT, 0),
                "laser_engrave_jobs_count": counts.get(LASER_ENGRAVE, 0),
                "laser_cut_jobs_count": counts.get(LASER_CUT, 0),
                "both_jobs_count": counts.get(BOTH, 0),
                "none_jobs_count": counts.get(NONE, 0),
            }
        )
