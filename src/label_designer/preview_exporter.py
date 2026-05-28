from __future__ import annotations

from datetime import date
from pathlib import Path

from models import Order

from .renderer import create_preview_image
from .template_schema import LabelTemplate, ResolvedLabelSettings


def export_label_png(
    path: Path,
    template: LabelTemplate,
    order: Order,
    run_date: date,
    base_dir: Path,
    label_settings: ResolvedLabelSettings | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = create_preview_image(template, order, run_date, base_dir, label_settings)
    image.save(str(path), "PNG")
    return path
