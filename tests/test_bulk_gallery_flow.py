from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend import bulk_label_api  # noqa: E402


def test_bulk_gallery_handles_hundred_customer_rows(tmp_path: Path) -> None:
    excel = tmp_path / "bulk_100.xlsx"
    rows = []
    for index in range(1, 101):
        rows.append(
            {
                "etiket_no": "99" if index in {25, 75} else "03" if index % 3 == 0 else "01",
                "isim": f"Musteri {index:03d} & Test",
                "tarih": f"{(index % 28) + 1:02d}.06.2026",
                "not": "Hatira",
                "adet": (index % 5) + 1,
            }
        )
    pd.DataFrame(rows).to_excel(excel, index=False)

    items = bulk_label_api.bulk_gallery_items(tmp_path, excel, _models())
    summary = bulk_label_api.bulk_gallery_summary(items)

    assert len(items) == 100
    assert summary["total_rows"] == 100
    assert summary["error_rows"] == 2
    assert summary["ready_rows"] == 98
    assert summary["total_quantity"] == 298


def _models() -> list[dict[str, object]]:
    return [
        {
            "model_no": "01",
            "template_no": "A",
            "label_variant": "GOLD",
            "title": "01 A Gold Rulo Etiket",
            "path": "templates/designs/01_a_gold.json",
            "preview_image": "file:///tmp/01.png",
            "label_width_mm": "50",
            "label_height_mm": "30",
            "size_text": "50x30 mm",
            "fields_summary": [{"role": "label_text"}, {"role": "date_text"}, {"role": "note_text"}],
        },
        {
            "model_no": "03",
            "template_no": "A",
            "label_variant": "GOLD",
            "title": "03 A Gold",
            "path": "templates/designs/03_a_gold.json",
            "preview_image": "file:///tmp/03.png",
            "label_width_mm": "40",
            "label_height_mm": "40",
            "size_text": "40x40 mm",
            "fields_summary": [{"role": "label_text"}, {"role": "date_text"}, {"role": "note_text"}],
        },
    ]


def _excel(path: Path) -> None:
    pd.DataFrame(
        [
            {"etiket_no": "01", "isim": "Ayşe & Mehmet", "tarih": "15.05.2026", "not": "Nişan Hatırası", "adet": 10},
            {"model numarası": "03", "ad soyad": "Burcu & Baran", "date": "20.06.2026", "açıklama": "Söz Hatırası", "qty": 5},
            {"tasarım_no": "99", "müşteri_adı": "Hatalı Model", "etkinlik_tarihi": "01.01.2026", "mesaj": "Test", "miktar": 1},
        ]
    ).to_excel(path, index=False)


def test_bulk_gallery_items_map_turkish_excel_columns_and_models(tmp_path: Path) -> None:
    excel = tmp_path / "bulk.xlsx"
    _excel(excel)

    items = bulk_label_api.bulk_gallery_items(tmp_path, excel, _models())

    assert len(items) == 3
    assert items[0]["model_name"] == "01 A Gold Rulo Etiket"
    assert items[0]["label_text"] == "Ayşe & Mehmet"
    assert items[0]["date_text"] == "15.05.2026"
    assert items[0]["note_text"] == "Nişan Hatırası"
    assert items[0]["quantity"] == "10"
    assert items[1]["model_name"] == "03 A Gold"
    assert items[1]["quantity"] == "5"
    assert items[2]["status"] == "ERROR"
    assert "model bulunamadı" in items[2]["errors"][0]


def test_bulk_gallery_manifest_excludes_deleted_and_error_rows(tmp_path: Path) -> None:
    excel = tmp_path / "bulk.xlsx"
    _excel(excel)
    items = bulk_label_api.bulk_gallery_items(tmp_path, excel, _models())
    items[1]["is_deleted"] = True
    items[1]["is_edited"] = True

    result = bulk_label_api.write_gallery_items_excel(tmp_path, excel, items)

    assert result["status"] == "OK"
    output_excel = tmp_path / str(result["relative_path"])
    manifest = tmp_path / str(result["manifest_path"])
    assert output_excel.exists()
    assert manifest.exists()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["total_rows"] == 3
    assert manifest_data["deleted_rows"] == 1
    assert manifest_data["error_rows"] == 1
    assert manifest_data["ready_rows"] == 1
    rendered_rows = pd.read_excel(output_excel, dtype=object)
    assert len(rendered_rows) == 1
    assert rendered_rows.iloc[0]["label_text"] == "Ayşe & Mehmet"
