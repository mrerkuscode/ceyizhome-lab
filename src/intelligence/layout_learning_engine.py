"""Learning-aware layout engine for labels and laser/name-cut jobs.

The module is intentionally deterministic. It scores and suggests layouts from
known text fields, model dimensions, and locally learned model profiles. LLMs may
explain a recommendation elsewhere, but the production layout decision is kept
measurable and testable here.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean
from typing import Any


SCHEMA_VERSION = 1
STORE_RELATIVE_PATH = Path("data") / "layout_learning_profiles.json"
MAX_APPROVED_LAYOUTS = 120
MAX_USER_ADJUSTMENTS = 160


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if number != number:  # NaN
            return default
        return number
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _score(value: float) -> int:
    return int(round(_clamp(value)))


def _project_root(path: Path | str | None = None) -> Path:
    return Path(path or ".").resolve()


def learning_store_path(project_root: Path | str | None = None) -> Path:
    return _project_root(project_root) / STORE_RELATIVE_PATH


def _load_store(project_root: Path | str | None = None) -> dict[str, Any]:
    path = learning_store_path(project_root)
    if not path.exists():
        return {"schemaVersion": SCHEMA_VERSION, "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": SCHEMA_VERSION, "profiles": {}}
    if not isinstance(data, dict):
        return {"schemaVersion": SCHEMA_VERSION, "profiles": {}}
    data.setdefault("schemaVersion", SCHEMA_VERSION)
    data.setdefault("profiles", {})
    return data


def _save_store(store: dict[str, Any], project_root: Path | str | None = None) -> None:
    path = learning_store_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _model_id(model: dict[str, Any] | None, model_id: str | None = None) -> str:
    if model_id:
        return str(model_id)
    model = model or {}
    return str(
        model.get("modelId")
        or model.get("model_id")
        or model.get("id")
        or model.get("path")
        or model.get("modelName")
        or model.get("model_name")
        or "__default__"
    )


def _model_name(model: dict[str, Any] | None) -> str:
    model = model or {}
    return str(model.get("modelName") or model.get("model_name") or model.get("name") or model.get("title") or "Etiket modeli")


def _label_size(model: dict[str, Any] | None) -> dict[str, float]:
    model = model or {}
    width = _safe_float(model.get("labelWidthMm") or model.get("label_width_mm") or model.get("canvas_width_mm"), 50.0)
    height = _safe_float(model.get("labelHeightMm") or model.get("label_height_mm") or model.get("canvas_height_mm"), 30.0)
    return {"width": max(10.0, min(300.0, width)), "height": max(10.0, min(300.0, height))}


def _safe_area(model: dict[str, Any] | None) -> dict[str, float]:
    size = _label_size(model)
    safe = (model or {}).get("safeArea") or (model or {}).get("safe_area") or {}
    pad = max(1.5, min(size["width"], size["height"]) * 0.05)
    left = _safe_float(safe.get("left") or safe.get("leftMm"), pad)
    top = _safe_float(safe.get("top") or safe.get("topMm"), pad)
    right = _safe_float(safe.get("right") or safe.get("rightMm"), pad)
    bottom = _safe_float(safe.get("bottom") or safe.get("bottomMm"), pad)
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def get_learning_profile(
    project_root: Path | str | None,
    model_id: str,
    *,
    model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _load_store(project_root)
    profiles = store.setdefault("profiles", {})
    profile = profiles.get(model_id)
    size = _label_size(model)
    if not profile:
        profile = {
            "modelId": model_id,
            "modelName": _model_name(model),
            "labelWidthMm": size["width"],
            "labelHeightMm": size["height"],
            "safeArea": _safe_area(model),
            "defaultNameBox": None,
            "defaultDateBox": None,
            "defaultNoteBox": None,
            "defaultLaserBox": None,
            "approvedLayouts": [],
            "rejectedLayouts": [],
            "userAdjustments": [],
            "learnedRules": {},
            "lastUpdated": _now_iso(),
        }
        profiles[model_id] = profile
        _save_store(store, project_root)
    return deepcopy(profile)


def _field_column(field: dict[str, Any]) -> str:
    return str(field.get("excel_column") or field.get("column") or field.get("field") or field.get("type") or "")


def _field_text(field: dict[str, Any], values: dict[str, Any]) -> str:
    column = _field_column(field)
    return str(values.get(column) or field.get("text") or field.get("value") or "")


def _numeric_field(field: dict[str, Any]) -> dict[str, Any]:
    next_field = deepcopy(field)
    next_field["x_mm"] = _safe_float(field.get("x_mm") or field.get("x"), 0.0)
    next_field["y_mm"] = _safe_float(field.get("y_mm") or field.get("y"), 0.0)
    next_field["width_mm"] = _safe_float(field.get("width_mm") or field.get("width"), 10.0)
    next_field["height_mm"] = _safe_float(field.get("height_mm") or field.get("height"), 5.0)
    next_field["font_size"] = _safe_float(field.get("font_size") or field.get("fontSize"), 12.0)
    next_field["line_height"] = _safe_float(field.get("line_height") or field.get("lineHeight"), 1.15)
    return next_field


def _estimate_text_box(field: dict[str, Any], text: str) -> dict[str, float]:
    font_size = max(1.0, _safe_float(field.get("font_size"), 12.0))
    line_height = max(0.8, _safe_float(field.get("line_height"), 1.15))
    lines = [line for line in str(text or "").splitlines()] or [""]
    max_len = max((len(line) for line in lines), default=0)
    raw_width = max_len * font_size * 0.24
    box_width = _safe_float(field.get("width_mm"), 0.0)
    wrapped_lines = len(lines)
    width = raw_width
    if box_width and raw_width > box_width and any(token in str(text or "") for token in (" ", "&", "/", "-")):
        chars_per_line = max(1, int(box_width / max(1.0, font_size * 0.24)))
        wrapped_lines = max(wrapped_lines, int((max_len + chars_per_line - 1) / chars_per_line))
        width = box_width * 0.96
    height = wrapped_lines * font_size * line_height * 0.38
    return {"width": width, "height": height}


def _field_overflows(field: dict[str, Any], text: str) -> bool:
    estimated = _estimate_text_box(field, text)
    return estimated["width"] > _safe_float(field.get("width_mm"), 0.0) or estimated["height"] > _safe_float(field.get("height_mm"), 0.0)


def _group_bounds(fields: list[dict[str, Any]]) -> dict[str, float]:
    if not fields:
        return {"x": 0.0, "y": 0.0, "right": 0.0, "bottom": 0.0, "width": 0.0, "height": 0.0}
    left = min(_safe_float(field.get("x_mm"), 0.0) for field in fields)
    top = min(_safe_float(field.get("y_mm"), 0.0) for field in fields)
    right = max(_safe_float(field.get("x_mm"), 0.0) + _safe_float(field.get("width_mm"), 0.0) for field in fields)
    bottom = max(_safe_float(field.get("y_mm"), 0.0) + _safe_float(field.get("height_mm"), 0.0) for field in fields)
    return {"x": left, "y": top, "right": right, "bottom": bottom, "width": max(0.0, right - left), "height": max(0.0, bottom - top)}


def _is_inside_safe_area(field: dict[str, Any], model: dict[str, Any] | None) -> bool:
    size = _label_size(model)
    safe = _safe_area(model)
    x = _safe_float(field.get("x_mm"), 0.0)
    y = _safe_float(field.get("y_mm"), 0.0)
    width = _safe_float(field.get("width_mm"), 0.0)
    height = _safe_float(field.get("height_mm"), 0.0)
    return (
        x >= safe["left"]
        and y >= safe["top"]
        and x + width <= size["width"] - safe["right"]
        and y + height <= size["height"] - safe["bottom"]
    )


def calculate_layout_quality(
    layout: dict[str, Any] | list[dict[str, Any]],
    model: dict[str, Any] | None,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return readability, balance, whitespace, safety and laser scores."""

    if isinstance(layout, list):
        fields = layout
        values = values or {}
    else:
        fields = layout.get("fields") or layout.get("_fields") or []
        values = values or layout.get("values") or {}
    normalized = [_numeric_field(field) for field in fields]
    active: list[dict[str, Any]] = []
    warnings: list[str] = []

    for field in normalized:
        text = _field_text(field, values).strip()
        if not text:
            continue
        active.append(field)

    if not active:
        return {
            "readabilityScore": 0,
            "balanceScore": 0,
            "whitespaceScore": 0,
            "safeAreaScore": 0,
            "overflowScore": 0,
            "laserFitScore": 100,
            "layoutQualityScore": 0,
            "warnings": ["No text fields to evaluate."],
        }

    readability_values: list[float] = []
    overflow_values: list[float] = []
    safe_values: list[float] = []
    font_by_column: dict[str, float] = {}

    for field in active:
        column = _field_column(field)
        text = _field_text(field, values).strip()
        font = _safe_float(field.get("font_size"), 12.0)
        font_by_column[column] = font
        min_font = 14.0 if column == "label_text" else 10.0
        if column == "name_cut_text":
            min_font = 12.0
        readability_values.append(_clamp((font / min_font) * 100.0))
        overflow_values.append(35.0 if _field_overflows(field, text) else 100.0)
        safe_values.append(100.0 if _is_inside_safe_area(field, model) else 45.0)
        if _field_overflows(field, text):
            warnings.append(f"{column or 'text'} overflows its box.")
        if not _is_inside_safe_area(field, model):
            warnings.append(f"{column or 'text'} is outside the safe area.")

    name_font = font_by_column.get("label_text") or max(font_by_column.values())
    ratios: list[float] = []
    if font_by_column.get("date_text"):
        ratios.append(_safe_float(font_by_column["date_text"]) / max(1.0, name_font))
    if font_by_column.get("note_text"):
        ratios.append(_safe_float(font_by_column["note_text"]) / max(1.0, name_font))
    ratio_scores = []
    for ratio in ratios:
        if 0.38 <= ratio <= 0.72:
            ratio_scores.append(100.0)
        else:
            ratio_scores.append(max(35.0, 100.0 - abs(ratio - 0.55) * 150.0))
    balance_score = mean(ratio_scores) if ratio_scores else 88.0

    size = _label_size(model)
    bounds = _group_bounds(active)
    area_ratio = (bounds["width"] * bounds["height"]) / max(1.0, size["width"] * size["height"])
    center_x = bounds["x"] + bounds["width"] / 2.0
    center_y = bounds["y"] + bounds["height"] / 2.0
    center_penalty = (abs(center_x - size["width"] / 2.0) / size["width"] + abs(center_y - size["height"] / 2.0) / size["height"]) * 120.0
    if area_ratio < 0.07:
        whitespace_score = 45.0 + area_ratio * 450.0
        warnings.append("Text group is visually too small for the label.")
    elif area_ratio > 0.55:
        whitespace_score = 82.0
    else:
        whitespace_score = 100.0
    whitespace_score = _clamp(whitespace_score - center_penalty)
    average_font_ratio = mean([_safe_float(field.get("font_size"), 12.0) for field in active]) / max(1.0, size["height"])
    if average_font_ratio < 0.43:
        whitespace_score = min(whitespace_score, 58.0 + average_font_ratio * 70.0)
        warnings.append("Text sizes are small compared with the label.")

    laser_text = str(values.get("name_cut_text") or values.get("laserNameText") or values.get("laserName") or "").strip()
    laser_score = 100.0
    if laser_text:
        laser_field = next((field for field in active if _field_column(field) == "name_cut_text"), None)
        laser_width = _safe_float((model or {}).get("laserWidthMm") or (model or {}).get("laser_width_mm"), 42.0)
        laser_height = _safe_float((model or {}).get("laserHeightMm") or (model or {}).get("laser_height_mm"), 10.0)
        laser_font = _safe_float(laser_field.get("font_size") if laser_field else 12.0, 12.0)
        estimated_width = len(laser_text.replace(" ", "")) * laser_font * 0.42
        estimated_height = laser_font * 0.55
        width_score = 100.0 if estimated_width <= laser_width else max(25.0, 100.0 - (estimated_width - laser_width) * 2.5)
        height_score = 100.0 if estimated_height <= laser_height else max(30.0, 100.0 - (estimated_height - laser_height) * 8.0)
        laser_score = min(width_score, height_score)
        if laser_score < 75:
            warnings.append("Laser name may not fit in the cutting area.")

    component_scores = {
        "readabilityScore": mean(readability_values),
        "balanceScore": balance_score,
        "whitespaceScore": whitespace_score,
        "safeAreaScore": mean(safe_values),
        "overflowScore": mean(overflow_values),
        "laserFitScore": laser_score,
    }
    quality = (
        component_scores["readabilityScore"] * 0.22
        + component_scores["balanceScore"] * 0.16
        + component_scores["whitespaceScore"] * 0.18
        + component_scores["safeAreaScore"] * 0.18
        + component_scores["overflowScore"] * 0.18
        + component_scores["laserFitScore"] * 0.08
    )
    return {
        **{key: _score(value) for key, value in component_scores.items()},
        "layoutQualityScore": _score(quality),
        "warnings": warnings,
    }


