from __future__ import annotations

from datetime import date
from pathlib import Path

from models import ProductionPaths


def create_run_folders(output_dir: Path, run_date: date, date_format: str = "%Y-%m-%d") -> ProductionPaths:
    run_dir = output_dir / run_date.strftime(date_format)
    paths = ProductionPaths(
        run_dir=run_dir,
        print_dir=run_dir / "print",
        laser_dir=run_dir / "laser",
        reports_dir=run_dir / "reports",
        logs_dir=run_dir / "logs",
    )

    for path in (
        paths.print_dir,
        paths.laser_dir,
        paths.reports_dir,
        paths.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    return paths


def create_report_folders(output_dir: Path, run_date: date, date_format: str = "%Y-%m-%d") -> tuple[Path, Path, Path]:
    run_dir = output_dir / run_date.strftime(date_format)
    reports_dir = run_dir / "reports"
    logs_dir = run_dir / "logs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, reports_dir, logs_dir

