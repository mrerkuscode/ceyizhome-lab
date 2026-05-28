from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from config_loader import load_settings

from .calibration import export_roll_label_calibration_pdf


@dataclass(frozen=True)
class CalibrationResult:
    pdf_path: Path


def create_calibration_pdf(project_root: Path, run_date: date | None = None) -> CalibrationResult:
    run_date = run_date or date.today()
    settings = load_settings(project_root / "config" / "settings.yaml")
    defaults = settings.label_defaults
    if defaults is None:
        raise ValueError("Varsayılan rulo etiket ölçüsü tanımlı değil.")
    output_dir = project_root / "output" / run_date.strftime(settings.app.output_date_format) / "print" / "calibration"
    output = output_dir / f"roll_label_calibration_{defaults.label_width_mm:g}x{defaults.label_height_mm:g}.pdf"
    export_roll_label_calibration_pdf(output, defaults)
    return CalibrationResult(pdf_path=output)
