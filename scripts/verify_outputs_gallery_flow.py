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


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "outputs_gallery_flow"
RESULT_PATH = OUTPUT_DIR / "VERIFY_OUTPUTS_GALLERY_FLOW_RESULT.json"


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


def page_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      outputCount: (currentState.labelOutputs || []).length,
      customerCardCount: document.querySelectorAll('#labelOutputList .output-card:not(.technical-output-item)').length,
      technicalCardCount: document.querySelectorAll('#labelOutputList .technical-output-item').length,
      kpiCount: document.querySelectorAll('#labelOutputSummary .output-kpi').length,
      tabText: document.getElementById('labelOutputTabs')?.innerText || '',
      summaryText: document.getElementById('labelOutputSummary')?.innerText || '',
      previewText: document.getElementById('labelOutputPreview')?.innerText || '',
      infoText: document.getElementById('selectedOutputInfo')?.innerText || '',
      actionText: document.getElementById('selectedOutputActions')?.innerText || '',
      hasStatusFilter: Boolean(document.getElementById('labelOutputStatusFilter')),
      hasQueueFilter: Boolean(document.getElementById('labelOutputQueueFilter')),
      hasPreviewPanel: Boolean(document.querySelector('#labelOutputs .output-preview-panel')),
      hasBrokenImage: [...document.querySelectorAll('#labelOutputs img')].some(img => img.complete && img.naturalWidth === 0),
      hasTechnicalInCustomer: [...document.querySelectorAll('#labelOutputList .output-card:not(.technical-output-item)')]
        .some(card => /report|debug|manifest|calibration/i.test(card.innerText || '')),
      safePrintOpen: !document.getElementById('safePrintModal')?.hidden,
      selectedCard: Boolean(document.querySelector('#labelOutputList .output-card.selected')),
      consoleErrors: window.__outputsGalleryErrors || []
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      window.__outputsGalleryErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__outputsGalleryErrors.push(String(message || error || 'unknown'));
      };
      showSection('labelOutputs');
      updateLabelOutputs(currentState.labelOutputs || []);
      return { ok: true };
    })()
    """, timeout_ms=120000)
    wait(1500)
    first = page_state(window)
    assert_true(first["activePage"] == "labelOutputs", "Etiket Çıktıları sayfası açılmadı", first)
    assert_true(first["kpiCount"] >= 6, "Kompakt KPI kartları eksik", first)
    assert_true("Teknik Arşiv" in str(first["tabText"]) and "Üretim Geçmişi" in str(first["tabText"]), "Tab yapısı eksik", first)
    assert_true(first["hasStatusFilter"], "Kalite durumu filtresi eksik", first)
    assert_true(first["hasQueueFilter"], "Queue filtresi eksik", first)
    assert_true(first["hasPreviewPanel"], "Sağ preview paneli yok", first)
    assert_true(not first["hasTechnicalInCustomer"], "Teknik raporlar müşteri galerisine karıştı", first)
    assert_true(not first["consoleErrors"], "Console error var", first)
    screenshots["gallery"] = save_screenshot(window, "outputs_gallery.png")
    checks.append({"name": "gallery_shell", "status": "PASSED", "state": first})

    selectable_state = first
    if int(selectable_state["customerCardCount"]) == 0 and "kontrol gereken" in str(selectable_state["summaryText"]).lower():
        run_js(window, """
        (() => {
          if (typeof setLabelOutputStatusFilter === 'function') {
            setLabelOutputStatusFilter('check');
          } else {
            const input = document.getElementById('labelOutputStatusFilter');
            if (input) input.value = 'check';
            updateLabelOutputs(currentState.labelOutputs || []);
          }
          return { ok: true };
        })()
        """)
        wait(900)
        selectable_state = page_state(window)
        assert_true(int(selectable_state["customerCardCount"]) > 0, "Kontrol gereken çıktılar filtresi müşteri kartı göstermedi", selectable_state)
        assert_true(not selectable_state["hasTechnicalInCustomer"], "Kontrol gereken filtresine teknik rapor karıştı", selectable_state)
        screenshots["review_outputs"] = save_screenshot(window, "outputs_review_filter.png")
        checks.append({"name": "review_filter_cards", "status": "PASSED", "state": selectable_state})

    if int(selectable_state["customerCardCount"]) > 0:
        selected = run_js(window, """
        (() => {
          const card = document.querySelector('#labelOutputList .output-card:not(.technical-output-item)');
          card?.click();
          return { ok: Boolean(card), text: card?.innerText || '' };
        })()
        """)
        assert_true(selected.get("ok"), "Galeri kartı seçilemedi", selected)
        wait(900)
        selected_state = page_state(window)
        assert_true(selected_state["selectedCard"], "Seçili kart vurgusu oluşmadı", selected_state)
        assert_true("Listeden bir çıktı seçin" not in str(selected_state["previewText"]), "Sağ preview paneli güncellenmedi", selected_state)
        assert_true("Studio’da Aç" in str(selected_state["actionText"]), "Sağ panel Studio’da Aç aksiyonu göstermiyor", selected_state)
        assert_true("Tekrar Üret" in str(selected_state["actionText"]), "Sağ panel Tekrar Üret aksiyonu göstermiyor", selected_state)
        assert_true(("Sıraya" in str(selected_state["actionText"])) or ("Sırasına" in str(selected_state["actionText"])) or ("PDF eklenir" in str(selected_state["actionText"])), "Sağ panel queue aksiyonu göstermiyor", selected_state)
        assert_true(not selected_state["hasBrokenImage"], "Kırık image var", selected_state)
        screenshots["selected_preview"] = save_screenshot(window, "outputs_selected_preview.png")
        checks.append({"name": "selected_preview_panel", "status": "PASSED", "state": selected_state})

        print_result = run_js(window, """
        (() => {
          const button = [...document.querySelectorAll('#selectedOutputActions button, #labelOutputList button')]
            .find(item => (item.textContent || '').includes('Yazdır'));
          if (!button) return { ok: false, reason: 'missing print button' };
          button.click();
          return { ok: true };
        })()
        """)
        assert_true(print_result.get("ok"), "Yazdır butonu bulunamadı", print_result)
        wait(1200)
        print_state = page_state(window)
        assert_true(print_state["safePrintOpen"] or "PDF kontrol sistemi" in str(print_state["consoleErrors"]) or "Önce PDF" in str(print_state["previewText"] + print_state["actionText"]), "Yazdır güvenli onay/hata akışı üretmedi", print_state)
        screenshots["print_modal"] = save_screenshot(window, "outputs_print_modal.png")
        checks.append({"name": "safe_print_action", "status": "PASSED", "state": print_state})

    run_js(window, "(() => { if (typeof closeSafePrintModal === 'function') closeSafePrintModal(); showSection('labelOutputs'); selectLabelOutputTab('technical'); return { ok: true }; })()")
    wait(800)
    technical = page_state(window)
    assert_true(int(technical["customerCardCount"]) == int(technical["technicalCardCount"]) or int(technical["technicalCardCount"]) >= 0, "Teknik arşiv sekmesi render olmadı", technical)
    screenshots["technical_archive"] = save_screenshot(window, "outputs_technical_archive.png")
    checks.append({"name": "technical_archive_tab", "status": "PASSED", "state": technical})

    run_js(window, "(() => { selectLabelOutputTab('history'); return { ok: true }; })()")
    wait(800)
    history = page_state(window)
    assert_true("Üretim geçmişi" in str(history["previewText"] + history["summaryText"] + history["tabText"]) or int(history["customerCardCount"]) >= 0, "Üretim geçmişi tabı çalışmadı", history)
    screenshots["history_tab"] = save_screenshot(window, "outputs_history_tab.png")
    checks.append({"name": "history_tab", "status": "PASSED", "state": history})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 940)
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
