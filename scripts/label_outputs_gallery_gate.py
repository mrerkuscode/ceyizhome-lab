from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "label_outputs_gallery_gate"
RESULT_PATH = OUTPUT_DIR / "LABEL_OUTPUTS_GALLERY_GATE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 60000):
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
        raise RuntimeError(f"JavaScript timed out: {script[:160]}")
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


def state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      outputCount: (currentState.labelOutputs || []).length,
      customerOutputCount: (currentState.labelOutputs || []).filter(item => typeof isCustomerOutput === 'function' ? isCustomerOutput(item) : true).length,
      cardCount: document.querySelectorAll('#labelOutputList .output-card:not(.technical-output-item)').length,
      technicalCardCount: document.querySelectorAll('#labelOutputList .technical-output-item').length,
      summaryText: document.getElementById('labelOutputSummary')?.innerText || '',
      previewText: document.getElementById('labelOutputPreview')?.innerText || '',
      hasSearch: Boolean(document.getElementById('labelOutputSearch')),
      hasTypeFilter: Boolean(document.getElementById('labelOutputTypeFilter')),
      hasModelFilter: Boolean(document.getElementById('labelOutputModelFilter')),
      hasDateFilter: Boolean(document.getElementById('labelOutputDateFilter')),
      hasStudioAction: Boolean([...document.querySelectorAll('#labelOutputList button')].find(button => (button.textContent || '').includes('Studio’da Aç'))),
      hasReadyStudioAction: Boolean(document.querySelector('#labelOutputList button[data-history-action="ready"]')),
      hasReproduceAction: Boolean([...document.querySelectorAll('#labelOutputList button')].find(button => (button.textContent || '').includes('Tekrar Üret'))),
      hasFolderAction: Boolean([...document.querySelectorAll('#labelOutputList button')].find(button => (button.textContent || '').includes('Klasörde Göster'))),
      hasQueueAction: Boolean([...document.querySelectorAll('#labelOutputList button')].find(button => (button.textContent || '').includes('Sıraya'))),
      technicalDetailsOpen: Boolean(document.querySelector('.technical-output-card details')?.open),
      manualTemplate: document.getElementById('manualTemplate')?.value || '',
      manualText: document.getElementById('manualText')?.value || '',
      manualDate: document.getElementById('manualDateText')?.value || '',
      manualNote: document.getElementById('manualNoteText')?.value || '',
      statusText: document.getElementById('labelOutputStatus')?.textContent || '',
      consoleErrors: window.__galleryGateErrors || []
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      window.__galleryGateErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__galleryGateErrors.push(String(message || error || 'unknown'));
      };
      showSection('labelOutputs');
      updateLabelOutputs(currentState.labelOutputs || []);
      return { ok: true };
    })()
    """, timeout_ms=120000)
    wait(1400)

    first = state(window)
    assert_true(first["activePage"] == "labelOutputs", "Etiket Çıktıları açılmadı", first)
    assert_true(first["hasSearch"], "Galeri arama filtresi yok", first)
    assert_true(first["hasTypeFilter"], "Dosya tipi filtresi yok", first)
    assert_true(first["hasModelFilter"], "Model filtresi yok", first)
    assert_true(first["hasDateFilter"], "Tarih filtresi yok", first)
    assert_true(not first["technicalDetailsOpen"], "Teknik raporlar varsayılan olarak açık", first)
    assert_true(not first["consoleErrors"], "Console error var", first)
    if int(first["customerOutputCount"]) > 0:
        assert_true(int(first["cardCount"]) > 0, "Müşteri çıktı kartları görünmüyor", first)
        assert_true(int(first["technicalCardCount"]) == 0, "Teknik raporlar müşteri galerisine karıştı", first)
        assert_true(first["hasQueueAction"], "Galeri kartlarında queue aksiyonu yok", first)
        assert_true(first["hasFolderAction"], "Galeri kartlarında klasörde göster aksiyonu yok", first)
        assert_true(first["hasStudioAction"], "Galeri kartlarında Studio’da Aç aksiyonu yok", first)
        assert_true(first["hasReproduceAction"], "Galeri kartlarında Tekrar Üret aksiyonu yok", first)
    run_js(window, "(() => { document.getElementById('labelOutputList')?.scrollIntoView({ block: 'center' }); return { ok: true }; })()")
    wait(450)
    screenshots["gallery_page"] = save_screenshot(window, "label_outputs_gallery_page.png")
    checks.append({"name": "gallery_page_customer_outputs", "status": "PASSED", "state": first})

    if int(first["cardCount"]) > 0:
      selected = run_js(window, """
      (() => {
        const card = document.querySelector('#labelOutputList .output-card:not(.technical-output-item)');
        card?.click();
        return { ok: Boolean(card), text: card?.innerText || '' };
      })()
      """)
      assert_true(selected.get("ok"), "Galeri kartı seçilemedi", selected)
      wait(800)
      preview = state(window)
      assert_true("Listeden çıktı seçin" not in str(preview["previewText"]), "Galeri kartı önizleme panelini güncellemedi", preview)
      screenshots["gallery_preview"] = save_screenshot(window, "label_outputs_gallery_preview.png")
      checks.append({"name": "gallery_card_updates_preview", "status": "PASSED", "state": preview})

      if first["hasStudioAction"]:
          opened = run_js(window, """
          (() => {
            const button = document.querySelector('#labelOutputList button[data-history-action="ready"]')
              || [...document.querySelectorAll('#labelOutputList button')].find(item => (item.textContent || '').includes('Studio’da Aç'));
            if (!button) return { ok: false, reason: 'missing Studio action' };
            const ready = button.dataset.historyAction === 'ready';
            button.click();
            return { ok: true, ready };
          })()
          """)
          assert_true(opened.get("ok"), "Studio’da Aç butonu tıklanamadı", opened)
          wait(900)
          studio = state(window)
          if opened.get("ready"):
              assert_true(studio["activePage"] == "label", "Galeri Studio’da Aç Etiket Studio’ya gitmedi", studio)
              assert_true(bool(studio["manualText"] or studio["manualDate"] or studio["manualNote"]), "Galeri Studio’da Aç üretim bilgilerini taşımadı", studio)
              screenshots["gallery_opened_in_studio"] = save_screenshot(window, "label_outputs_gallery_opened_in_studio.png")
              checks.append({"name": "gallery_open_in_studio", "status": "PASSED", "state": studio})
          else:
              assert_true("üretim geçmişi bulunamadı" in str(studio["statusText"]).lower(), "Geçmişsiz çıktı Studio aksiyonu sade uyarı vermedi", studio)
              checks.append({"name": "gallery_missing_history_is_explained", "status": "PASSED", "state": studio})

    run_js(window, "(() => { showSection('labelOutputs'); selectLabelOutputTab('technical'); return { ok: true }; })()", timeout_ms=120000)
    wait(1000)
    technical = state(window)
    assert_true(technical["activePage"] == "labelOutputs", "Teknik arşiv sekmesi Etiket Çıktıları içinde kalmadı", technical)
    screenshots["gallery_technical_archive"] = save_screenshot(window, "label_outputs_technical_archive.png")
    checks.append({"name": "technical_archive_separated", "status": "PASSED", "state": technical})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1440, 950)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    finally:
        window.close()
        app.quit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
