from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from models import (
    AppConfig,
    AppSettings,
    ExcelSettings,
    LASER_PROCESSES,
    OPTIONAL_COLUMNS,
    PRINT_PROCESSES,
    PrintSettings,
    REQUIRED_COLUMNS,
    ReportSettings,
    VALID_LABEL_VARIANTS,
    VALID_PERSONALIZATION_TYPES,
    VALID_PROCESS_TYPES,
    VALID_STATUSES,
    LaserSettings,
    LaserTextSettings,
    LabelDefaults,
)

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


class ConfigError(Exception):
    """Raised for user-fixable settings.yaml problems."""


def load_settings(config_path: Path) -> AppSettings:
    if not config_path.exists():
        raise ConfigError(f"Ayar dosyası bulunamadı: {config_path}")

    project_root = config_path.resolve().parent.parent
    raw = _load_yaml(config_path)
    if not isinstance(raw, dict):
        raise ConfigError("settings.yaml okunamadı. Dosya YAML formatında olmalı.")

    app = _section(raw, "app")
    excel = _section(raw, "excel")
    templates = _section(raw, "templates")
    print_config = _section(raw, "print")
    label_defaults_config = raw.get("label_defaults")
    laser = _section(raw, "laser")
    laser_text = _section(raw, "laser_text")
    reports = _section(raw, "reports")

    settings = AppSettings(
        project_root=project_root,
        app=AppConfig(
            output_date_format=_required_str(app, "output_date_format"),
            language=_required_str(app, "language"),
        ),
        excel=ExcelSettings(
            mode=_required_str(excel, "mode"),
            input_file=project_root / _required_str(excel, "input_file"),
        ),
        print=PrintSettings(
            mode=str(print_config.get("mode", "data_only")).strip(),
            generate_print_data_csv=_required_bool(print_config, "generate_print_data_csv"),
            auto_print_enabled=_required_bool(print_config, "auto_print_enabled"),
            allow_direct_print=_optional_bool(print_config, "allow_direct_print", False),
            require_print_confirmation=_optional_bool(print_config, "require_print_confirmation", True),
            default_printer=str(print_config.get("default_printer", "")).strip(),
            use_default_label_settings=_optional_bool(print_config, "use_default_label_settings", True),
        ),
        label_defaults=_load_label_defaults(label_defaults_config),
        reports=ReportSettings(
            generate_errors_report=_required_bool(reports, "generate_errors_report"),
            generate_summary_report=_required_bool(reports, "generate_summary_report"),
            generate_layout_report=_required_bool(reports, "generate_layout_report"),
            generate_template_matching_report=_required_bool(
                reports,
                "generate_template_matching_report",
            ),
        ),
        input_excel=project_root / _required_str(excel, "input_file"),
        output_dir=project_root / "output",
        print_templates_dir=project_root / _required_str(templates, "print_folder"),
        laser_templates_dir=project_root / _required_str(templates, "laser_folder"),
        required_columns=list(REQUIRED_COLUMNS),
        optional_columns=list(OPTIONAL_COLUMNS),
        valid_process_types=set(VALID_PROCESS_TYPES),
        valid_personalization_types=set(VALID_PERSONALIZATION_TYPES),
        valid_label_variants=set(VALID_LABEL_VARIANTS),
        valid_statuses=set(VALID_STATUSES),
        print_processes=set(PRINT_PROCESSES),
        laser_processes=set(LASER_PROCESSES),
        laser=LaserSettings(
            auto_start_laser=_required_bool(laser, "auto_start_laser"),
            output_format=_required_str(laser, "output_format"),
            plate_width_mm=_required_positive_float(laser, "plate_width_mm"),
            plate_height_mm=_required_positive_float(laser, "plate_height_mm"),
            margin_mm=_required_non_negative_float(laser, "margin_mm"),
            gap_x_mm=_required_non_negative_float(laser, "gap_x_mm"),
            gap_y_mm=_required_non_negative_float(laser, "gap_y_mm"),
            include_order_number_guide=_required_bool(laser, "include_order_number_guide"),
        ),
        laser_text=LaserTextSettings(
            laser_font_path=project_root / _required_str(laser_text, "laser_font_path"),
            default_font_size_mm=_required_positive_float(laser_text, "default_font_size_mm"),
            min_font_size_mm=_required_positive_float(laser_text, "min_font_size_mm"),
            max_font_size_mm=_required_positive_float(laser_text, "max_font_size_mm"),
            force_connected_letters=_required_bool(laser_text, "force_connected_letters"),
            convert_text_to_paths=_required_bool(laser_text, "convert_text_to_paths"),
            warn_if_disconnected_shapes=_required_bool(laser_text, "warn_if_disconnected_shapes"),
            add_bridges_for_dots_and_accents=_required_bool(
                laser_text,
                "add_bridges_for_dots_and_accents",
            ),
        ),
    )
    _validate_settings(settings)
    _ensure_required_folders(settings)
    return settings


