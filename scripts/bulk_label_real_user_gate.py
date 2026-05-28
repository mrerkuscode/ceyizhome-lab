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


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "bulk_label_gate"
RESULT_PATH = OUTPUT_DIR / "BULK_LABEL_REAL_USER_GATE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
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
        raise RuntimeError(f"JavaScript timed out: {script[:120]}")
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
      stepCount: document.querySelectorAll('#bulkLabel .studio-steps span').length,
      hasExcelSelect: Boolean([...document.querySelectorAll('#bulkLabel button')].find(button => (button.textContent || '').includes('Excel Seç'))),
      hasDryRun: Boolean([...document.querySelectorAll('#bulkLabel button')].find(button => (button.textContent || '').includes('Kontrol Et'))),
      hasGenerate: Boolean([...document.querySelectorAll('#bulkLabel button')].find(button => (button.textContent || '').includes('Çıktıları Oluştur'))),
      hasQueueAll: Boolean([...document.querySelectorAll('#bulkLabel button')].find(button => (button.textContent || '').includes('Sıraya Ekle'))),
      hasRealMiniPreview: Boolean(document.querySelector("button[onclick='renderBulkRealMiniPreviews()']")),
      hasSelectedRowsGenerate: Boolean(document.querySelector("button[onclick='generateSelectedBulkRowsAndQueue()']")),
      hasRollPreview: Boolean(document.getElementById('rollLayoutPreview')),
      hasRowPreviewList: Boolean(document.getElementById('bulkRowPreviewList')),
      selectedExcelPath: currentState.selectedExcelPath || '',
      selectedExcelName: currentState.selectedExcelName || '',
      rollPreviewText: document.getElementById('rollLayoutPreview')?.innerText || '',
      rowPreviewText: document.getElementById('bulkRowPreviewList')?.innerText || '',
      statusText: document.getElementById('bulkRowPreviewStatus')?.textContent || '',
      directPrintText: document.getElementById('bulkLabel')?.innerText || '',
      consoleErrors: window.__bulkGateErrors || []
    }))()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      window.__bulkGateErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__bulkGateErrors.push(String(message || error || 'unknown'));
      };
      showSection('bulkLabel');
      return { ok: true };
    })()
    """, timeout_ms=120000)
    wait(1200)

    first = state(window)
    assert_true(first["activePage"] == "bulkLabel", "Toplu Etiket sayfası açılmadı", first)
    assert_true(first["stepCount"] >= 5, "Toplu Etiket stepper eksik", first)
    assert_true(first["hasExcelSelect"], "Excel Seç butonu yok", first)
    assert_true(first["hasDryRun"], "Kontrol Et butonu yok", first)
    assert_true(first["hasGenerate"], "Çıktıları Oluştur butonu yok", first)
    assert_true(first["hasRealMiniPreview"], "Gerçek Mini Önizleme Oluştur butonu yok", first)
    assert_true(first["hasSelectedRowsGenerate"], "Seçili Satırları Üret ve Sıraya Ekle butonu yok", first)
    assert_true(first["hasRollPreview"], "Rulo Yerleşim Önizlemesi yok", first)
    assert_true("Direct print yok" in str(first["directPrintText"]), "Direct print güvenlik dili görünmüyor", first)
    assert_true(not first["consoleErrors"], "Console error var", first)
    screenshots["bulk_page"] = save_screenshot(window, "bulk_label_page.png")
    checks.append({"name": "bulk_page_controls", "status": "PASSED", "state": first})

    run_js(window, """
    (() => {
      updateBulkRowPreview(currentState.bulkPreviewSamples || [], currentState.reviewRows || currentState.errorRows || []);
      updateRollLayoutPreview(currentState);
      return {
        rowCards: document.querySelectorAll('.bulk-row-card').length,
        rollText: document.getElementById('rollLayoutPreview')?.innerText || ''
      };
    })()
    """)
    wait(700)
    preview = state(window)
    assert_true("Rulo" in str(preview["rollPreviewText"]) or "Etiket" in str(preview["rollPreviewText"]), "Rulo yerleşim özeti dolmadı", preview)
    screenshots["bulk_row_preview"] = save_screenshot(window, "bulk_label_row_preview.png")
    checks.append({"name": "bulk_row_and_roll_preview", "status": "PASSED", "state": preview})

    bridge_checks = run_js(window, """
    (() => {
      const source = String(renderBulkRealMiniPreviews) + String(renderSelectedBulkMiniPreviews) + String(generateSelectedBulkRowsAndQueue);
      return {
        hasPreviewBridge: source.includes('render_bulk_preview_samples'),
        hasSelectedBridge: source.includes('render_selected_bulk_preview_samples') || source.includes('bulk_generate_selected_and_add_to_queue'),
        hasNoSilentPrint: !source.includes('window.print')
      };
    })()
    """)
    assert_true(bridge_checks["hasPreviewBridge"], "Mini preview gerçek render bridge akışına bağlı değil", bridge_checks)
    assert_true(bridge_checks["hasSelectedBridge"], "Seçili satır üretimi bridge akışına bağlı değil", bridge_checks)
    assert_true(bridge_checks["hasNoSilentPrint"], "Toplu akışta silent print referansı var", bridge_checks)
    checks.append({"name": "bulk_bridge_actions_are_real", "status": "PASSED", "state": bridge_checks})

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1440, 950)
    window.show()
    wait(6000)
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
