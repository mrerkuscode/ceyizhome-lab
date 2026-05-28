from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LabelElement:
    type: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class LabelTemplate:
    template_id: str
    model_no: str
    template_no: str
    label_variant: str
    canvas_width_mm: float
    canvas_height_mm: float
    media_type: str
    label_width_mm: float | None
    label_height_mm: float | None
    roll_gap_mm: float | None
    printer_dpi: int | None
    copies_per_order: int | None
    horizontal_offset_mm: float | None
    vertical_offset_mm: float | None
    scale_percent: float | None
    show_order_number_on_label: bool | None
    background_enabled: bool | None
    model_name: str
    source_design_file: str
    preview_image: str
    active: bool
    fields: list[dict[str, Any]]
    background_image: str
    elements: list[LabelElement]
    source_file: Path


@dataclass(frozen=True)
class ResolvedLabelSettings:
    media_type: str
    label_width_mm: float
    label_height_mm: float
    roll_gap_mm: float
    printer_dpi: int
    copies_per_order: int
    horizontal_offset_mm: float
    vertical_offset_mm: float
    scale_percent: float
    background_enabled: bool
    show_cut_boundary: bool
    safe_margin_mm: float
    show_order_number_on_label: bool
    used_settings_source: str
    warning: str