def print_startup_summary(settings: AppSettings) -> None:
    print("Başlangıç özeti")
    print(f"- Excel dosyası: {_display_path(settings.input_excel, settings.project_root)}")
    print(f"- Excel modu: {settings.excel.mode}")
    print(f"- Print şablonları: {_display_path(settings.print_templates_dir, settings.project_root)}")
    print(f"- Laser şablonları: {_display_path(settings.laser_templates_dir, settings.project_root)}")
    print(
        "- Plaka ölçüsü: "
        f"{_format_mm(settings.laser.plate_width_mm)} x "
        f"{_format_mm(settings.laser.plate_height_mm)} mm"
    )
    print(f"- Otomatik yazdırma: {_enabled_text(settings.print.auto_print_enabled)}")
    print(f"- Print modu: {settings.print.mode}")
    print(f"- Otomatik lazer: {_enabled_text(settings.laser.auto_start_laser)}")
    if not settings.laser_text.laser_font_path.exists():
        print(
            "- LASER_CUT font uyarısı: "
            f"{_display_path(settings.laser_text.laser_font_path, settings.project_root)} bulunamadı. "
            "LASER_CUT siparişleri güvenlik için hata raporuna yazılır."
        )
    print("")


def _load_yaml(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        if yaml is not None:
            return yaml.safe_load(file) or {}
        return _load_simple_yaml(file.read())


def _section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"settings.yaml içinde '{key}' bölümü eksik.")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if value is None or str(value).strip() == "":
        raise ConfigError(f"settings.yaml içinde '{key}' ayarı eksik.")
    return str(value).strip()


def _required_bool(section: dict[str, Any], key: str) -> bool:
    if key not in section:
        raise ConfigError(f"settings.yaml içinde '{key}' ayarı eksik.")
    value = section[key]
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    raise ConfigError(f"settings.yaml içinde '{key}' true veya false olmalı.")


def _optional_bool(section: dict[str, Any], key: str, default: bool) -> bool:
    if key not in section:
        return default
    return _required_bool(section, key)


def _load_label_defaults(section: Any) -> LabelDefaults | None:
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ConfigError("settings.yaml içinde 'label_defaults' bölümü YAML object olmalı.")
    return LabelDefaults(
        media_type=str(section.get("media_type", "ROLL")).strip().upper(),
        label_width_mm=_required_positive_float(section, "label_width_mm"),
        label_height_mm=_required_positive_float(section, "label_height_mm"),
        roll_gap_mm=_optional_non_negative_float(section, "roll_gap_mm", 3),
        printer_dpi=int(_optional_positive_float(section, "printer_dpi", 300)),
        default_copies=int(_optional_positive_float(section, "default_copies", 1)),
        horizontal_offset_mm=_optional_float(section, "horizontal_offset_mm", 0),
        vertical_offset_mm=_optional_float(section, "vertical_offset_mm", 0),
        scale_percent=_optional_positive_float(section, "scale_percent", 100),
        background_enabled=_optional_bool(section, "background_enabled", True),
        show_cut_boundary=_optional_bool(section, "show_cut_boundary", False),
        safe_margin_mm=_optional_non_negative_float(section, "safe_margin_mm", 1.5),
        show_order_number_on_label=_optional_bool(section, "show_order_number_on_label", False),
    )


def _required_positive_float(section: dict[str, Any], key: str) -> float:
    value = _required_float(section, key)
    if value <= 0:
        raise ConfigError(f"settings.yaml içinde '{key}' 0'dan büyük olmalı.")
    return value


def _required_non_negative_float(section: dict[str, Any], key: str) -> float:
    value = _required_float(section, key)
    if value < 0:
        raise ConfigError(f"settings.yaml içinde '{key}' negatif olamaz.")
    return value


def _required_float(section: dict[str, Any], key: str) -> float:
    if key not in section:
        raise ConfigError(f"settings.yaml içinde '{key}' ayarı eksik.")
    try:
        return float(section[key])
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"settings.yaml içinde '{key}' sayı olmalı.") from exc


