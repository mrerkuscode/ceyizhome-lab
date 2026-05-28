from __future__ import annotations

import json
import subprocess
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
from webui_backend import bulk_label_api, label_api, print_queue_api, template_api  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "bulk_gallery_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_BULK_GALLERY_EXCEL_FLOW_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def flush_ui(window: WebMainWindow, ms: int = 300) -> None:
    app = QApplication.instance()
    if app:
        app.processEvents()
    wait(ms)
    if app:
        app.processEvents()
    window.view.repaint()
    if app:
        app.processEvents()


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
    flush_ui(window, 350)
    window.view.grab().save(str(path))
    assert_true(path.exists() and path.stat().st_size > 0, f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def ensure_sample_excel() -> Path:
    path = PROJECT_ROOT / "examples" / "toplu_etiket_ornek.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"etiket_no": "01", "isim": "Ayşe & Mehmet", "tarih": "15.05.2026", "not": "Nişan Hatırası", "adet": 10},
            {"etiket_no": "03", "isim": "Burcu & Baran", "tarih": "20.06.2026", "not": "Söz Hatırası", "adet": 5},
            {"etiket_no": "01", "isim": "Çok Uzun İsim Örneği & Mehmet Can Uzunsoy", "tarih": "01.07.2026", "not": "Hatıra", "adet": 2},
            {"etiket_no": "99", "isim": "Hatalı Model", "tarih": "01.01.2026", "not": "Test", "adet": 1},
        ]
    ).to_excel(path, index=False)
    return path


