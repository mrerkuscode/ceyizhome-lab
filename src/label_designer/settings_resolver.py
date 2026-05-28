from __future__ import annotations

from models import AppSettings

from .template_schema import LabelTemplate, ResolvedLabelSettings


class LabelSettingsError(ValueError):
    pass


def resolve_label_settings(
    template: LabelTemplate,
    settings: AppSettings,
    used_settings_source: str = "TEMPLATE",
) -> ResolvedLabelSettings:
    defaults = settings.label_defaults
    has_template_size = template.label_width_mm is not None and template.label_height_mm is not None

    if has_template_size:
        source = used_settings_source
        width = float(template.label_width_mm or 0)
        height = float(template.label_height_mm or 0)
    elif defaults is not None and settings.print.use_default_label_settings:
        source = "DEFAULT_CONFIG"
        width = defaults.label_width_mm
        height = defaults.label_height_mm
    else:
        raise LabelSettingsError("Varsayılan rulo etiket ölçüsü tanımlı değil.")

    if width <= 0 or height <= 0:
        raise LabelSettingsError("Rulo etiket genişliği ve yüksekliği 0'dan büyük olmalıdır.")

    warning_parts: list[str] = []
    if not has_template_size:
        warning_parts.append("Bu şablonda özel ölçü yok. Varsayılan rulo etiket ölçüsü kullanıldı.")

    roll_gap = _first_number(template.roll_gap_mm, defaults.roll_gap_mm if defaults else None, 3)
    printer_dpi = int(_first_number(template.printer_dpi, defaults.printer_dpi if defaults else None, 300))
    copies = int(_first_number(template.copies_per_order, defaults.default_copies if defaults else None, 1))
    horizontal_offset = _first_number(template.horizontal_offset_mm, defaults.horizontal_offset_mm if defaults else None, 0)
    vertical_offset = _first_number(template.vertical_offset_mm, defaults.vertical_offset_mm if defaults else None, 0)
    scale_percent = _first_number(template.scale_percent, defaults.scale_percent if defaults else None, 100)
    background_enabled = (
        template.background_enabled
        if template.background_enabled is not None
        else (defaults.background_enabled if defaults else True)
    )
    show_cut_boundary = defaults.show_cut_boundary if defaults else False
    safe_margin = defaults.safe_margin_mm if defaults else 1.5
    show_order_number = (
        template.show_order_number_on_label
        if template.show_order_number_on_label is not None
        else (defaults.show_order_number_on_label if defaults else False)
    )

    if printer_dpi not in {203, 300, 600}:
        warning_parts.append("Yazıcı DPI standart değerlerden farklı. Test baskısı yapın.")
    if scale_percent != 100:
        warning_parts.append("Etiket baskısında ölçek genelde %100 olmalıdır. Lütfen test baskısı yapın.")
    if horizontal_offset or vertical_offset:
        warning_parts.append("Yazdırma pozisyonu kaydırma ayarı uygulanıyor.")

    return ResolvedLabelSettings(
        media_type=template.media_type or (defaults.media_type if defaults else "ROLL"),
        label_width_mm=width,
        label_height_mm=height,
        roll_gap_mm=roll_gap,
        printer_dpi=printer_dpi,
        copies_per_order=max(1, copies),
        horizontal_offset_mm=horizontal_offset,
        vertical_offset_mm=vertical_offset,
        scale_percent=scale_percent,
        background_enabled=background_enabled,
        show_cut_boundary=show_cut_boundary,
        safe_margin_mm=safe_margin,
        show_order_number_on_label=bool(show_order_number),
        used_settings_source=source,
        warning=" ".join(warning_parts),
    )


def _first_number(*values: float | int | None) -> float:
    for value in values:
        if value is not None:
            return float(value)
    return 0
