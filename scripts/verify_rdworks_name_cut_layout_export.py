from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import combined_production_api, template_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "rdworks_name_cut_ready"
RESULT_PATH = OUTPUT_DIR / "VERIFY_RDWORKS_NAME_CUT_LAYOUT_EXPORT_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 90000):
    loop = QEventLoop()
    result = {"value": None, "done": False}

    def callback(value):
        result["value"] = value
        result["done"] = True
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:180]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def ensure_excel() -> Path:
    path = PROJECT_ROOT / "examples" / "rdworks_isim_kesim_ornek.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
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
            "kalinlastirma": "Orta",
            "alt_destek": "hayır",
            "taban_plaka": "hayır",
        },
        {
            "musteri_adi": "sedef sefer",
            "tarih": "20.06.2026",
            "not": "Söz Hatırası",
            "adet": 1,
            "etiket_cikar": "hayır",
            "etiket_no": "",
            "isim_kes": "evet",
            "isim_kesim_adet": 1,
            "isim_genislik_mm": 260,
            "kompozisyon": "Alt Alta Romantik",
            "isim_stil": "Söz/Nişan Script",
            "kalinlastirma": "Kalın",
            "alt_destek": "evet",
            "taban_plaka": "hayır",
        },
        {
            "musteri_adi": "elif kaan",
            "tarih": "01.07.2026",
            "not": "",
            "adet": 1,
            "etiket_cikar": "hayır",
            "isim_kes": "evet",
            "isim_kesim_adet": 1,
            "isim_yukseklik_mm": 70,
            "isim_stil": "Kalın Bitişik Kesim",
            "kalinlastirma": "Özel offset",
            "offset_mm": 1.6,
            "alt_destek": "evet",
            "taban_plaka": "evet",
        },
    ]
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def fifty_name_items(count: int = 50) -> list[dict[str, object]]:
    raw_names = [
        "ayse omer", "sedef sefer", "elif kaan", "cagla cagri", "irem tugce",
        "deniz emre", "seda alper", "zeynep burak", "fatma ahmet", "dilara oguz",
    ]
    styles = ["Bitişik Romantik Script", "Söz/Nişan Script", "Kalın Bitişik Kesim", "Pleksi Güvenli Script"]
    compositions = ["Tek Satır Yan Yana", "Alt Alta Romantik", "Büyük İsim + Küçük İsim", "Çift İsim Dengeli"]
    modes = ["Hafif", "Orta", "Kalın", "Özel offset"]
    items: list[dict[str, object]] = []
    for index in range(count):
        mode = modes[index % len(modes)]
        offset = 1.6 if mode == "Özel offset" else combined_production_api.resolve_offset_mm(mode)
        text = combined_production_api.format_name_for_cutting(raw_names[index % len(raw_names)])
        width, height = combined_production_api.resolve_name_cut_dimensions(
            text,
            160 + (index % 6) * 22,
            None,
            max_width_mm=330,
            max_height_mm=90,
            composition=compositions[index % len(compositions)],
        )
        items.append(
            {
                "item_id": f"rdworks-name-{index}",
                "row_number": str(index + 2),
                "raw_customer_name": raw_names[index % len(raw_names)],
                "name_text": text,
                "preview_text": text.replace(" ", "\n") if "Alt Alta" in compositions[index % len(compositions)] else text.replace(" ", "   "),
                "quantity": "1",
                "width_mm": width,
                "height_mm": height,
                "style": styles[index % len(styles)],
                "composition": compositions[index % len(compositions)],
                "composition_mode": compositions[index % len(compositions)],
                "thickening_mode": mode,
                "offset_mm": offset,
                "support_line": index % 3 == 0,
                "back_plate": index % 8 == 0,
                "status": "READY",
                "warnings": [],
                "errors": [],
                "is_deleted": False,
                "is_edited": False,
            }
        )
    return items


