from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import combined_production_api  # noqa: E402


def _models() -> list[dict[str, object]]:
    return [
        {
            "model_no": "01",
            "title": "01 A Gold Rulo Etiket",
            "path": "templates/designs/01_a_gold.json",
            "preview_image": "file:///tmp/01.png",
            "label_width_mm": "50",
            "label_height_mm": "30",
            "size_text": "50 x 30 mm",
        },
        {
            "model_no": "03",
            "title": "03 Yeşil Geometrik",
            "path": "templates/designs/03_yesil.json",
            "preview_image": "file:///tmp/03.png",
            "label_width_mm": "40",
            "label_height_mm": "40",
            "size_text": "40 x 40 mm",
        },
    ]


def _excel(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "musteri_adi": "ayse omer",
                "tarih": "15.05.2026",
                "not": "Nişan Hatırası",
                "adet": 10,
                "etiket_cikar": "evet",
                "etiket_no": "01",
                "isim_kes": "evet",
                "isim_kesim_adet": 1,
                "isim_genislik_mm": 300,
                "isim_stil": "Bitişik Romantik Script",
                "alt_destek": "hayır",
                "taban_plaka": "hayır",
            },
            {
                "musteri_adi": "burcu baran",
                "tarih": "20.06.2026",
                "not": "Söz Hatırası",
                "adet": 5,
                "etiket_cikar": "evet",
                "etiket_no": "03",
                "isim_kes": "hayır",
            },
            {
                "musteri_adi": "elif kaan",
                "tarih": "01.07.2026",
                "not": "",
                "adet": 1,
                "etiket_cikar": "hayır",
                "isim_kes": "evet",
                "isim_kesim_adet": 1,
                "isim_genislik_mm": 250,
                "isim_stil": "Kalın Bitişik Kesim",
                "alt_destek": "evet",
            },
            {
                "musteri_adi": "üretim yok",
                "tarih": "01.01.2026",
                "adet": 1,
                "etiket_cikar": "hayır",
                "isim_kes": "hayır",
            },
        ]
    ).to_excel(path, index=False)


def test_combined_excel_splits_label_and_name_cut_jobs(tmp_path: Path) -> None:
    excel = tmp_path / "combined.xlsx"
    _excel(excel)

    state = combined_production_api.combined_production_state(tmp_path, excel, _models())

    assert state["status"] == "OK"
    assert state["summary"]["total_rows"] == 4
    assert state["summary"]["label_jobs"] == 2
    assert state["summary"]["name_cut_jobs"] == 2
    assert state["summary"]["both_jobs"] == 1
    assert state["summary"]["no_production"] == 1
    assert len(state["label_items"]) == 2
    assert len(state["name_cut_items"]) == 2
    assert state["name_cut_items"][0]["name_text"] == "Ayşe Ömer"
    assert state["name_cut_items"][1]["support_line"] is True
    assert any("üretim" in warning.lower() for warning in state["orders"][3]["warnings"])


