from pathlib import Path

from src.intelligence.layout_learning_engine import (
    calculate_layout_quality,
    get_learning_profile,
    record_production_success,
    record_user_adjustment,
    suggest_layout,
    update_learned_rules,
)


def model():
    return {
        "modelId": "01-a-gold",
        "modelName": "01 A Gold Rulo Etiket",
        "labelWidthMm": 50,
        "labelHeightMm": 30,
        "safeArea": {"left": 2, "top": 2, "right": 2, "bottom": 2},
        "laserWidthMm": 38,
        "laserHeightMm": 9,
    }


def bad_fields():
    return [
        {"excel_column": "label_text", "x_mm": 8, "y_mm": 11, "width_mm": 32, "height_mm": 5, "font_size": 18, "align": "center"},
        {"excel_column": "date_text", "x_mm": 18, "y_mm": 19, "width_mm": 14, "height_mm": 3, "font_size": 8, "align": "center"},
        {"excel_column": "note_text", "x_mm": 18, "y_mm": 23, "width_mm": 14, "height_mm": 3, "font_size": 9, "align": "center"},
    ]


def test_smart_layout_improves_small_visual_layout():
    values = {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "Söz Hatırası"}
    before = calculate_layout_quality(bad_fields(), model(), values)
    suggestion = suggest_layout({"fields": bad_fields(), "values": values}, model())
    after = suggestion["qualityAfter"]

    assert after["layoutQualityScore"] > before["layoutQualityScore"]
    assert after["readabilityScore"] >= before["readabilityScore"]
    assert after["safeAreaScore"] == 100
    assert any("Kalite skoru" in item for item in suggestion["summary"])


def test_short_name_gets_larger_and_centered():
    values = {"label_text": "EFE", "date_text": "", "note_text": ""}
    suggestion = suggest_layout({"fields": bad_fields(), "values": values}, model())
    name_field = next(field for field in suggestion["fields"] if field["excel_column"] == "label_text")

    assert float(name_field["font_size"]) >= 20
    assert 2 <= float(name_field["x_mm"]) <= 8
    assert suggestion["qualityAfter"]["whitespaceScore"] >= 70


def test_long_name_stays_inside_safe_area_with_controlled_font():
    values = {"label_text": "YAĞMUR & MUSTAFA KEMAL", "date_text": "", "note_text": ""}
    suggestion = suggest_layout({"fields": bad_fields(), "values": values}, model())
    name_field = next(field for field in suggestion["fields"] if field["excel_column"] == "label_text")

    assert float(name_field["font_size"]) >= 12
    assert suggestion["qualityAfter"]["safeAreaScore"] == 100
    assert suggestion["qualityAfter"]["overflowScore"] >= 80


def test_missing_date_rebalances_without_date_gap():
    values = {"label_text": "Ayşe & Mehmet", "date_text": "", "note_text": "Söz Hatırası"}
    suggestion = suggest_layout({"fields": bad_fields(), "values": values}, model())
    name_field = next(field for field in suggestion["fields"] if field["excel_column"] == "label_text")
    note_field = next(field for field in suggestion["fields"] if field["excel_column"] == "note_text")

    assert float(name_field["y_mm"]) < float(note_field["y_mm"])
    assert float(note_field["y_mm"]) < 22


def test_user_adjustment_and_production_success_are_learned(tmp_path: Path):
    values = {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "Söz Hatırası"}
    suggestion = suggest_layout({"fields": bad_fields(), "values": values}, model())
    before = {"fields": bad_fields(), "values": values}
    after = {"fields": suggestion["fields"], "values": values}

    adjustment = record_user_adjustment(
        tmp_path,
        "01-a-gold",
        before,
        after,
        {"userAction": "font_increased", "changedFields": ["label_text"]},
    )
    assert adjustment["userAction"] == "font_increased"

    entry = record_production_success(
        tmp_path,
        "01-a-gold",
        {**after, "quality": suggestion["qualityAfter"]},
        {"sourceType": "manual", "sentToProduction": True},
    )
    assert entry["sourceType"] == "manual"

    rules = update_learned_rules(tmp_path, "01-a-gold")
    assert rules["approvedExampleCount"] == 1
    assert rules["nameFontSize"] is not None
    profile = get_learning_profile(tmp_path, "01-a-gold")
    assert len(profile["approvedLayouts"]) == 1
    assert len(profile["userAdjustments"]) == 1


def test_long_laser_name_warns_about_cutting_fit():
    fields = bad_fields() + [
        {"excel_column": "name_cut_text", "x_mm": 2, "y_mm": 2, "width_mm": 38, "height_mm": 8, "font_size": 16, "align": "center"}
    ]
    values = {
        "label_text": "Ayşe & Mehmet",
        "date_text": "",
        "note_text": "",
        "name_cut_text": "YAĞMUR & MUSTAFA KEMAL",
    }
    quality = calculate_layout_quality(fields, model(), values)

    assert quality["laserFitScore"] < 80
    assert any("Laser name" in warning for warning in quality["warnings"])