def _optional_float(section: dict[str, Any], key: str, default: float) -> float:
    if key not in section:
        return default
    try:
        return float(section[key])
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"settings.yaml içinde '{key}' sayı olmalı.") from exc


def _optional_positive_float(section: dict[str, Any], key: str, default: float) -> float:
    value = _optional_float(section, key, default)
    if value <= 0:
        raise ConfigError(f"settings.yaml içinde '{key}' 0'dan büyük olmalı.")
    return value


def _optional_non_negative_float(section: dict[str, Any], key: str, default: float) -> float:
    value = _optional_float(section, key, default)
    if value < 0:
        raise ConfigError(f"settings.yaml içinde '{key}' negatif olamaz.")
    return value


def _validate_settings(settings: AppSettings) -> None:
    if settings.excel.mode != "clean_production_excel":
        raise ConfigError(
            "Excel modu desteklenmiyor. settings.yaml içinde "
            "excel.mode değeri 'clean_production_excel' olmalı."
        )
    try:
        date.today().strftime(settings.app.output_date_format)
    except ValueError as exc:
        raise ConfigError(
            "app.output_date_format geçerli bir tarih formatı olmalı. "
            "Örnek: '%Y-%m-%d'"
        ) from exc
    if settings.laser.output_format.lower() != "svg":
        raise ConfigError(
            "Lazer çıktı formatı desteklenmiyor. settings.yaml içinde "
            "laser.output_format değeri 'svg' olmalı."
        )
    if settings.laser.margin_mm * 2 >= settings.laser.plate_width_mm:
        raise ConfigError("Lazer margin_mm plaka genişliğine göre çok büyük.")
    if settings.laser.margin_mm * 2 >= settings.laser.plate_height_mm:
        raise ConfigError("Lazer margin_mm plaka yüksekliğine göre çok büyük.")
    if settings.laser_text.min_font_size_mm > settings.laser_text.default_font_size_mm:
        raise ConfigError("laser_text.min_font_size_mm varsayılan font boyutundan büyük olamaz.")
    if settings.laser_text.default_font_size_mm > settings.laser_text.max_font_size_mm:
        raise ConfigError("laser_text.default_font_size_mm maksimum font boyutundan büyük olamaz.")
    if settings.print.auto_print_enabled:
        raise ConfigError(
            "Güvenlik nedeniyle MVP'de print.auto_print_enabled false olmalı. "
            "Sistem otomatik yazdırma yapmaz."
        )
    if settings.print.mode not in {"data_only", "label_designer"}:
        raise ConfigError("print.mode 'data_only' veya 'label_designer' olmalı.")
    if settings.print.allow_direct_print:
        raise ConfigError(
            "Güvenlik nedeniyle bu fazda print.allow_direct_print false olmalı. "
            "Sistem direkt yazdırma yapmaz."
        )
    if settings.label_defaults is not None:
        if settings.label_defaults.media_type != "ROLL":
            raise ConfigError("label_defaults.media_type bu fazda 'ROLL' olmalı.")
        if settings.label_defaults.printer_dpi not in {203, 300, 600}:
            print("Uyarı: printer_dpi standart değerlerden farklı. Test baskısı yapın.")
    if settings.laser.auto_start_laser:
        raise ConfigError(
            "Güvenlik nedeniyle MVP'de laser.auto_start_laser false olmalı. "
            "Sistem lazeri başlatmaz."
        )


def _ensure_required_folders(settings: AppSettings) -> None:
    for path in (
        settings.input_excel.parent,
        settings.output_dir,
        settings.print_templates_dir,
        settings.project_root / "templates" / "designs",
        settings.laser_templates_dir,
        settings.laser_text.laser_font_path.parent,
        settings.project_root / "assets" / "label_backgrounds",
    ):
        path.mkdir(parents=True, exist_ok=True)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _format_mm(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def _enabled_text(value: bool) -> str:
    return "aktif" if value else "kapalı"


def _load_simple_yaml(content: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_section: str | None = None

    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":"):
            current_section = line[:-1]
            result[current_section] = {}
            continue

        if indent == 0 and ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = _parse_scalar(value.strip())
            current_section = None
            continue

        if indent == 2 and ":" in line and current_section:
            key, value = line.split(":", 1)
            result[current_section][key.strip()] = _parse_scalar(value.strip())

    return result


def _parse_scalar(value: str) -> str | bool | int | float:
    text = value.strip().strip('"').strip("'")
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text