def test_name_cut_layout_and_export_are_safe_files_only(tmp_path: Path) -> None:
    items = []
    for index in range(50):
        items.append(
            {
                "item_id": f"name-{index}",
                "row_number": str(index + 2),
                "name_text": f"Ayşe Ömer {index}",
                "quantity": "1",
                "width_mm": 160 + (index % 5) * 18,
                "height_mm": 50 + (index % 3) * 5,
                "style": "Söz/Nişan Script",
                "composition": "Tek Satır Yan Yana",
                "composition_mode": "Tek Satır Yan Yana",
                "thickening_mode": "Orta" if index % 3 else "Kalın",
                "offset_mm": 0.8 if index % 3 else 1.2,
                "support_line": index % 2 == 0,
                "back_plate": index % 7 == 0,
                "status": "READY",
                "warnings": [],
                "errors": [],
                "is_deleted": False,
                "is_edited": False,
            }
        )

    layout = combined_production_api.layout_name_cut_items(items)
    assert layout["summary"]["total_names"] == 50
    assert layout["summary"]["total_copies"] == 50
    assert layout["summary"]["pages"] >= 1
    assert layout["summary"]["overflow"] is False
    assert layout["summary"]["placement_strategy"] == "ACTUAL_PATH_DENSE_SHELF"
    assert layout["summary"]["dense_nesting"] is True
    assert layout["items"][0]["laser_name_object"]["widthMm"] == layout["items"][0]["width_mm"]
    assert layout["items"][0]["laser_name_object"]["readyForCut"] is True
    assert layout["summary"]["collision_free"] is True
    assert layout["summary"]["within_work_area"] is True
    assert layout["summary"]["page_stats"]

    excel = tmp_path / "combined.xlsx"
    _excel(excel)
    result = combined_production_api.export_name_cut_batch(tmp_path, excel, items, {"mirror_cut": True, "row_gap_mm": 12})

    assert result["status"] == "OK"
    assert result["text_to_outline_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS"
    for key in ["svg_path", "dxf_path", "pdf_preview", "png_preview", "manifest_path"]:
        assert (tmp_path / result[key]).exists(), key
    manifest = json.loads((tmp_path / result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["total_items"] == 50
    assert manifest["total_names"] == 50
    assert manifest["work_area_width_mm"] == 800.0
    assert manifest["work_area_height_mm"] == 600.0
    assert manifest["mirror_cut"] is True
    assert manifest["used_area_percent"] > 0
    assert manifest["primary_rdworks_export"] == manifest["exported_dxf"]
    assert manifest["export_priority"][0] == "DXF"
    assert manifest["manual_control_required"] is True
    assert manifest["machine_automation"]["rdworks_auto_open"] is False
    assert manifest["machine_automation"]["laser_auto_start"] is False
    assert manifest["machine_automation"]["direct_print"] is False
    assert manifest["machine_automation"]["speed_power_exported"] is False
    assert "CUT_NAME_OUTLINE" in manifest["rdworks_layer_contract"]
    assert manifest["placement_strategy"] == "ACTUAL_PATH_DENSE_SHELF"
    assert manifest["actual_path_layout"] is True
    assert manifest["collision_free"] is True
    assert manifest["within_work_area"] is True
    assert manifest["page_stats"]
    assert manifest["layer_color_standard"]["CUT_NAME_OUTLINE"]["color"] == "red"
    assert manifest["layer_color_standard"]["CUT_SUPPORT_LINE"]["color"] == "blue"
    assert manifest["layer_color_standard"]["CUT_BACK_PLATE"]["color"] == "purple"
    assert result["primary_export_path"] == result["dxf_path"]
    assert result["export_priority"][0] == "DXF"
    assert "RDWorks otomatik açılmaz" in manifest["rdworks_note"]
    assert manifest["text_to_outline_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS"
    assert manifest["text_to_path_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS"
    assert manifest["thickening_status"] == "TRUE_POLYGON_OFFSET_WITH_PYCLIPPER"
    assert any(item["thickening_mode"] == "Kalın" for item in manifest["items"])
    assert any(item["offset_mm"] == 1.2 for item in manifest["items"])
    assert all(item["rdworks_layer"] == "CUT_NAME_OUTLINE" for item in manifest["items"])
    assert all(item["text_to_path_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS" for item in manifest["items"])
    assert any(item["support_layer"] == "CUT_SUPPORT_LINE" for item in manifest["items"])
    assert any(item["back_plate_layer"] == "CUT_BACK_PLATE" for item in manifest["items"])
    svg = (tmp_path / result["svg_path"]).read_text(encoding="utf-8")
    dxf = (tmp_path / result["dxf_path"]).read_text(encoding="utf-8")
    assert 'id="CUT_NAME_OUTLINE"' in svg
    assert 'data-outline="fonttools-path"' in svg
    assert 'data-offset-mm="1.2"' in svg
    assert "CUT_SUPPORT_LINE" in svg
    assert "CUT_BACK_PLATE" in svg
    assert "CUT_NAME_OUTLINE" in dxf
    assert "POLYLINE" in dxf
    assert "TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS" in dxf
    assert "OFFSET_ENGINE TRUE_POLYGON_OFFSET_WITH_PYCLIPPER" in dxf
    assert "CUT_SUPPORT_LINE" in dxf
    assert "CUT_BACK_PLATE" in dxf
    assert "GUIDE_PREVIEW" not in dxf
    assert "CALIBRATION" not in dxf
    assert "GUIDE_PREVIEW" not in svg
    assert "CALIBRATION" not in svg
    assert "62\n1" in dxf
    assert "62\n5" in dxf
    assert "62\n6" in dxf
    assert "MIRROR_CUT True" in dxf
    assert "THICKENING Kalın OFFSET_MM 1.2" in dxf


def test_name_formatting_uses_turkish_corrections() -> None:
    assert combined_production_api.format_name_for_cutting("ayse omer") == "Ayşe Ömer"
    assert combined_production_api.format_name_for_cutting("cagla cagri") == "Çağla Çağrı"
    assert combined_production_api.format_name_for_cutting("SEDEF SEFER") == "Sedef Sefer"
    assert combined_production_api.format_name_for_cutting("ali ayse fatma leyla mucahit") == "Ali Ayşe Fatma Leyla Mücahit"
    assert combined_production_api.format_name_for_cutting("irem oguz ilker") == "İrem Oğuz İlker"
    # Turkish diacritic round-trip: already-correct Turkish chars must survive lowercasing.
    assert combined_production_api.format_name_for_cutting("İlknur") == "İlknur"
    assert combined_production_api.format_name_for_cutting("ilknur") == "İlknur"
    assert combined_production_api.format_name_for_cutting("ILKNUR") == "İlknur"
    assert combined_production_api.format_name_for_cutting("Şeyma") == "Şeyma"
    assert combined_production_api.format_name_for_cutting("ŞEYMA") == "Şeyma"
    assert combined_production_api.format_name_for_cutting("Çağla") == "Çağla"
    assert combined_production_api.format_name_for_cutting("ÇAĞLA") == "Çağla"
    assert combined_production_api.format_name_for_cutting("Oğuz") == "Oğuz"
    assert combined_production_api.format_name_for_cutting("OĞUZ") == "Oğuz"
    assert combined_production_api.format_name_for_cutting("Gül") == "Gül"
    assert combined_production_api.format_name_for_cutting("GÜL") == "Gül"
    assert combined_production_api.format_name_for_cutting("ŞÜKRÜ") == "Şükrü"
    # & separator preserved in paired names.
    assert combined_production_api.format_name_for_cutting("Ayşe & Mehmet") == "Ayşe & Mehmet"
    assert combined_production_api.format_name_for_cutting("ayse & mehmet") == "Ayşe & Mehmet"


def test_joined_names_mode_splits_space_separated_names_without_merging(tmp_path: Path) -> None:
    item = {
        "item_id": "manual-joined",
        "row_number": "1",
        "name_text": combined_production_api.format_name_for_cutting("ali ayse fatma leyla mucahit"),
        "quantity": "1",
        "width_mm": 300,
        "height_mm": 70,
        "style": "Mochary Personal Use Only",
        "composition": "İsimleri Bitiştir",
        "composition_mode": "İsimleri Bitiştir",
        "thickening_mode": "Orta",
        "offset_mm": 0.8,
        "support_line": False,
        "back_plate": False,
        "status": "READY",
        "warnings": [],
        "errors": [],
        "is_deleted": False,
        "is_edited": True,
    }
    layout = combined_production_api.layout_name_cut_items([item], combined_production_api.LayoutConfig(joined_name_gap_mm=2))
    names = [row["name_text"] for row in layout["items"]]
    assert names == ["Ali", "Ayşe", "Fatma", "Leyla", "Mücahit"]
    assert layout["summary"]["total_source_items"] == 1
    assert layout["summary"]["total_names"] == 5
    assert layout["summary"]["collision_free"] is True
    assert all(row["composition_mode"] == "İsimleri Bitiştir" for row in layout["items"])

    result = combined_production_api.export_name_cut_batch(tmp_path, tmp_path / "manual.xlsx", [item], {"joined_name_gap_mm": 2})
    manifest = json.loads((tmp_path / result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["total_source_items"] == 1
    assert manifest["total_names"] == 5
    assert manifest["joined_name_gap_mm"] == 2
    assert [row["formatted_name"] for row in manifest["items"]] == names
    assert all(row["source_name_text"] == "Ali Ayşe Fatma Leyla Mücahit" for row in manifest["items"])
    assert all(row["font_family"] == "Mochary Personal Use Only" for row in manifest["items"])
    assert all(
        "MOCHARY" in row["font_path_status"] or row["font_path_status"] == "FONT_FILE_AVAILABLE"
        for row in manifest["items"]
    )
    assert all(
        row["script_connection_status"] == "AUTO_CAPITAL_CONNECTION_TRACKING_FOR_MOCHARY_STYLE"
        for row in manifest["items"]
    )
    assert any(
        row["diacritic_bridge_status"] == "AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE"
        for row in manifest["items"]
    )
    dxf = (tmp_path / result["dxf_path"]).read_text(encoding="utf-8")
    assert dxf.count("CUT_NAME_OUTLINE") >= 5


def test_name_cut_dimensions_and_offset_rules() -> None:
    width_only = combined_production_api.resolve_name_cut_dimensions("Ayşe Ömer", 300, None)
    height_only = combined_production_api.resolve_name_cut_dimensions("Ayşe Ömer", None, 60)
    bounded = combined_production_api.resolve_name_cut_dimensions("Ayşe Ömer", 500, 120, max_width_mm=250, max_height_mm=80)

    assert width_only[0] == 300
    assert width_only[1] > 30
    assert height_only[1] == 60
    assert height_only[0] > 120
    assert bounded[0] <= 250
    assert bounded[1] <= 80
    assert combined_production_api.resolve_offset_mm("Hafif") == 0.4
    assert combined_production_api.resolve_offset_mm("Orta") == 0.8
    assert combined_production_api.resolve_offset_mm("Kalın") == 1.2
    assert combined_production_api.resolve_offset_mm("Özel offset", "2.4") == 2.4