def ensure_hundred_row_excel() -> Path:
    path = PROJECT_ROOT / "examples" / "toplu_etiket_100_ornek.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(1, 101):
        model_no = "99" if index in {25, 75} else "03" if index % 3 == 0 else "01"
        rows.append(
            {
                "etiket_no": model_no,
                "isim": f"Müşteri {index:03d} & Test",
                "tarih": f"{(index % 28) + 1:02d}.06.2026",
                "not": "Uzun isim kontrolü" if index % 10 == 0 else "Hatıra",
                "adet": (index % 5) + 1,
            }
        )
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def backend_gate() -> dict[str, object]:
    excel = ensure_sample_excel()
    hundred_excel = ensure_hundred_row_excel()
    models = template_api.list_label_model_gallery(PROJECT_ROOT)
    items = bulk_label_api.bulk_gallery_items(PROJECT_ROOT, excel, models)
    hundred_items = bulk_label_api.bulk_gallery_items(PROJECT_ROOT, hundred_excel, models)
    assert_true(len(items) == 4, f"Beklenen 4 galeri item, gelen {len(items)}")
    assert_true(len(hundred_items) == 100, f"Beklenen 100 galeri item, gelen {len(hundred_items)}")
    assert_true(sum(1 for item in hundred_items if item["status"] == "ERROR") == 2, "100 satır fixture hatalı model satırlarını yakalamadı")
    hundred_summary = bulk_label_api.bulk_gallery_summary(hundred_items)
    assert_true(hundred_summary["total_rows"] == 100, "100 satır summary toplamı hatalı")
    assert_true(hundred_summary["ready_rows"] >= 90, "100 satır summary hazır sayısı beklenenden düşük")
    hundred_result = bulk_label_api.write_gallery_items_excel(PROJECT_ROOT, hundred_excel, hundred_items)
    assert_true(hundred_result["status"] == "OK", f"100 satir hazir Excel hazirlanamadi: {hundred_result}")
    assert_true(hundred_result["row_count"] == 98, "100 satir fixture hatali satirlari uretim Excel'inden cikarmadi", hundred_result)
    hundred_manifest = PROJECT_ROOT / str(hundred_result["manifest_path"])
    assert_true(hundred_manifest.exists(), "100 satir batch manifest olusmadi", hundred_result)
    hundred_manifest_data = json.loads(hundred_manifest.read_text(encoding="utf-8"))
    assert_true(hundred_manifest_data["total_rows"] == 100, "100 satir manifest toplam satir hatali")
    assert_true(hundred_manifest_data["ready_rows"] == 98, "100 satir manifest hazir satir hatali")
    assert_true(hundred_manifest_data["error_rows"] == 2, "100 satir manifest hata satiri hatali")
    assert_true(len([row for row in hundred_manifest_data["rows"] if row["status"] == "ERROR"]) == 2, "100 satir manifest hata satirlarini saklamadi")
    assert_true(items[0]["model_status"] == "FOUND", "01 modeli eşleşmedi")
    assert_true(items[1]["model_status"] == "FOUND", "03 modeli eşleşmedi")
    assert_true(items[2]["model_status"] == "FOUND", "Uzun isim satırı modeli eşleşmedi")
    assert_true(items[3]["status"] == "ERROR", "99 model no hatalı satır üretmedi")
    assert_true(items[0]["label_text"] == "Ayşe & Mehmet", "İsim label_text alanına gitmedi")
    assert_true(items[0]["date_text"] == "15.05.2026", "Tarih date_text alanına gitmedi")
    assert_true(items[0]["note_text"] == "Nişan Hatırası", "Not note_text alanına gitmedi")
    assert_true(str(items[0]["quantity"]) == "10", "Adet quantity alanına gitmedi")

    draft = dict(items[0])
    draft["label_text"] = "Ayşe & Mehmet QA"
    draft["is_edited"] = True
    items[0] = draft
    deleted = dict(items[3])
    deleted["is_deleted"] = True
    deleted["is_edited"] = True
    items[3] = deleted

    result = bulk_label_api.write_gallery_items_excel(PROJECT_ROOT, excel, items)
    assert_true(result["status"] == "OK", f"Galeri Excel hazırlanamadı: {result}")
    ready_excel = PROJECT_ROOT / str(result["relative_path"])
    manifest = PROJECT_ROOT / str(result["manifest_path"])
    assert_true(ready_excel.exists(), "Hazır üretim Excel dosyası oluşmadı")
    assert_true(manifest.exists(), "Batch manifest oluşmadı")
    assert_true(ready_excel != PROJECT_ROOT / str(hundred_result["relative_path"]), "Ardışık toplu üretim Excel dosyaları aynı path'e yazıldı")
    assert_true(manifest != hundred_manifest, "Ardışık toplu üretim manifest dosyaları aynı path'e yazıldı")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert_true(manifest_data["total_rows"] == 4, "Manifest toplam satır hatalı")
    assert_true(manifest_data["deleted_rows"] == 1, "Manifest silinen satır sayısı hatalı")
    assert_true(manifest_data["ready_rows"] >= 2, "Manifest hazır satır sayısı hatalı")
    rendered_rows = pd.read_excel(ready_excel, dtype=object)
    assert_true("Ayşe & Mehmet QA" in set(rendered_rows["label_text"].astype(str)), "Kaydet düzenlemesi üretim Excel'ine yansımadı")

    run = subprocess.run(
        [sys.executable, "src/main.py", "--excel", str(ready_excel), "--render-labels"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert_true(run.returncode == 0, f"Toplu galeri render başarısız:\nSTDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}")
    outputs = label_api.list_label_outputs(PROJECT_ROOT)
    pdf_rows = [row for row in outputs if str(row.get("relative_path") or "").lower().endswith(".pdf")]
    latest_pdf = max(
        pdf_rows,
        key=lambda row: Path(str(row.get("file_path") or PROJECT_ROOT / str(row.get("relative_path") or ""))).stat().st_mtime,
        default=None,
    )
    assert_true(bool(latest_pdf), "Render sonrası PDF bulunamadı")
    queue_result = print_queue_api.add_label_outputs_to_queue(PROJECT_ROOT, outputs)
    assert_true(queue_result.get("status") in {"OK", "WARNING"}, f"Queue güncellenemedi: {queue_result}")

    manifest_data["generated_pdf"] = latest_pdf.get("relative_path") or ""
    manifest_data["queue_path"] = queue_result.get("queue_path") or ""
    manifest.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "sample_excel": str(excel.relative_to(PROJECT_ROOT)),
        "hundred_row_excel": str(hundred_excel.relative_to(PROJECT_ROOT)),
        "hundred_row_summary": hundred_summary,
        "hundred_ready_excel": str((PROJECT_ROOT / str(hundred_result["relative_path"])).relative_to(PROJECT_ROOT)),
        "hundred_manifest": str(hundred_manifest.relative_to(PROJECT_ROOT)),
        "ready_excel": str(ready_excel.relative_to(PROJECT_ROOT)),
        "manifest": str(manifest.relative_to(PROJECT_ROOT)),
        "generated_pdf": latest_pdf.get("relative_path"),
        "queue_status": queue_result.get("status"),
        "ui_items": bulk_label_api.bulk_gallery_items(PROJECT_ROOT, excel, models),
        "hundred_ui_items": hundred_items,
    }


def page_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      stepCount: document.querySelectorAll('#bulkLabel .bulk-stepper span').length,
      summaryCount: document.querySelectorAll('#bulkGallerySummary > div').length,
      cardCount: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item').length,
      selectedCards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.selected').length,
      errorCards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.has-error').length,
      editedCards: [...document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item')].filter(card => (card.innerText || '').includes('Düzenlendi')).length,
      deletedCards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.deleted').length,
      hasDetailPanel: Boolean(document.getElementById('bulkSelectedInfo')),
      detailText: document.getElementById('bulkSelectedInfo')?.innerText || '',
      actionText: document.getElementById('bulkSelectedActions')?.innerText || '',
      modalOpen: !document.getElementById('bulkGalleryEditModal')?.hidden,
      modalText: document.getElementById('bulkGalleryEditModal')?.innerText || '',
      safePrintOpen: !document.getElementById('safePrintModal')?.hidden,
      hasSearch: Boolean(document.getElementById('bulkGallerySearch')),
      hasBrokenImage: [...document.querySelectorAll('#bulkLabel img')].some(img => img.complete && img.naturalWidth === 0),
      bodyText: document.getElementById('bulkLabel')?.innerText || ''
    }))()
    """)


def hundred_row_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      const summary = {};
      [...document.querySelectorAll('#bulkGallerySummary > div')].forEach(card => {
        const key = (card.querySelector('span')?.innerText || '').trim();
        const value = Number((card.querySelector('b')?.innerText || '0').replace(/[^0-9]/g, '')) || 0;
        if (key) summary[key] = value;
      });
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        cardCount: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item').length,
        errorCards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.has-error').length,
        selectedCards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.selected').length,
        summary,
        hasSearch: Boolean(document.getElementById('bulkGallerySearch')),
        hasBrokenImage: [...document.querySelectorAll('#bulkLabel img')].some(img => img.complete && img.naturalWidth === 0),
        firstCardText: document.querySelector('#bulkGalleryGrid .bulk-gallery-item')?.innerText || '',
        errorText: [...document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item.has-error')].slice(0, 2).map(card => card.innerText).join('\\n')
      };
    })()
    """)