def _fit_font_to_box(field: dict[str, Any], text: str, *, min_font: float) -> dict[str, Any]:
    next_field = deepcopy(field)
    while _safe_float(next_field.get("font_size"), 12.0) > min_font and _field_overflows(next_field, text):
        next_field["font_size"] = round(max(min_font, _safe_float(next_field.get("font_size"), 12.0) - 0.7), 1)
    return next_field


def _clamp_field(field: dict[str, Any], model: dict[str, Any] | None) -> dict[str, Any]:
    size = _label_size(model)
    safe = _safe_area(model)
    next_field = deepcopy(field)
    width = min(_safe_float(next_field.get("width_mm"), 10.0), size["width"] - safe["left"] - safe["right"])
    height = min(_safe_float(next_field.get("height_mm"), 5.0), size["height"] - safe["top"] - safe["bottom"])
    next_field["width_mm"] = round(max(2.0, width), 1)
    next_field["height_mm"] = round(max(2.0, height), 1)
    next_field["x_mm"] = round(_clamp(_safe_float(next_field.get("x_mm"), 0.0), safe["left"], size["width"] - safe["right"] - next_field["width_mm"]), 1)
    next_field["y_mm"] = round(_clamp(_safe_float(next_field.get("y_mm"), 0.0), safe["top"], size["height"] - safe["bottom"] - next_field["height_mm"]), 1)
    return next_field


