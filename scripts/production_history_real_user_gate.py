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


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "production_history_gate"
RESULT_PATH = OUTPUT_DIR / "PRODUCTION_HISTORY_REAL_USER_GATE_RESULT.json"
DEBUG_PATH = OUTPUT_DIR / "PRODUCTION_HISTORY_REAL_USER_GATE_DEBUG.log"


def debug(message: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_PATH.write_text((DEBUG_PATH.read_text(encoding="utf-8") if DEBUG_PATH.exists() else "") + message + "\n", encoding="utf-8")


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


def wait_for(window: WebMainWindow, script: str, timeout_ms: int = 60000, interval_ms: int = 800):
    deadline = max(1, timeout_ms // interval_ms)
    last = None
    for _ in range(deadline):
        last = run_js(window, script, timeout_ms=min(5000, timeout_ms))
        if isinstance(last, dict) and last.get("ok"):
            return last
        wait(interval_ms)
    raise AssertionError(f"Condition timed out: {last}")


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
      historyCount: (currentState.productionHistory || []).length,
      visibleRows: document.querySelectorAll('#productionHistoryList .production-history-row').length,
      analyticsText: document.getElementById('productionHistoryAnalytics')?.innerText || '',
      listText: document.getElementById('productionHistoryList')?.innerText || '',
      hasSearch: Boolean(document.getElementById('productionHistorySearch')),
      hasModelFilter: Boolean(document.getElementById('productionHistoryModelFilter')),
      hasQueueFilter: Boolean(document.getElementById('productionHistoryQueueFilter')),
      hasValidationFilter: Boolean(document.getElementById('productionHistoryValidationFilter')),
      hasDateFilters: Boolean(document.getElementById('productionHistoryFromDate') && document.getElementById('productionHistoryToDate')),
      hasOpenStudioButton: Boolean([...document.querySelectorAll('#productionHistoryList button')].find(button => (button.textContent || '').includes('Aynı Bilgilerle Studio’da Aç'))),
      hasQueueButton: Boolean([...document.querySelectorAll('#productionHistoryList button')].find(button => (button.textContent || '').includes('Tekrar Sıraya Ekle'))),
      selectedTemplate: document.getElementById('manualTemplate')?.value || '',
      manualText: document.getElementById('manualText')?.value || '',
      manualDate: document.getElementById('manualDateText')?.value || '',
      manualNote: document.getElementById('manualNoteText')?.value || '',
      queueModalOpen: !document.getElementById('queueAddedModal')?.hidden,
      queueModalText: document.getElementById('queueAddedText')?.textContent || '',
      queueModalFile: document.getElementById('queueAddedFile')?.textContent || '',
      consoleErrors: window.__historyGateErrors || []
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    debug("open label outputs")
    run_js(window, """
    (() => {
      window.__historyGateErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__historyGateErrors.push(String(message || error || 'unknown'));
      };
      showSection('labelOutputs');
      updateProductionHistory(currentState.productionHistory || []);
      return { ok: true, historyCount: (currentState.productionHistory || []).length };
    })()
    """, timeout_ms=120000)
    wait(1400)

    debug("inspect page state")
    first = state(window)
    assert_true(first["activePage"] == "labelOutputs", "Etiket Çıktıları sayfası açılmadı", first)
    assert_true(first["hasSearch"], "Üretim geçmişi arama filtresi yok", first)
    assert_true(first["hasModelFilter"], "Üretim geçmişi model filtresi yok", first)
    assert_true(first["hasQueueFilter"], "Üretim geçmişi queue filtresi yok", first)
    assert_true(first["hasValidationFilter"], "Üretim geçmişi doğrulama filtresi yok", first)
    assert_true(first["hasDateFilters"], "Üretim geçmişi tarih filtreleri yok", first)
    assert_true(not first["consoleErrors"], "Console error var", first)
    run_js(window, "(() => { document.getElementById('productionHistoryList')?.scrollIntoView({ block: 'center' }); return { ok: true }; })()")
    wait(450)
    screenshots["history_page"] = save_screenshot(window, "production_history_page.png")
    checks.append({"name": "history_page_filters_and_analytics", "status": "PASSED", "state": first})

    if int(first["historyCount"]) == 0:
        assert_true("Henüz üretim geçmişi yok" in str(first["listText"]), "Boş geçmiş state'i sade değil", first)
        checks.append({"name": "history_empty_state", "status": "PASSED", "state": first})
        return {"status": "PASSED", "checks": checks, "screenshots": screenshots}

    assert_true(int(first["visibleRows"]) > 0, "Üretim geçmişi kaydı ekranda görünmüyor", first)
    assert_true(first["hasOpenStudioButton"], "Geçmişten Studio'da Aç butonu yok", first)
    checks.append({"name": "history_rows_have_reproduce_actions", "status": "PASSED", "state": first})

    debug("open history item in studio")
    studio_result = run_js(window, """
    (() => {
      const row = [...document.querySelectorAll('#productionHistoryList .production-history-row')]
        .find(item => item.querySelector('button[onclick*="openHistoryInStudio"]'));
      if (!row) return { ok: false, error: 'history row with studio button missing' };
      const visibleHistory = filteredProductionHistory(
        customerProductionHistoryRows(currentState.productionHistory || [])
      );
      const before = visibleHistory[0] || {};
      row.querySelector('button[onclick*="openHistoryInStudio"]').click();
      return {
        ok: true,
        expectedLabel: before.label_text || '',
        expectedDate: before.date_text || '',
        expectedNote: before.note_text || '',
        expectedModel: before.model_name || before.model_id || ''
      };
    })()
    """)
    assert_true(studio_result.get("ok"), "Geçmiş Studio butonu tıklanamadı", studio_result)
    wait(1000)
    studio = state(window)
    assert_true(studio["activePage"] == "label", "Geçmişten Studio'da Aç Etiket Studio'ya gitmedi", studio)
    if studio_result.get("expectedLabel"):
        assert_true(studio["manualText"] == studio_result["expectedLabel"], "Geçmiş label_text Studio'ya taşınmadı", {"expected": studio_result, "actual": studio})
    if studio_result.get("expectedDate"):
        assert_true(studio["manualDate"] == studio_result["expectedDate"], "Geçmiş date_text Studio'ya taşınmadı", {"expected": studio_result, "actual": studio})
    if studio_result.get("expectedNote"):
        assert_true(studio["manualNote"] == studio_result["expectedNote"], "Geçmiş note_text Studio'ya taşınmadı", {"expected": studio_result, "actual": studio})
    screenshots["history_opened_in_studio"] = save_screenshot(window, "production_history_opened_in_studio.png")
    checks.append({"name": "history_reopens_same_inputs_in_studio", "status": "PASSED", "state": studio})

    debug("requeue history PDF")
    queue_candidate = run_js(window, """
    (() => {
      const item = (currentState.productionHistory || []).find(row => row.pdf_path || row.batch_pdf_path);
      const pdf = item?.pdf_path || item?.batch_pdf_path || '';
      if (!pdf) return { ok: false, skipped: true, reason: 'history PDF action missing' };
      return { ok: true, pdf };
    })()
    """, timeout_ms=10000)
    if queue_candidate.get("ok"):
        queue_result = window.add_pdf_output_to_print_queue(str(queue_candidate.get("pdf") or ""))
        status = str(queue_result.get("status") or queue_result.get("queue_result", {}).get("status") or "").upper()
        assert_true(status in {"OK", "ADDED", "DUPLICATE", "EXISTS"}, "Geçmiş PDF'i yazdırma sırasına alınamadı", queue_result)
        screenshots["history_requeue_backend_result"] = save_screenshot(window, "production_history_requeue_backend_result.png")
        checks.append({"name": "history_requeues_validated_pdf", "status": "PASSED", "state": queue_result})
    else:
        checks.append({"name": "history_requeues_validated_pdf", "status": "SKIPPED", "state": queue_candidate})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    debug("boot")
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1440, 950)
    window.show()
    wait(6500)
    try:
        result = run_gate(window)
    finally:
        debug("close")
        window.close()
        app.quit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