def scroll_to_bulk_gallery(window: WebMainWindow) -> None:
    run_js(window, """
    (() => {
      const target = document.getElementById('bulkGalleryGrid') || document.getElementById('bulkGallerySummary');
      target?.scrollIntoView({ block: 'start', inline: 'nearest' });
      return {
        top: target?.getBoundingClientRect().top || 0,
        cards: document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item').length
      };
    })()
    """)
    flush_ui(window, 650)


def ui_gate(backend: dict[str, object]) -> dict[str, object]:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1680, 980)
    window.show()
    wait(6500)
    screenshots: dict[str, str] = {}
    checks: list[dict[str, object]] = []
    items_json = json.dumps(backend["ui_items"], ensure_ascii=False)
    hundred_items_json = json.dumps(backend["hundred_ui_items"], ensure_ascii=False)
    generated_pdf = str(backend.get("generated_pdf") or "")
    try:
        run_js(window, f"""
        (() => {{
          window.__bulkGalleryErrors = [];
          window.onerror = (message, source, line, column, error) => {{
            window.__bulkGalleryErrors.push(String(message || error || 'unknown'));
          }};
          window.__setBulkGalleryForVerification = (items, excelName) => {{
            currentState = {{
              ...currentState,
              readiness: 'HAZIR',
              selectedExcelName: excelName || currentState.selectedExcelName || 'siparisler.xlsx',
              bulkGalleryItems: items
            }};
            const summary = bulkGallerySummary(items);
            setText('bulkExcelName', currentState.selectedExcelName);
            setText('bulkTotalOrders', summary.total);
            setText('bulkLabelJobs', summary.ready);
            setText('bulkReviewJobs', summary.warning);
            setText('bulkErrorJobs', summary.error);
            setText('bulkLastRunText', 'Son kontrol durumu: HAZIR');
            bulkGalleryItems = items;
            selectedBulkGalleryItemId = bulkGalleryItems[0]?.item_id || '';
            renderBulkGallery();
          }};
          showSection('bulkLabel');
          window.__setBulkGalleryForVerification({items_json}, 'toplu_etiket_ornek.xlsx');
          return {{ ok: true }};
        }})()
        """, timeout_ms=120000)
        wait(1200)
        run_js(window, f"""
        (() => {{
          showSection('bulkLabel');
          bulkGalleryFilter = 'all';
          bulkGallerySearch = '';
          window.__setBulkGalleryForVerification({hundred_items_json}, 'toplu_etiket_100_ornek.xlsx');
          return {{ ok: true, count: bulkGalleryItems.length }};
        }})()
        """, timeout_ms=120000)
        wait(1200)
        hundred = hundred_row_state(window)
        expected_summary = backend["hundred_row_summary"]
        assert_true(hundred["activePage"] == "bulkLabel", "100 satir galeri Toplu Etiket sayfasinda acilmadi", hundred)
        assert_true(hundred["cardCount"] == 100, "100 satir fixture UI galerisine tam basilmadi", hundred)
        assert_true(hundred["errorCards"] == expected_summary["error_rows"], "100 satir hata karti summary ile senkron degil", hundred)
        assert_true(hundred["summary"].get("Toplam satır") == expected_summary["total_rows"], "100 satir toplam summary UI ile senkron degil", hundred)
        assert_true(hundred["summary"].get("Hazır") == expected_summary["ready_rows"], "100 satir hazir summary UI ile senkron degil", hundred)
        assert_true(hundred["summary"].get("Hatalı") == expected_summary["error_rows"], "100 satir hata summary UI ile senkron degil", hundred)
        assert_true(hundred["summary"].get("Toplam adet") == expected_summary["total_quantity"], "100 satir adet summary UI ile senkron degil", hundred)
        assert_true(hundred["hasSearch"], "100 satir galeri arama alani yok", hundred)
        assert_true(not hundred["hasBrokenImage"], "100 satir galeri kirik image gosteriyor", hundred)
        assert_true("model bulunamad" in str(hundred["errorText"]).lower(), "100 satir hatali model mesaji gorunmuyor", hundred)
        scroll_to_bulk_gallery(window)
        screenshots["hundred_row_gallery"] = save_screenshot(window, "bulk_100_row_gallery.png")
        checks.append({"name": "hundred_row_gallery_summary_sync", "status": "PASSED", "state": hundred})

        run_js(window, f"""
        (() => {{
          bulkGalleryFilter = 'all';
          bulkGallerySearch = '';
          window.__setBulkGalleryForVerification({items_json}, 'toplu_etiket_ornek.xlsx');
          return {{ ok: true, count: bulkGalleryItems.length }};
        }})()
        """, timeout_ms=120000)
        wait(1200)
        first = page_state(window)
        assert_true(first["activePage"] == "bulkLabel", "Toplu Etiket sayfası açılmadı", first)
        assert_true(first["stepCount"] >= 6, "6 adımlı stepper görünmüyor", first)
        assert_true(first["summaryCount"] >= 7, "Galeri özet kartları eksik", first)
        assert_true(first["cardCount"] == 4, "Excel satırları galeri kartına dönüşmedi", first)
        assert_true(first["errorCards"] >= 1, "Hatalı model satırı görünmüyor", first)
        assert_true(first["hasDetailPanel"], "Seçili etiket detay paneli eksik", first)
        assert_true(first["hasSearch"], "Galeri arama alanı eksik", first)
        assert_true(not first["hasBrokenImage"], "Toplu Etiket içinde kırık preview görseli var", first)
        assert_true("Ay" in str(first["bodyText"]) and first["cardCount"] == 4, "Galeri kartlari kullanici ekraninda gorunur degil", first)
        scroll_to_bulk_gallery(window)
        screenshots["gallery_view"] = save_screenshot(window, "bulk_gallery_view.png")
        checks.append({"name": "gallery_layout", "status": "PASSED", "state": first})

        run_js(window, """
        (() => {
          const second = document.querySelectorAll('#bulkGalleryGrid .bulk-gallery-item')[1];
          second?.click();
          return { ok: Boolean(second), text: second?.innerText || '' };
        })()
        """)
        wait(700)
        selected = page_state(window)
        assert_true(selected["selectedCards"] == 1, "Kart seçimi selected state üretmedi", selected)
        assert_true("Burcu" in str(selected["detailText"]), "Sağ detay paneli seçili kartla senkron değil", selected)
        screenshots["selected_detail"] = save_screenshot(window, "bulk_selected_detail.png")
        checks.append({"name": "selected_detail_panel", "status": "PASSED", "state": selected})

        run_js(window, "(() => { openBulkGalleryEditor(0); return { ok: true }; })()")
        wait(900)
        modal = page_state(window)
        assert_true(modal["modalOpen"], "Galeri düzenleme modalı açılmadı", modal)
        screenshots["edit_modal"] = save_screenshot(window, "bulk_edit_modal.png")
        run_js(window, """
        (() => {
          const input = document.getElementById('bulkGalleryEditName');
          input.value = 'Ayşe & Mehmet LIVE';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return { preview: document.getElementById('bulkGalleryEditPreview')?.innerText || '' };
        })()
        """)
        wait(500)
        live = page_state(window)
        assert_true("LIVE" in str(live["modalText"]), "Modal canlı preview/input değişimini göstermedi", live)
        screenshots["modal_live_preview"] = save_screenshot(window, "bulk_modal_live_preview.png")
        run_js(window, "(() => { saveBulkGalleryDraft(); return { ok: true }; })()")
        wait(700)
        edited = page_state(window)
        assert_true(edited["editedCards"] >= 1, "Kaydet sonrası düzenlendi badge'i oluşmadı", edited)
        assert_true("LIVE" in str(edited["bodyText"]), "Kaydet değişikliği galeri state'ine işlemedi", edited)
        screenshots["edited_badge"] = save_screenshot(window, "bulk_edited_badge.png")
        checks.append({"name": "edit_save_live_preview", "status": "PASSED", "state": edited})

        run_js(window, """
        (() => {
          openBulkGalleryEditor(1);
          const input = document.getElementById('bulkGalleryEditName');
          input.value = 'VAZGEC TESTI';
          input.dispatchEvent(new Event('input', { bubbles: true }));
          cancelBulkGalleryDraft();
          return { ok: true };
        })()
        """)
        wait(700)
        cancel = page_state(window)
        assert_true("VAZGEC TESTI" not in str(cancel["bodyText"]), "Vazgeç modal değişikliğini geri almadı", cancel)
        checks.append({"name": "cancel_does_not_mutate_item", "status": "PASSED", "state": cancel})

        run_js(window, "(() => { markBulkGalleryDeleted(3); return { ok: true }; })()")
        wait(700)
        deleted = page_state(window)
        assert_true(deleted["deletedCards"] >= 1, "Sil item'ı üretimden çıkarılmış olarak işaretlemedi", deleted)
        screenshots["deleted_item"] = save_screenshot(window, "bulk_deleted_item.png")
        checks.append({"name": "delete_marks_item", "status": "PASSED", "state": deleted})

        run_js(window, f"(() => {{ requestPdfPrint('{generated_pdf}'); return {{ ok: true }}; }})()")
        wait(1200)
        safe_print = page_state(window)
        assert_true(safe_print["safePrintOpen"], "Toplu Yazdır güvenli onay modalı açmadı", safe_print)
        screenshots["print_modal"] = save_screenshot(window, "bulk_print_modal.png")
        run_js(window, "(() => { if (typeof closeSafePrintModal === 'function') closeSafePrintModal(); return { ok: true }; })()")
        checks.append({"name": "safe_print_modal", "status": "PASSED", "state": safe_print})

        run_js(window, "(() => { showSection('printQueue'); updatePrintQueue(currentState.printQueue || []); return { ok: true }; })()")
        wait(1000)
        screenshots["print_queue_batch_item"] = save_screenshot(window, "bulk_print_queue_batch_item.png")
        checks.append({"name": "queue_navigation", "status": "PASSED", "state": {"screenshot": screenshots["print_queue_batch_item"]}})
    finally:
        window.close()
        app.quit()
    return {"checks": checks, "screenshots": screenshots}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    backend = backend_gate()
    ui = ui_gate(backend)
    result = {
        "status": "PASSED",
        **{key: value for key, value in backend.items() if key not in {"ui_items", "hundred_ui_items"}},
        "checks": ui["checks"],
        "screenshots": ui["screenshots"],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