def backend_gate() -> dict[str, object]:
    excel = ensure_excel()
    models = template_api.list_label_model_gallery(PROJECT_ROOT)
    state = combined_production_api.combined_production_state(PROJECT_ROOT, excel, models)
    assert_true(state["status"] == "OK", "Birleşik üretim state oluşmadı", state)
    assert_true(state["name_cut_items"][0]["name_text"] == "Ayşe Ömer", "Türkçe isim formatlama çalışmadı", state["name_cut_items"][0])
    assert_true(state["name_cut_items"][1]["preview_text"] == "Sedef\nSefer", "Alt alta kompozisyon oluşmadı", state["name_cut_items"][1])
    assert_true(float(state["name_cut_items"][2]["offset_mm"]) == 1.6, "Özel offset Excel'den alınmadı", state["name_cut_items"][2])

    layout = combined_production_api.layout_name_cut_items(fifty_name_items())
    assert_true(layout["summary"]["total_copies"] == 50, "50 isim yerleşimi eksik", layout["summary"])
    assert_true(layout["summary"]["pages"] >= 1, "Çalışma alanı/sayfa hesabı yok", layout["summary"])
    assert_true(layout["summary"]["used_area_percent"] > 0, "Kullanılan alan hesaplanmadı", layout["summary"])
    assert_true(layout["summary"]["placement_strategy"] == "FIRST_FIT_SHELF_HEIGHT_DESC", "Packing stratejisi manifestlenmedi", layout["summary"])
    assert_true(layout["summary"]["collision_free"] is True, "İsim yerleşiminde çakışma var", layout["summary"])
    assert_true(layout["summary"]["within_work_area"] is True, "İsim yerleşimi çalışma alanı dışına taşıyor", layout["summary"])
    layout_100 = combined_production_api.layout_name_cut_items(fifty_name_items(100))
    assert_true(layout_100["summary"]["total_copies"] == 100, "100 isim yerleşimi eksik", layout_100["summary"])
    assert_true(layout_100["summary"]["overflow"] is False, "100 isim yeni plate/sayfa yerine taşma oluşturdu", layout_100["summary"])
    assert_true(layout_100["summary"]["pages"] >= layout["summary"]["pages"], "100 isim plate/sayfa hesabı tutarsız", layout_100["summary"])
    assert_true(layout_100["summary"]["collision_free"] is True, "100 isim yerleşiminde çakışma var", layout_100["summary"])
    assert_true(layout_100["summary"]["within_work_area"] is True, "100 isim çalışma alanı dışına taşıyor", layout_100["summary"])

    export = combined_production_api.export_name_cut_batch(PROJECT_ROOT, excel, fifty_name_items(), {"mirror_cut": True, "row_gap_mm": 12})
    assert_true(export["status"] == "OK", "RDWorks export oluşmadı", export)
    for key in ["svg_path", "dxf_path", "pdf_preview", "png_preview", "manifest_path"]:
        assert_true((PROJECT_ROOT / str(export[key])).exists(), f"{key} oluşmadı", export)
    manifest = json.loads((PROJECT_ROOT / str(export["manifest_path"])).read_text(encoding="utf-8"))
    assert_true(manifest["primary_rdworks_export"] == manifest["exported_dxf"], "DXF birincil RDWorks export olarak isaretlenmedi", manifest)
    assert_true(manifest["export_priority"][0] == "DXF", "Export onceligi DXF degil", manifest)
    assert_true(manifest["placement_strategy"] == "FIRST_FIT_SHELF_HEIGHT_DESC", "Manifest packing stratejisini taşımıyor", manifest)
    assert_true(manifest["collision_free"] is True and manifest["within_work_area"] is True, "Manifest güvenli yerleşim durumunu taşımıyor", manifest)
    assert_true(manifest["layer_color_standard"]["CUT_NAME_OUTLINE"]["color"] == "red", "Ana kesim layer rengi kirmizi degil", manifest)
    assert_true(manifest["mirror_cut"] is True, "Ayna kesim modu manifest'e yansimadi", manifest)
    svg = (PROJECT_ROOT / str(export["svg_path"])).read_text(encoding="utf-8")
    dxf = (PROJECT_ROOT / str(export["dxf_path"])).read_text(encoding="utf-8")
    svg_name_y_values: list[float] = []
    for path_data in re.findall(r'<path d="([^"]+)"', svg):
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path_data)]
        svg_name_y_values.extend(numbers[index] for index in range(1, len(numbers), 2))

    assert_true(manifest["total_names"] == 50, "Manifest toplam isim yanlış", manifest)
    assert_true(manifest["text_to_path_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS", "Text-to-path outline durumu beklenen seviyede değil", manifest)
    assert_true(manifest["thickening_status"] == "TRUE_POLYGON_OFFSET_WITH_PYCLIPPER", "Gerçek polygon offset motoru raporlanmadı", manifest)
    assert_true(
        any(item.get("diacritic_bridge_status") == "AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE" for item in manifest["items"]),
        "Türkçe nokta/isaret köprüleri manifest ve export hattına yansımadı",
        manifest["items"][:5],
    )
    assert_true(any(float(item["offset_mm"]) >= 1.2 for item in manifest["items"]), "Manifest offset değerlerini taşımıyor", manifest["items"][:3])
    assert_true('id="CUT_NAME_OUTLINE"' in svg and 'data-outline="fonttools-path"' in svg and "data-offset-mm" in svg, "SVG kesim path/offset taşımıyor", svg[:400])
    assert_true(manifest["manual_control_required"] is True, "RDWorks manuel kontrol zorunlulugu manifestte yok", manifest)
    assert_true(manifest["machine_automation"]["rdworks_auto_open"] is False, "RDWorks otomatik acma guvenlik siniri bozuldu", manifest)
    assert_true(manifest["machine_automation"]["laser_auto_start"] is False, "Lazer otomatik baslatma guvenlik siniri bozuldu", manifest)
    assert_true(manifest["machine_automation"]["speed_power_exported"] is False, "Makine speed/power ayari export edilmemeli", manifest)
    assert_true(all(item["rdworks_layer"] == "CUT_NAME_OUTLINE" for item in manifest["items"]), "Item RDWorks layer bilgisi eksik", manifest["items"][:2])
    if manifest["pages"] > 1:
        assert_true(max(svg_name_y_values, default=0) > float(manifest["work_area_height_mm"]), "SVG çoklu plate isim path'leri plate offset taşımıyor", svg[:800])
    assert_true("CUT_SUPPORT_LINE" in svg and "CUT_BACK_PLATE" in svg, "SVG destek/plaka layer taşımıyor", svg[:400])
    assert_true("CUT_NAME_OUTLINE" in dxf and "POLYLINE" in dxf and "THICKENING" in dxf and "OFFSET_ENGINE TRUE_POLYGON_OFFSET_WITH_PYCLIPPER" in dxf, "DXF outline layer/kalınlaştırma/offset motoru notu taşımıyor", dxf[:400])

    for token in ["CUT_SUPPORT_LINE", "CUT_BACK_PLATE", "GUIDE_PREVIEW", "CALIBRATION", "62\n1", "62\n5", "62\n6", "MIRROR_CUT True", "TEXT_TO_PATH OUTLINED_PATHS_WITH_FONTTOOLS"]:
        assert_true(token in dxf, f"DXF RDWorks layer/color standard eksik: {token}", dxf[:800])

    state["name_cut_items"] = fifty_name_items()
    state["layout"] = layout
    return {"sample_excel": str(excel.relative_to(PROJECT_ROOT)), "state": state, "export": export, "manifest": manifest}


def ui_gate(backend: dict[str, object]) -> dict[str, str]:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.selected_excel = PROJECT_ROOT / str(backend["sample_excel"])
    window.resize(1680, 980)
    window.show()
    wait(6000)
    screenshots: dict[str, str] = {}
    state_json = json.dumps(backend["state"], ensure_ascii=False)
    try:
        run_js(window, f"""
        (() => {{
          showSection('bulkLabel');
          updateCombinedProduction({state_json});
          return true;
        }})()
        """)
        wait(1000)
        first = run_js(window, """
        (() => ({
          page: document.querySelector('.page.active')?.id || '',
          cards: document.querySelectorAll('#nameCutGalleryGrid .name-cut-card').length,
          text: document.getElementById('bulkLabel')?.innerText || '',
          hasLayout: Boolean(document.querySelector('#nameCutLayoutPreview .laser-layout-stage'))
        }))()
        """)
        assert_true(first["page"] == "bulkLabel", "Toplu Etiket sayfası açılmadı", first)
        assert_true(first["cards"] >= 50, "50 isim galeride görünmüyor", first)
        assert_true(first["hasLayout"], "Lazer yerleşim önizlemesi yok", first)
        assert_true("Manuel İsim Ekle" in first["text"], "Manuel isim ekleme aksiyonu yok", first)
        screenshots["name_cut_main"] = save_screenshot(window, "name_cut_main.png")

        run_js(window, "(() => { showSection('nameCutStudio'); return true; })()")
        wait(900)
        studio = run_js(window, """
        (() => ({
          page: document.querySelector('.page.active')?.id || '',
          cards: document.querySelectorAll('#nameCutStudioGalleryGrid .name-cut-card').length,
          text: document.getElementById('nameCutStudio')?.innerText || '',
          hasLayout: Boolean(document.querySelector('#nameCutStudioLayoutPreview .laser-layout-stage')),
          hasExport: Boolean(document.getElementById('nameCutStudioExportPanel')?.innerText.includes('DXF'))
        }))()
        """)
        assert_true(studio["page"] == "nameCutStudio", "Isim Kesim Studio sayfasi acilmadi", studio)
        assert_true(studio["cards"] >= 50, "Isim Kesim Studio galerisi 50 ismi gostermiyor", studio)
        assert_true(studio["hasLayout"], "Isim Kesim Studio RDWorks yerlesim onizlemesi yok", studio)
        assert_true(studio["hasExport"], "Isim Kesim Studio DXF export panelini gostermiyor", studio)
        assert_true("RDWorks" in studio["text"] and "lazer" in studio["text"].lower(), "Guvenli RDWorks manuel kontrol mesaji yok", studio)
        screenshots["name_cut_studio"] = save_screenshot(window, "name_cut_studio.png")

        run_js(window, "(() => { openManualNameCutModal(); return true; })()")
        wait(700)
        modal = run_js(window, """
        (() => ({
          open: !document.getElementById('nameCutEditModal')?.hidden,
          text: document.getElementById('nameCutEditModal')?.innerText || '',
          style: document.getElementById('nameCutEditStyle')?.value || '',
          composition: document.getElementById('nameCutEditComposition')?.value || ''
        }))()
        """)
        assert_true(modal["open"], "Manuel isim modalı açılmadı", modal)
        assert_true("Kesim Kalınlığı" in modal["text"] and "Kompozisyon" in modal["text"], "Modal kalınlaştırma/kompozisyon ayarlarını göstermiyor", modal)
        assert_true("Mochary" in modal["style"], "Manuel isim varsayılan fontu Mochary değil", modal)
        assert_true("Bitiştir" in modal["composition"], "Manuel isim varsayılan kompozisyonu isimleri bitiştir değil", modal)
        screenshots["manual_name_modal"] = save_screenshot(window, "manual_name_modal.png")

        run_js(window, """
        (() => {
          document.getElementById('nameCutEditName').value = 'ali ayse fatma leyla mucahit';
          document.getElementById('nameCutEditName').dispatchEvent(new Event('input', { bubbles: true }));
          document.getElementById('nameCutEditThickening').value = 'Kalın';
          document.getElementById('nameCutEditThickening').dispatchEvent(new Event('change', { bubbles: true }));
          document.getElementById('nameCutEditSupport').checked = true;
          document.getElementById('nameCutEditSupport').dispatchEvent(new Event('change', { bubbles: true }));
          saveNameCutDraft();
          return document.getElementById('nameCutGalleryGrid')?.innerText || '';
        })()
        """)
        wait(900)
        saved = run_js(window, "(() => ({ text: document.getElementById('nameCutGalleryGrid')?.innerText || '' }))()")
        assert_true("Ali Ayşe Fatma Leyla Mücahit" in saved["text"], "Çoklu manuel isim formatlanıp galeriye eklenmedi", saved)
        screenshots["manual_name_saved"] = save_screenshot(window, "manual_name_saved.png")

        run_js(window, "(() => { document.getElementById('nameCutLayoutPreview')?.scrollIntoView({ block: 'center' }); return true; })()")
        wait(700)
        screenshots["laser_layout_preview"] = save_screenshot(window, "laser_layout_preview.png")
        run_js(window, "(() => { document.getElementById('nameCutExportPanel')?.scrollIntoView({ block: 'center' }); return true; })()")
        wait(700)
        screenshots["rdworks_export_panel"] = save_screenshot(window, "rdworks_export_panel.png")
    finally:
        window.close()
        app.quit()
    return screenshots


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    backend = backend_gate()
    screenshots = ui_gate(backend)
    result = {
        "status": "PASSED",
        "sample_excel": backend["sample_excel"],
        "export": backend["export"],
        "manifest_text_to_path_status": backend["manifest"]["text_to_path_status"],
        "manifest_thickening_status": backend["manifest"]["thickening_status"],
        "screenshots": screenshots,
        "safety": {
            "rdworks_auto_opened": False,
            "laser_started": False,
            "direct_print_enabled": False,
            "printer_started": False,
        },
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
