from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = [
    "order_no",
    "buyer_name",
    "product_name",
    "model_no",
    "template_no",
    "process_type",
    "personalization_type",
    "label_variant",
    "label_text",
    "laser_text",
    "quantity",
    "material_type",
    "material_thickness_mm",
    "extra_chocolate_qty",
    "extra_madlen_qty",
    "production_note",
    "needs_review",
    "status",
]

OPTIONAL_COLUMNS: list[str] = [
    "date_text",
    "note_text",
    "custom_text_1",
    "custom_text_2",
    "custom_text_3",
]

PRINT = "PRINT"
LASER_ENGRAVE = "LASER_ENGRAVE"
LASER_CUT = "LASER_CUT"
BOTH = "BOTH"
NONE = "NONE"

PERSONALIZATION_LABEL = "LABEL"
PERSONALIZATION_NAME = "NAME"
PERSONALIZATION_LABEL_AND_NAME = "LABEL_AND_NAME"
PERSONALIZATION_NO_PERSONALIZATION = "NO_PERSONALIZATION"

LABEL_VARIANT_GOLD = "GOLD"
LABEL_VARIANT_SILVER = "SILVER"
LABEL_VARIANT_WHITE = "WHITE"
LABEL_VARIANT_RED = "RED"
LABEL_VARIANT_CUSTOM = "CUSTOM"
LABEL_VARIANT_NONE = "NONE"

TEMPLATE_OK = "OK"
TEMPLATE_MISSING = "MISSING"
TEMPLATE_NEEDS_REVIEW = "NEEDS_REVIEW"

VALID_PROCESS_TYPES = {PRINT, LASER_ENGRAVE, LASER_CUT, BOTH, NONE}
VALID_PERSONALIZATION_TYPES = {
    PERSONALIZATION_LABEL,
    PERSONALIZATION_NAME,
    PERSONALIZATION_LABEL_AND_NAME,
    PERSONALIZATION_NO_PERSONALIZATION,
}
VALID_LABEL_VARIANTS = {
    LABEL_VARIANT_GOLD,
    LABEL_VARIANT_SILVER,
    LABEL_VARIANT_WHITE,
    LABEL_VARIANT_RED,
    LABEL_VARIANT_CUSTOM,
    LABEL_VARIANT_NONE,
}
VALID_STATUSES = {"NEW", "READY", "NEEDS_REVIEW", "COMPLETED", "CANCELLED"}
PRINT_PROCESSES = {PRINT, BOTH}
LASER_PROCESSES = {LASER_ENGRAVE, LASER_CUT, BOTH}


@dataclass(frozen=True)
class AppConfig:
    output_date_format: str
    language: str


@dataclass(frozen=True)
class ExcelSettings:
    mode: str
    input_file: Path


@dataclass(frozen=True)
class PrintSettings:
    mode: str = "data_only"
    generate_print_data_csv: bool = True
    auto_print_enabled: bool = False
    allow_direct_print: bool = False
    require_print_confirmation: bool = True
    default_printer: str = ""
    use_default_label_settings: bool = True


@dataclass(frozen=True)
class LabelDefaults:
    media_type: str = "ROLL"
    label_width_mm: float = 50
    label_height_mm: float = 30
    roll_gap_mm: float = 3
    printer_dpi: int = 300
    default_copies: int = 1
    horizontal_offset_mm: float = 0
    vertical_offset_mm: float = 0
    scale_percent: float = 100
    background_enabled: bool = True
    show_cut_boundary: bool = False
    safe_margin_mm: float = 1.5
    show_order_number_on_label: bool = False


@dataclass(frozen=True)
class LaserSettings:
    auto_start_laser: bool
    output_format: str
    plate_width_mm: float
    plate_height_mm: float
    margin_mm: float
    gap_x_mm: float
    gap_y_mm: float
    include_order_number_guide: bool


@dataclass(frozen=True)
class LaserTextSettings:
    laser_font_path: Path
    default_font_size_mm: float
    min_font_size_mm: float
    max_font_size_mm: float
    force_connected_letters: bool
    convert_text_to_paths: bool
    warn_if_disconnected_shapes: bool
    add_bridges_for_dots_and_accents: bool


@dataclass(frozen=True)
class ReportSettings:
    generate_errors_report: bool
    generate_summary_report: bool
    generate_layout_report: bool
    generate_template_matching_report: bool


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    app: AppConfig
    excel: ExcelSettings
    print: PrintSettings
    label_defaults: LabelDefaults | None
    reports: ReportSettings
    input_excel: Path
    output_dir: Path
    print_templates_dir: Path
    laser_templates_dir: Path
    required_columns: list[str]
    optional_columns: list[str]
    valid_process_types: set[str]
    valid_personalization_types: set[str]
    valid_label_variants: set[str]
    valid_statuses: set[str]
    print_processes: set[str]
    laser_processes: set[str]
    laser: LaserSettings
    laser_text: LaserTextSettings


@dataclass(frozen=True)
class Order:
    row_number: int
    order_no: str
    buyer_name: str
    product_name: str
    model_no: str
    template_no: str
    process_type: str
    personalization_type: str
    label_variant: str
    label_text: str
    laser_text: str
    quantity: int
    material_type: str
    material_thickness_mm: str
    extra_chocolate_qty: int
    extra_madlen_qty: int
    production_note: str
    needs_review: str
    status: str
    source: dict[str, Any]


@dataclass(frozen=True)
class PrintTemplateMatch:
    status: str
    files: list[Path]


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int | str
    order_no: str
    field: str
    message: str


@dataclass(frozen=True)
class LaserPlacement:
    plate_file: Path
    order_no: str
    buyer_name: str
    product_name: str
    laser_text: str
    model_no: str
    process_type: str
    material_type: str
    material_thickness_mm: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    font_size: float
    font_name: str
    connected_status: str
    disconnected_parts_count: int
    status: str
    warning: str


@dataclass(frozen=True)
class ProductionPaths:
    run_dir: Path
    print_dir: Path
    laser_dir: Path
    reports_dir: Path
    logs_dir: Path
