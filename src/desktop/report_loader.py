from __future__ import annotations

import csv
from datetime import date
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportSet:
    run_dir: Path
    reports_dir: Path
    summary_rows: list[dict[str, str]]
    error_rows: list[dict[str, str]]
    review_rows: list[dict[str, str]]
    warning_rows: list[dict[str, str]]
    material_rows: list[dict[str, str]]
    template_rows: list[dict[str, str]]
    print_data_files: list[Path]
    svg_files: list[Path]
    human_summary: str


def load_latest_reports(project_root: Path) -> ReportSet:
    run_dir = _latest_run_dir(project_root)
    reports_dir = run_dir / "reports"
    print_dir = _first_existing(run_dir / "print", run_dir / "PRINT")
    return ReportSet(
        run_dir=run_dir,
        reports_dir=reports_dir,
        summary_rows=_read_csv(reports_dir / "summary_report.csv"),
        error_rows=_read_csv(reports_dir / "errors_report.csv"),
        review_rows=_read_csv(reports_dir / "needs_review_report.csv"),
        warning_rows=_read_csv(reports_dir / "smart_warnings_report.csv"),
        material_rows=_read_csv(reports_dir / "material_efficiency_report.csv"),
        template_rows=_read_csv(print_dir / "template_matching_report.csv"),
        print_data_files=_print_report_files(print_dir),
        svg_files=sorted((run_dir / "laser").glob("model_*/plate_*.svg")),
        human_summary=_read_text(reports_dir / "production_summary_human_readable.txt"),
    )


def readiness_status(report_set: ReportSet) -> str:
    if not report_set.summary_rows and not report_set.error_rows and not report_set.review_rows:
        return "Henüz kontrol yapılmadı"
    error_rows = _non_empty_rows(report_set.error_rows)
    review_rows = _non_empty_rows(report_set.review_rows)
    if error_rows:
        return "BLOKE"
    if review_rows:
        return "KONTROL GEREKLİ"
    return "HAZIR"


def summary_values(report_set: ReportSet) -> dict[str, str]:
    if not report_set.summary_rows:
        return {}
    return report_set.summary_rows[0]


def _latest_run_dir(project_root: Path) -> Path:
    output_dir = project_root / "output"
    if not output_dir.exists():
        return output_dir
    run_dirs = [path for path in output_dir.iterdir() if path.is_dir() and _is_date_dir(path)]
    if not run_dirs:
        return output_dir
    return sorted(run_dirs, key=lambda item: item.stat().st_mtime)[-1]


def _is_date_dir(path: Path) -> bool:
    try:
        date.fromisoformat(path.name)
    except ValueError:
        return False
    return True


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _print_report_files(print_dir: Path) -> list[Path]:
    if not print_dir.exists():
        return []
    paths: set[Path] = set()
    paths.update(print_dir.glob("model_*/print_data.csv"))
    paths.update(print_dir.glob("model_*/rendered/label_render_report.csv"))
    root_label_report = print_dir / "label_render_report.csv"
    if root_label_report.exists():
        paths.add(root_label_report)
    return sorted(paths)


def _non_empty_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if any((value or "").strip() for value in row.values())]
