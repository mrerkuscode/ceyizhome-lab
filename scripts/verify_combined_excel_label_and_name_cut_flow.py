from __future__ import annotations

import json
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


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "combined_production_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_COMBINED_EXCEL_LABEL_AND_NAME_CUT_FLOW_RESULT.json"


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


def ensure_sample_excel() -> Path:
    path = PROJECT_ROOT / "examples" / "etiket_ve_isim_kesim_ornek.xlsx"
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
            "isim_kesim_adet": 0,
            "isim_genislik_mm": "",
            "isim_stil": "",
            "alt_destek": "",
            "taban_plaka": "",
        },
        {
            "musteri_adi": "elif kaan",
            "tarih": "01.07.2026",
            "not": "",
            "adet": 1,
            "etiket_cikar": "hayır",
            "etiket_no": "",
            "isim_kes": "evet",
            "isim_kesim_adet": 1,
            "isim_genislik_mm": 250,
            "isim_stil": "Kalın Bitişik Kesim",
            "alt_destek": "evet",
            "taban_plaka": "hayır",
        },
        {
            "musteri_adi": "çağla çağrı",
            "tarih": "05.07.2026",
            "not": "",
            "adet": 1,
            "etiket_cikar": "evet",
            "etiket_no": "01",
            "isim_kes": "evet",
            "isim_kesim_adet": 1,
            "isim_genislik_mm": 320,
            "isim_stil": "Söz/Nişan Script",
            "alt_destek": "evet",
            "taban_plaka": "hayır",
        },
        {
            "musteri_adi": "deneme hatalı",
            "tarih": "01.01.2026",
            "not": "Test",
            "adet": 1,
            "etiket_cikar": "evet",
            "etiket_no": "99",
            "isim_kes": "evet",
            "isim_kesim_adet": 1,
            "isim_genislik_mm": 300,
            "isim_stil": "Romantik",
            "alt_destek": "hayır",
            "taban_plaka": "hayır",
        },
    ]
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def fifty_name_items() -> list[dict[str, object]]:
    names = [
        "Ayşe Ömer", "Elif Kaan", "Çağla Çağrı", "Merve Yusuf", "İrem Tuğçe",
        "Deniz Emre", "Seda Alper", "Zeynep Burak", "Fatma Ahmet", "Dilara Oğuz",
    ]
    items = []
    for index in range(50):
        text = names[index % len(names)]
        items.append(
            {
                "item_id": f"stress-{index}",
                "row_number": str(index + 2),
                "name_text": text,
                "quantity": "1",
                "width_mm": 150 + (index % 5) * 22,
                "height_mm": 48 + (index % 4) * 6,
                "style": "Söz/Nişan Script",
                "composition": "Tek Satır Yan Yana",
                "support_line": index % 3 == 0,
                "back_plate": index % 9 == 0,
                "status": "READY",
                "warnings": [],
                "errors": [],
                "is_deleted": False,
                "is_edited": False,
            }
        )
    return items


def backend_gate() -> dict[str, object]:
    excel = ensure_sample_excel()
    models = template_api.list_label_model_gallery(PROJECT_ROOT)
    state = combined_production_api.combined_production_state(PROJECT_ROOT, excel, models)
    assert_true(state["status"] == "OK", "Birleşik üretim state oluşmadı", state)
    summary = state["summary"]
    assert_true(summary["total_rows"] == 5, "Toplam satır yanlış", summary)
    assert_true(summary["label_jobs"] == 4, "Etiket işi sayısı yanlış", summary)
    assert_true(summary["name_cut_jobs"] == 4, "İsim kesim işi sayısı yanlış", summary)
    assert_true(summary["both_jobs"] == 3, "İkisi birden işi sayısı yanlış", summary)
    assert_true(state["name_cut_items"][0]["name_text"] == "Ayşe Ömer", "İsim Türkçe formatlanmadı", state["name_cut_items"][0])
    assert_true(any("Türkçe" in warning for warning in state["name_cut_items"][0]["warnings"]), "Türkçe karakter riski yakalanmadı")
    assert_true(state["label_items"][-1]["status"] == "ERROR", "Hatalı model satırı yakalanmadı")

    layout_50 = combined_production_api.layout_name_cut_items(fifty_name_items())
    assert_true(layout_50["summary"]["total_copies"] == 50, "50 isim yerleşimi eksik", layout_50["summary"])
    export = combined_production_api.export_name_cut_batch(PROJECT_ROOT, excel, fifty_name_items())
    assert_true(export["status"] == "OK", "İsim kesim export oluşmadı", export)
    assert_true((PROJECT_ROOT / export["svg_path"]).exists(), "SVG export yok", export)
    assert_true((PROJECT_ROOT / export["pdf_preview"]).exists(), "PDF preview yok", export)
    assert_true((PROJECT_ROOT / export["manifest_path"]).exists(), "Manifest yok", export)
    manifest = json.loads((PROJECT_ROOT / export["manifest_path"]).read_text(encoding="utf-8"))
    assert_true("RDWorks otomatik açılmaz" in manifest["rdworks_note"], "RDWorks güvenlik notu yok", manifest)
    assert_true(manifest["text_to_outline_status"] == "OUTLINED_PATHS_WITH_FONTTOOLS", "Text-to-outline outline durumu beklenen seviyede değil", manifest)
    assert_true(
        any(item.get("diacritic_bridge_status") == "AUTO_TURKISH_DIACRITIC_BRIDGES_ADDED_TO_CUT_OUTLINE" for item in manifest["items"]),
        "Turkce nokta/isaret kopruleri manifest ve export hattina yansimadi",
        manifest["items"][:5],
    )
    state["layout"] = layout_50
    state["name_cut_items"] = fifty_name_items()
    return {
        "sample_excel": str(excel.relative_to(PROJECT_ROOT)),
        "state": state,
        "export": export,
        "manifest": export["manifest_path"],
    }


