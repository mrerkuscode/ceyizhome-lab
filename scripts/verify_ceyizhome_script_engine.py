from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from webui_backend.combined_production_api import export_name_cut_batch  # noqa: E402


TEST_WORDS = [
    "Sedel",
    "Leyla",
    "Mücahit",
    "Ceyizhome",
    "Aşk ile söz verdik",
    "Söz & Nişan",
    "Ayşe & Mehmet",
    "Zeynep’in Nişanı",
    "Özel Tasarım",
    "₺250",
    "Şeyma",
    "Çağla",
    "Gülay",
    "İrem",
    "Burak",
    "Ceren",
    "Serkan",
]


def assert_true(condition: bool, message: str, details: object = None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def main() -> int:
    items = []
    for index, name in enumerate(TEST_WORDS, start=1):
        items.append(
            {
                "item_id": f"ceyizhome-script-{index}",
                "row_number": str(index),
                "raw_customer_name": name,
                "name_text": name,
                "preview_text": name,
                "quantity": "1",
                "width_mm": 150 if len(name) < 8 else 240,
                "height_mm": 38,
                "style": "Ceyizhome Lab Script (Mochary)",
                "composition": "Tek Satır Yan Yana",
                "composition_mode": "Tek Satır Yan Yana",
                "thickening_mode": "Özel offset",
                "offset_mm": 0.3,
                "support_line": False,
                "back_plate": False,
                "status": "READY",
                "warnings": [],
                "errors": [],
                "is_deleted": False,
            }
        )

    result = export_name_cut_batch(
        PROJECT_ROOT,
        PROJECT_ROOT / "examples" / "rdworks_isim_kesim_ornek.xlsx",
        items,
        {
            "width_mm": 800,
            "height_mm": 600,
            "margin_mm": 15,
            "item_gap_mm": 1.5,
            "row_gap_mm": 1.5,
            "start_corner": "top-right",
            "packing_direction": "right-to-left",
        },
    )
    assert_true(result["status"] == "OK", "Export basarisiz", result)
    manifest_path = PROJECT_ROOT / result["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert_true(manifest["text_to_path_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS", "Text path'e donusmedi", manifest["text_to_path_status"])
    assert_true(manifest["script_engine"]["name"] == "Ceyizhome Lab Script Engine", "Script engine manifestte yok", manifest.get("script_engine"))
    assert_true(all(item.get("keep_names_separate") for item in manifest["items"]), "Isimler ayri obje kalmadi", manifest["items"][:3])
    assert_true({item.get("weld_scope") for item in manifest["items"]} == {"INSIDE_EACH_NAME_ONLY"}, "Weld kapsam kurali bozuldu", manifest["items"][:3])

    by_name = {item["formatted_name"]: item for item in manifest["items"]}
    for name in ["Sedel", "Leyla", "Mücahit", "Ceren", "Serkan"]:
        assert_true(name in by_name, "Test ismi manifestte yok", name)
    assert_true(by_name["Sedel"]["capital_connection_bridge_status"] == "MANUAL_CAPITAL_BRIDGES_ADDED_INSIDE_NAME_ONLY", "Sedel S bridge almadı", by_name["Sedel"])
    assert_true(by_name["Leyla"]["capital_connection_bridge_status"] == "MANUAL_CAPITAL_BRIDGES_ADDED_INSIDE_NAME_ONLY", "Leyla L bridge almadı", by_name["Leyla"])
    assert_true(by_name["Mücahit"]["capital_connection_bridge_status"] == "MANUAL_CAPITAL_BRIDGES_ADDED_INSIDE_NAME_ONLY", "Mücahit M bridge almadı", by_name["Mücahit"])
    assert_true(by_name["₺250"]["text_to_path_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS", "₺ fallback path export'a girmedi", by_name["₺250"])

    dxf_text = (PROJECT_ROOT / result["dxf_path"]).read_text(encoding="utf-8", errors="ignore")
    svg_text = (PROJECT_ROOT / result["svg_path"]).read_text(encoding="utf-8", errors="ignore")
    assert_true("<path" in svg_text and "<text" not in svg_text, "SVG text yerine path icermeli", result["svg_path"])
    assert_true("POLYLINE" in dxf_text, "DXF polyline path icermeli", result["dxf_path"])

    summary = {
        "status": "PASSED",
        "manifest_path": result["manifest_path"],
        "svg_path": result["svg_path"],
        "dxf_path": result["dxf_path"],
        "pdf_preview": result["pdf_preview"],
        "png_preview": result["png_preview"],
        "manual_bridge_names": [
            item["formatted_name"]
            for item in manifest["items"]
            if item.get("capital_connection_bridge_status") == "MANUAL_CAPITAL_BRIDGES_ADDED_INSIDE_NAME_ONLY"
        ],
        "try_symbol_export": by_name["₺250"]["text_to_path_status"],
        "keep_names_separate": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