def suggest_layout(
    text_fields: dict[str, Any] | list[dict[str, Any]],
    model: dict[str, Any] | None,
    learned_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Suggest a balanced layout from text fields and optional learned rules."""

    learned_rules = learned_rules or {}
    if isinstance(text_fields, list):
        fields = deepcopy(text_fields)
        values = {str(field.get("excel_column") or field.get("column") or ""): str(field.get("text") or field.get("value") or "") for field in fields}
    else:
        fields = deepcopy(text_fields.get("fields") or [])
        values = deepcopy(text_fields.get("values") or text_fields)

    size = _label_size(model)
    before_score = calculate_layout_quality(fields, model, values)
    name_text = str(values.get("label_text") or values.get("nameText") or values.get("name") or "").strip()
    date_text = str(values.get("date_text") or values.get("dateText") or values.get("date") or "").strip()
    note_text = str(values.get("note_text") or values.get("noteText") or values.get("note") or "").strip()

    text_length = len(name_text.replace(" ", ""))
    learned_name_font = _safe_float(learned_rules.get("nameFontSize"), 0.0)
    if learned_name_font:
        name_font = learned_name_font
    elif text_length <= 4:
        name_font = max(20.0, size["height"] * 0.82)
    elif text_length <= 16:
        name_font = max(17.0, size["height"] * 0.68)
    else:
        name_font = max(13.0, size["height"] * 0.52)

    date_ratio = _safe_float(learned_rules.get("dateFontRatio"), 0.55)
    note_ratio = _safe_float(learned_rules.get("noteFontRatio"), 0.46)
    date_font = max(10.0, name_font * date_ratio)
    note_font = max(10.0, name_font * note_ratio)

    active_columns = [column for column, text in (("label_text", name_text), ("date_text", date_text), ("note_text", note_text)) if text]
    if active_columns == ["label_text"]:
        y_map = {"label_text": size["height"] * 0.39}
    elif active_columns == ["label_text", "date_text"]:
        y_map = {"label_text": size["height"] * 0.34, "date_text": size["height"] * 0.59}
    elif active_columns == ["label_text", "note_text"]:
        y_map = {"label_text": size["height"] * 0.33, "note_text": size["height"] * 0.61}
    else:
        y_map = {"label_text": size["height"] * 0.31, "date_text": size["height"] * 0.56, "note_text": size["height"] * 0.72}

    target = {
        "label_text": {
            "x_mm": size["width"] * 0.08,
            "y_mm": y_map.get("label_text", size["height"] * 0.33),
            "width_mm": size["width"] * 0.84,
            "height_mm": size["height"] * (0.38 if active_columns == ["label_text"] else 0.34),
            "font_size": name_font,
            "align": "center",
        },
        "date_text": {
            "x_mm": size["width"] * 0.26,
            "y_mm": y_map.get("date_text", size["height"] * 0.58),
            "width_mm": size["width"] * 0.48,
            "height_mm": size["height"] * 0.17,
            "font_size": date_font,
            "align": "center",
        },
        "note_text": {
            "x_mm": size["width"] * 0.17,
            "y_mm": y_map.get("note_text", size["height"] * 0.72),
            "width_mm": size["width"] * 0.66,
            "height_mm": size["height"] * 0.17,
            "font_size": note_font,
            "align": "center",
        },
    }

    output_fields: list[dict[str, Any]] = []
    seen_columns: set[str] = set()
    for field in fields:
        column = _field_column(field)
        if column in seen_columns:
            continue
        seen_columns.add(column)
        next_field = deepcopy(field)
        if column in target:
            next_field.update(target[column])
            min_font = 12.0 if column == "label_text" else 9.0
            next_field = _fit_font_to_box(next_field, str(values.get(column) or ""), min_font=min_font)
            next_field = _clamp_field(next_field, model)
        output_fields.append(next_field)

    after_score = calculate_layout_quality(output_fields, model, values)
    summary: list[str] = []
    before_fonts = {_field_column(field): _safe_float(field.get("font_size"), 0.0) for field in fields}
    after_fonts = {_field_column(field): _safe_float(field.get("font_size"), 0.0) for field in output_fields}
    labels = {"label_text": "İsim", "date_text": "Tarih", "note_text": "Not"}
    for column in ("label_text", "date_text", "note_text"):
        if not str(values.get(column) or "").strip():
            continue
        before = before_fonts.get(column, 0.0)
        after = after_fonts.get(column, 0.0)
        if before and abs(before - after) >= 1:
            direction = "çıkarıldı" if after > before else "düşürüldü"
            summary.append(f"{labels[column]} fontu {before:g}'den {after:g}'e {direction}.")
    if after_score["layoutQualityScore"] > before_score["layoutQualityScore"]:
        summary.append(f"Kalite skoru %{before_score['layoutQualityScore']}'den %{after_score['layoutQualityScore']}'e yükseldi.")
    if text_length > 20:
        summary.append("Uzun isim için kontrollü font ve geniş alan önerildi.")

    return {
        "fields": output_fields,
        "qualityBefore": before_score,
        "qualityAfter": after_score,
        "summary": summary or ["Yerleşim kalite kontrolünden geçirildi."],
        "warnings": after_score.get("warnings", []),
    }


def update_learned_rules(project_root: Path | str | None, model_id: str) -> dict[str, Any]:
    store = _load_store(project_root)
    profile = store.setdefault("profiles", {}).get(model_id)
    if not profile:
        return {}
    layouts = [layout for layout in profile.get("approvedLayouts", []) if _safe_int(layout.get("layoutQualityScore"), 0) >= 78]
    if not layouts:
        profile["learnedRules"] = profile.get("learnedRules") or {}
        return deepcopy(profile["learnedRules"])

    name_fonts = [_safe_float(layout.get("nameFontSize"), 0.0) for layout in layouts if _safe_float(layout.get("nameFontSize"), 0.0)]
    date_ratios = []
    note_ratios = []
    for layout in layouts:
        name = _safe_float(layout.get("nameFontSize"), 0.0)
        if name and _safe_float(layout.get("dateFontSize"), 0.0):
            date_ratios.append(_safe_float(layout.get("dateFontSize")) / name)
        if name and _safe_float(layout.get("noteFontSize"), 0.0):
            note_ratios.append(_safe_float(layout.get("noteFontSize")) / name)
    rules = {
        "nameFontSize": round(mean(name_fonts), 1) if name_fonts else None,
        "dateFontRatio": round(mean(date_ratios), 2) if date_ratios else 0.55,
        "noteFontRatio": round(mean(note_ratios), 2) if note_ratios else 0.46,
        "approvedExampleCount": len(layouts),
        "updatedAt": _now_iso(),
    }
    profile["learnedRules"] = rules
    profile["lastUpdated"] = _now_iso()
    _save_store(store, project_root)
    return deepcopy(rules)


def record_user_adjustment(
    project_root: Path | str | None,
    model_id: str,
    before_layout: dict[str, Any],
    after_layout: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _load_store(project_root)
    profile = store.setdefault("profiles", {}).setdefault(model_id, get_learning_profile(project_root, model_id))
    entry = {
        "beforeLayout": before_layout,
        "afterLayout": after_layout,
        "changedFields": (context or {}).get("changedFields") or [],
        "reason": (context or {}).get("reason"),
        "userAction": (context or {}).get("userAction") or "manual_adjustment",
        "savedAsSuccessful": bool((context or {}).get("savedAsSuccessful")),
        "createdAt": _now_iso(),
    }
    profile.setdefault("userAdjustments", []).append(entry)
    profile["userAdjustments"] = profile["userAdjustments"][-MAX_USER_ADJUSTMENTS:]
    profile["lastUpdated"] = _now_iso()
    _save_store(store, project_root)
    return deepcopy(entry)


def _layout_success_entry(layout: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    fields = layout.get("fields") or layout.get("_fields") or []
    values = layout.get("values") or {}
    by_column = {_field_column(field): _numeric_field(field) for field in fields}
    quality = context.get("quality") or layout.get("quality") or {}
    if not quality:
        quality = {"layoutQualityScore": context.get("layoutQualityScore", 0)}
    return {
        "sourceType": context.get("sourceType") or "manual",
        "nameText": values.get("label_text") or context.get("nameText") or "",
        "nameLength": len(str(values.get("label_text") or context.get("nameText") or "")),
        "dateText": values.get("date_text") or context.get("dateText") or "",
        "noteText": values.get("note_text") or context.get("noteText") or "",
        "laserNameText": values.get("name_cut_text") or context.get("laserNameText") or "",
        "nameFont": by_column.get("label_text", {}).get("font_family") or context.get("nameFont"),
        "nameFontSize": by_column.get("label_text", {}).get("font_size"),
        "dateFontSize": by_column.get("date_text", {}).get("font_size"),
        "noteFontSize": by_column.get("note_text", {}).get("font_size"),
        "laserFontSize": by_column.get("name_cut_text", {}).get("font_size"),
        "nameX": by_column.get("label_text", {}).get("x_mm"),
        "nameY": by_column.get("label_text", {}).get("y_mm"),
        "dateX": by_column.get("date_text", {}).get("x_mm"),
        "dateY": by_column.get("date_text", {}).get("y_mm"),
        "noteX": by_column.get("note_text", {}).get("x_mm"),
        "noteY": by_column.get("note_text", {}).get("y_mm"),
        "laserX": by_column.get("name_cut_text", {}).get("x_mm"),
        "laserY": by_column.get("name_cut_text", {}).get("y_mm"),
        "textGroupBounds": _group_bounds(list(by_column.values())),
        "safeAreaStatus": context.get("safeAreaStatus") or "ok",
        "overflowStatus": context.get("overflowStatus") or "ok",
        "readabilityScore": quality.get("readabilityScore"),
        "whitespaceScore": quality.get("whitespaceScore"),
        "visualBalanceScore": quality.get("balanceScore"),
        "layoutQualityScore": quality.get("layoutQualityScore"),
        "userApproved": bool(context.get("userApproved", True)),
        "sentToProduction": bool(context.get("sentToProduction", True)),
        "createdAt": _now_iso(),
    }


def record_production_success(
    project_root: Path | str | None,
    model_id: str,
    layout: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _load_store(project_root)
    profile = store.setdefault("profiles", {}).setdefault(model_id, get_learning_profile(project_root, model_id))
    entry = _layout_success_entry(layout, context)
    profile.setdefault("approvedLayouts", []).append(entry)
    profile["approvedLayouts"] = profile["approvedLayouts"][-MAX_APPROVED_LAYOUTS:]
    profile["lastUpdated"] = _now_iso()
    _save_store(store, project_root)
    update_learned_rules(project_root, model_id)
    return deepcopy(entry)