def ui_gate(backend: dict[str, object]) -> dict[str, object]:
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
          return {{
            page: document.querySelector('.page.active')?.id || '',
            kpis: document.querySelectorAll('#combinedSummaryGrid .combined-kpi').length,
            nameCards: document.querySelectorAll('#nameCutGalleryGrid .name-cut-card').length,
            hasLayout: Boolean(document.querySelector('#nameCutLayoutPreview .laser-layout-stage')),
            hasExport: document.getElementById('nameCutExportPanel')?.innerText || ''
          }};
        }})()
        """)
        wait(1200)
        first = run_js(window, """
        (() => ({
          page: document.querySelector('.page.active')?.id || '',
          kpis: document.querySelectorAll('#combinedSummaryGrid .combined-kpi').length,
          nameCards: document.querySelectorAll('#nameCutGalleryGrid .name-cut-card').length,
          hasLayout: Boolean(document.querySelector('#nameCutLayoutPreview .laser-layout-stage')),
          text: document.getElementById('bulkLabel')?.innerText || '',
          brokenImages: [...document.querySelectorAll('#bulkLabel img')].some(img => img.complete && img.naturalWidth === 0)
        }))()
        """)
        assert_true(first["page"] == "bulkLabel", "Toplu Etiket sayfası açılmadı", first)
        assert_true(first["kpis"] >= 6, "Birleşik üretim KPI kartları eksik", first)
        assert_true(first["nameCards"] >= 50, "İsim kesim galerisi 50 isim göstermiyor", first)
        assert_true(first["hasLayout"], "Lazer yerleşim preview yok", first)
        assert_true("RDWorks" in first["text"], "RDWorks manuel kontrol mesajı görünmüyor", first)
        assert_true(not first["brokenImages"], "UI içinde kırık görsel var", first)
        run_js(window, "(() => { document.querySelector('.combined-production-panel')?.scrollIntoView({ block: 'start' }); return true; })()")
        wait(700)
        screenshots["combined_excel_loading"] = save_screenshot(window, "combined_excel_loading.png")
        run_js(window, "(() => { document.getElementById('nameCutGalleryGrid')?.scrollIntoView({ block: 'center' }); return true; })()")
        wait(700)
        screenshots["name_cut_gallery"] = save_screenshot(window, "name_cut_gallery.png")

        run_js(window, "(() => { openNameCutEditor(0); return { open: !document.getElementById('nameCutEditModal')?.hidden }; })()")
        wait(900)
        modal = run_js(window, """
        (() => ({
          open: !document.getElementById('nameCutEditModal')?.hidden,
          text: document.getElementById('nameCutEditModal')?.innerText || ''
        }))()
        """)
        assert_true(modal["open"], "İsim kesim düzenleme modalı açılmadı", modal)
        assert_true("Alt destek" in modal["text"], "İsim kesim modalında destek ayarları yok", modal)
        screenshots["name_cut_edit_modal"] = save_screenshot(window, "name_cut_edit_modal.png")

        edited_modal = run_js(window, """
        (() => {
          updateNameCutDraftField('name_text', 'Sedef Sefer mücahit');
          const input = document.getElementById('nameCutEditName');
          if (input) input.value = 'Sedef Sefer mücahit';
          return {
            input: input?.value || '',
            preview: document.getElementById('nameCutEditPreview')?.innerText || '',
            bridgeCount: document.querySelectorAll('#nameCutEditPreview .diacritic-cut-bridge').length
          };
        })()
        """)
        wait(400)
        edited_modal = run_js(window, """
        (() => ({
          input: document.getElementById('nameCutEditName')?.value || '',
          preview: document.getElementById('nameCutEditPreview')?.innerText || '',
          bridgeCount: document.querySelectorAll('#nameCutEditPreview .diacritic-cut-bridge').length
        }))()
        """)
        assert_true("Sedef Sefer mücahit" in edited_modal["input"], "Mücahit modal input'a yazılamadı", edited_modal)
        assert_true(edited_modal["bridgeCount"] >= 2, "Türkçe nokta/işaret köprüleri modal preview'de görünmüyor", edited_modal)
        screenshots["name_cut_edit_modal_mucahit_bridged"] = save_screenshot(window, "name_cut_edit_modal_mucahit_bridged.png")
        run_js(window, """
        (() => {
          saveNameCutDraft();
          return { text: document.getElementById('nameCutGalleryGrid')?.innerText || '' };
        })()
        """)
        wait(900)
        edited = run_js(window, "(() => ({ text: document.getElementById('nameCutGalleryGrid')?.innerText || '' }))()")
        assert_true("Sedef Sefer" in edited["text"], "Kaydet isim kesim state'ini güncellemedi", edited)
        screenshots["name_cut_saved_badge"] = save_screenshot(window, "name_cut_saved_badge.png")

        run_js(window, "(() => { document.getElementById('nameCutLayoutPreview')?.scrollIntoView({ block: 'center' }); return true; })()")
        wait(700)
        screenshots["laser_layout_preview"] = save_screenshot(window, "laser_layout_preview.png")
        run_js(window, "(() => { document.getElementById('nameCutExportPanel')?.scrollIntoView({ block: 'center' }); return true; })()")
        wait(700)
        screenshots["export_panel"] = save_screenshot(window, "rdworks_export_panel.png")
    finally:
        window.close()
        app.quit()
    return {"screenshots": screenshots}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    backend = backend_gate()
    ui = ui_gate(backend)
    result = {
        "status": "PASSED",
        "sample_excel": backend["sample_excel"],
        "export": backend["export"],
        "manifest": backend["manifest"],
        "screenshots": ui["screenshots"],
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
