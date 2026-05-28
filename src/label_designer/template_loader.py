from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .template_schema import LabelElement, LabelTemplate


SUPPORTED_ELEMENT_TYPES = {"text", "image", "rectangle", "line"}


class LabelTemplateError(ValueError):
    pass


def load_template(path: Path) -> LabelTemplate:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise LabelTemplateError(f"Template JSON object olmalı: {path}")

    fields_raw = raw.get("fields", [])
    if fields_raw in (None, ""):
        fields_raw = []
    if not isinstance(fields_raw, list):
        raise LabelTemplateError(f"Template fields list olmalı: {path}")

    elements_raw = raw.get("elements", [])
    if not isinstance(elements_raw, list):
        raise LabelTemplateError(f"Template elements list olmalı: {path}")
    elements_raw = [*_fields_to_text_elements(fields_raw, path), *elements_raw]

    elements: list[LabelElement] = []
    for element in elements_raw:
        if not isinstance(element, dict):
            raise LabelTemplateError(f"Template element object olmalı: {path}")
        element_type = str(element.get("type", "")).strip()
        if element_type not in SUPPORTED_ELEMENT_TYPES:
            raise LabelTemplateError(f"Desteklenmeyen element type '{element_type}': {path}")
        elements.append(LabelElement(type=element_type, raw=element))

    return LabelTemplate(
        template_id=str(raw.get("template_id") or _default_template_id(raw)).strip(),
        model_no=_required_str(raw, "model_no", path),
        template_no=_required_str(raw, "template_no", path),
        label_variant=_required_str(raw, "label_variant", path).upper(),
        canvas_width_mm=_optional_float(raw, "canvas_width_mm", None, path) or _optional_float(raw, "label_width_mm", None, path) or 0,
        canvas_height_mm=_optional_float(raw, "canvas_height_mm", None, path) or _optional_float(raw, "label_height_mm", None, path) or 0,
        media_type=str(raw.get("media_type", "ROLL") or "ROLL").strip().upper(),
        label_width_mm=_optional_float(raw, "label_width_mm", None, path),
        label_height_mm=_optional_float(raw, "label_height_mm", None, path),
        roll_gap_mm=_optional_float(raw, "roll_gap_mm", None, path),
        printer_dpi=_optional_int(raw, "printer_dpi", None, path),
        copies_per_order=_optional_int(raw, "copies_per_order", None, path),
        horizontal_offset_mm=_optional_float(raw, "horizontal_offset_mm", None, path),
        vertical_offset_mm=_optional_float(raw, "vertical_offset_mm", None, path),
        scale_percent=_optional_float(raw, "scale_percent", None, path),
        show_order_number_on_label=_optional_bool(raw, "show_order_number_on_label", None, path),
        background_enabled=_optional_bool(raw, "background_enabled", None, path),
        model_name=str(raw.get("model_name", "") or raw.get("template_name", "") or ""),
        source_design_file=str(raw.get("source_file", "") or ""),
        preview_image=str(raw.get("preview_image", "") or ""),
        active=_optional_bool(raw, "active", True, path) is not False,
        fields=[dict(field) for field in fields_raw if isinstance(field, dict)],
        background_image=str(raw.get("background_image", "") or ""),
        elements=elements,
        source_file=path,
    )


def find_template(templates_dir: Path, model_no: str, template_no: str, label_variant: str) -> LabelTemplate | None:
    matches = []
    if not templates_dir.exists():
        return None
    for path in sorted(templates_dir.glob("*.json")):
        template = load_template(path)
        if not template.active:
            continue
        if (
            template.model_no == str(model_no)
            and template.template_no.upper() == str(template_no).upper()
            and template.label_variant.upper() == str(label_variant).upper()
        ):
            matches.append(template)
    if len(matches) != 1:
        return None
    return matches[0]


def list_templates(templates_dir: Path) -> list[LabelTemplate]:
    if not templates_dir.exists():
        return []
    return [load_template(path) for path in sorted(templates_dir.glob("*.json"))]


def _fields_to_text_elements(fields_raw: list[object], path: Path) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for index, field in enumerate(fields_raw, start=1):
        if not isinstance(field, dict):
            raise LabelTemplateError(f"Template field object olmalı: {path}")
        excel_column = str(field.get("excel_column", "") or "").strip()
        placeholder = str(field.get("placeholder", "") or "").strip()
        if not placeholder and excel_column:
            placeholder = "{{" + excel_column.upper() + "}}"
        if not placeholder:
            placeholder = "{{LABEL_TEXT}}"
        element = {
            "type": "text",
            "id": str(field.get("id") or field.get("field_name") or f"field_{index}"),
            "placeholder": placeholder,
            "x_mm": field.get("x_mm", 0),
            "y_mm": field.get("y_mm", 0),
            "width_mm": field.get("width_mm", 10),
            "height_mm": field.get("height_mm", 5),
            "font_family": field.get("font_family", "Segoe UI"),
            "font_path": field.get("font_path", ""),
            "font_size": field.get("font_size", 10),
            "line_height": field.get("line_height", 1.18),
            "color": field.get("color", "#111111"),
            "bold": field.get("bold", False),
            "italic": field.get("italic", False),
            "align": field.get("align", "center"),
            "vertical_align": field.get("vertical_align", "middle"),
            "rotation": field.get("rotation", 0),
            "visible": field.get("visible", True),
            "excel_column": excel_column,
            "field_name": str(field.get("field_name", "")),
        }
        elements.append(element)
    return elements


def _required_str(raw: dict[str, Any], key: str, path: Path) -> str:
    value = raw.get(key)
    if value is None or str(value).strip() == "":
        raise LabelTemplateError(f"Template içinde '{key}' eksik: {path}")
    return str(value).strip()


def _default_template_id(raw: dict[str, Any]) -> str:
    return f"{raw.get('model_no', '')}_{raw.get('template_no', '')}_{raw.get('label_variant', '')}".strip("_").lower()


def _required_float(raw: dict[str, Any], key: str, path: Path) -> float:
    try:
        value = float(raw[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise LabelTemplateError(f"Template içinde '{key}' sayı olmalı: {path}") from exc
    if value <= 0:
        raise LabelTemplateError(f"Template içinde '{key}' 0'dan büyük olmalı: {path}")
    return value


def _optional_float(raw: dict[str, Any], key: str, default: float | None, path: Path) -> float | None:
    if key not in raw or raw[key] in (None, ""):
        return default
    try:
        value = float(raw[key])
    except (TypeError, ValueError) as exc:
        raise LabelTemplateError(f"Template içinde '{key}' sayı olmalı: {path}") from exc
    if value <= 0 and key not in {"horizontal_offset_mm", "vertical_offset_mm"}:
        raise LabelTemplateError(f"Template içinde '{key}' 0'dan büyük olmalı: {path}")
    return value


def _optional_int(raw: dict[str, Any], key: str, default: int | None, path: Path) -> int | None:
    value = _optional_float(raw, key, None, path)
    return default if value is None else int(value)


def _optional_bool(raw: dict[str, Any], key: str, default: bool | None, path: Path) -> bool | None:
    if key not in raw or raw[key] in (None, ""):
        return default
    value = raw[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "evet"}:
            return True
        if normalized in {"false", "0", "no", "hayır", "hayir"}:
            return False
    raise LabelTemplateError(f"Template içinde '{key}' true/false olmalı: {path}")
