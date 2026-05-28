from __future__ import annotations

import csv
from pathlib import Path

from desktop.report_loader import ReportSet, load_latest_reports

from .text_normalizer import friendly_error


def load_reports(project_root: Path) -> ReportSet:
    return load_latest_reports(project_root)


def readiness(report_set: ReportSet | None) -> str:
    if report_set is None:
        return "NO_CHECK"
    if _non_empty(report_set.error_rows):
        return "BLOKE"
    if _non_empty(report_set.review_rows):
        return "KONTROL_GEREKLI"
    if report_set.summary_rows:
        return "HAZIR"
    return "NO_CHECK"


def summary(report_set: ReportSet | None) -> dict[str, int]:
    row = report_set.summary_rows[0] if report_set and report_set.summary_rows else {}
    errors = _non_empty(report_set.error_rows if report_set else [])
    review = _non_empty(report_set.review_rows if report_set else [])
    laser_jobs = _to_int(row.get("laser_engrave_jobs_count") or row.get("laser_engrave_jobs")) + _to_int(
        row.get("laser_cut_jobs_count") or row.get("laser_cut_jobs")
    ) + _to_int(row.get("both_jobs_count") or row.get("both_jobs"))
    return {
        "valid": _to_int(row.get("valid_rows")),
        "errors": len(errors) or _to_int(row.get("invalid_rows")),
        "review": len(review),
        "label": _to_int(row.get("print_jobs_count") or row.get("print_jobs")),
        "print": _to_int(row.get("print_jobs_count") or row.get("print_jobs")),
        "laser": laser_jobs,
    }


def first_errors(report_set: ReportSet | None, limit: int = 5) -> list[dict[str, str]]:
    rows = _non_empty(report_set.error_rows if report_set else [])[:limit]
    return [friendly_error(row) for row in rows]


def report_payload(report_set: ReportSet | None) -> dict[str, object]:
    if report_set is None:
        return {}
    return {
        "humanSummary": report_set.human_summary,
        "errors": [friendly_error(row) for row in _non_empty(report_set.error_rows)],
        "reviewRows": _non_empty(report_set.review_rows),
        "warnings": _non_empty(report_set.warning_rows),
        "labelRows": _label_rows(report_set),
        "laserRows": _non_empty(report_set.material_rows),
        "svgFiles": [str(path) for path in report_set.svg_files],
    }


def _label_rows(report_set: ReportSet) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in report_set.print_data_files:
        csv_rows = _read_csv(path)
        if not csv_rows:
            rows.append({"file": str(path), "name": path.name, "status": "Rapor boş veya henüz üretilmedi"})
            continue
        for row in csv_rows[:50]:
            combined = {"file": str(path), "name": path.name}
            combined.update({str(key): str(value) for key, value in row.items()})
            rows.append(combined)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _non_empty(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def _to_int(value: object) -> int:
    try:
        return int(float(str(value or 0)))
    except ValueError:
        return 0
