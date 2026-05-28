from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-20" / "production_etiket_studio_step3_preflight_panel"
RESULT_PATH = OUTPUT_DIR / "production_etiket_studio_step3_preflight_panel_gate_result.json"
TEMPLATE_SUFFIX = "templates/designs/01_a_gold.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


def suppress_message_boxes() -> None:
    QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *args, **kwargs: QMessageBox.Yes)


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
    loop = QEventLoop()
    result = {"done": False, "value": None}

    def callback(value):
        result["done"] = True
        result["value"] = value
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), "stack": String(error && error.stack || "") }});
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


def poll_js(window: WebMainWindow, script: str, predicate, timeout_ms: int = 60000, interval_ms: int = 250):
    elapsed = 0
    last = None
    while elapsed <= timeout_ms:
        last = run_js(window, script, timeout_ms=10000)
        if predicate(last):
            return last
        wait(interval_ms)
        elapsed += interval_ms
    raise RuntimeError(f"Polling timed out. Last value: {last}")


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def setup_label_studio(window: WebMainWindow) -> dict:
    result = run_js(window, f"""
    (() => {{
      showSection('label');
      if (typeof setupManualLiveBindings === 'function') setupManualLiveBindings();
      const target = {json.dumps(TEMPLATE_SUFFIX)};
      const normal = value => String(value || '').replace(/\\\\/g, '/');
      const model = (currentLabelModels || []).find(item => normal(item.path).endsWith(target)) || (currentLabelModels || [])[0] || null;
      if (model?.path) useModelForManual(model.path);
      const setInput = (id, value) => {{
        const el = document.getElementById(id);
        if (!el) return false;
        el.value = value;
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return true;
      }};
      setInput('manualText', 'Ayşe & Mehmet');
      setInput('manualDateText', '12.05.2026');
      setInput('manualNoteText', 'Söz Hatırası');
      setInput('manualQty', '2');
      setInput('manualLaserName', 'Ayşe & Mehmet');
      if (typeof setManualZoom === 'function') setManualZoom('fit');
      const labelIndex = (selectedLabelModel?.fields_summary || []).findIndex(field => field.excel_column === 'label_text');
      if (labelIndex >= 0 && typeof selectField === 'function') selectField(labelIndex);
      if (typeof syncManualValuesFromInputs === 'function') syncManualValuesFromInputs();
      if (typeof showManualPreviewPlaceholder === 'function') showManualPreviewPlaceholder();
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return {{
        ok: Boolean(selectedLabelModel),
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
        outputBadge: document.getElementById('manualOutputControlBadge')?.textContent || '',
        controlText: document.getElementById('manualOutputControlCard')?.innerText || ''
      }};
    }})()
    """, timeout_ms=60000)
    wait(1200)
    if not result.get("ok"):
        raise RuntimeError(f"Model seçimi başarısız: {result}")
    return result


def snapshot(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => ({
      activeSection: document.querySelector('.page.active')?.id || '',
      modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
      manualText: document.getElementById('manualText')?.value || '',
      manualDateText: document.getElementById('manualDateText')?.value || '',
      manualNoteText: document.getElementById('manualNoteText')?.value || '',
      manualQty: document.getElementById('manualQty')?.value || '',
      manualLaserName: document.getElementById('manualLaserName')?.value || '',
      badge: document.getElementById('manualOutputControlBadge')?.textContent || '',
      controlText: document.getElementById('manualOutputControlCard')?.innerText || '',
      controlVisible: Boolean(document.getElementById('manualOutputControlCard')),
      outputActionsText: document.getElementById('manualOutputActions')?.innerText || '',
      preflightText: document.getElementById('manualPreflightStatus')?.innerText || '',
      safePrintVisible: !(document.getElementById('safePrintModal')?.hidden ?? true),
      queueVisible: !(document.getElementById('queueAddedModal')?.hidden ?? true),
      queueFile: document.getElementById('queueAddedFile')?.textContent || '',
      previewHasModelSelectText: (document.getElementById('manualPreview')?.innerText || '').includes('Model seçin')
    }))()
    """)


def run_render(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      window.__step3RenderDone = false;
      window.__step3RenderResult = null;
      renderManual({
        silent: true,
        silentPreflight: false,
        skipStateRefresh: false,
        onComplete: (result, ok) => {
          window.__step3RenderDone = true;
          window.__step3RenderResult = { ok, result, controlText: document.getElementById('manualOutputControlCard')?.innerText || '' };
        }
      });
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ done: Boolean(window.__step3RenderDone), payload: window.__step3RenderResult || null }))()",
        lambda value: value.get("done") is True,
        timeout_ms=90000,
    )


def run_invalid_quantity(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const qty = document.getElementById('manualQty');
      qty.value = '0';
      qty.dispatchEvent(new Event('input', { bubbles: true }));
      let callbackCalled = false;
      let errorResult = null;
      runManualPreflight(
        () => { callbackCalled = true; },
        { onError: result => { errorResult = result; } }
      );
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return {
        callbackCalled,
        errorResult,
        badge: document.getElementById('manualOutputControlBadge')?.textContent || '',
        controlText: document.getElementById('manualOutputControlCard')?.innerText || '',
        preflightText: document.getElementById('manualPreflightStatus')?.innerText || ''
      };
    })()
    """)


def restore_quantity(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const qty = document.getElementById('manualQty');
      qty.value = '2';
      qty.dispatchEvent(new Event('input', { bubbles: true }));
      qty.dispatchEvent(new Event('change', { bubbles: true }));
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return { qty: qty.value, badge: document.getElementById('manualOutputControlBadge')?.textContent || '' };
    })()
    """)


def run_queue(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      window.__step3QueueStarted = true;
      renderManualToQueue();
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ visible: !(document.getElementById('queueAddedModal')?.hidden ?? true), text: document.getElementById('queueAddedText')?.textContent || '', file: document.getElementById('queueAddedFile')?.textContent || '', controlText: document.getElementById('manualOutputControlCard')?.innerText || '' }))()",
        lambda value: value.get("visible") is True,
        timeout_ms=90000,
    )


def run_print_warning(window: WebMainWindow) -> dict:
    run_js(window, "(() => { closeQueueAddedModal?.(); requestManualPrint(); return { requested: true }; })()")
    return poll_js(
        window,
        "(() => ({ visible: !(document.getElementById('safePrintModal')?.hidden ?? true), status: document.getElementById('safePrintStatus')?.textContent || '', details: document.getElementById('safePrintDetails')?.innerText || '', controlText: document.getElementById('manualOutputControlCard')?.innerText || '' }))()",
        lambda value: value.get("visible") is True,
        timeout_ms=60000,
    )


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    result["checks"]["setup"] = setup_label_studio(window)
    render = run_render(window)
    result["checks"]["render_pdf_png"] = render
    render_payload = render.get("payload") or {}
    if not render_payload.get("ok"):
      raise RuntimeError(f"PDF/PNG render başarısız: {render}")
    result["checks"]["ready_state"] = snapshot(window)
    result["screenshots"]["ready_1920"] = save_screenshot(window, "etiket-studio-production-step3-ready-1920.png")

    invalid = run_invalid_quantity(window)
    result["checks"]["invalid_quantity"] = invalid
    if invalid.get("callbackCalled"):
        raise RuntimeError("Adet 0 iken preflight callback çalıştı; backend render'a gitmemeli.")
    result["screenshots"]["warning_1920"] = save_screenshot(window, "etiket-studio-production-step3-warning-1920.png")

    result["checks"]["quantity_restored"] = restore_quantity(window)
    queue = run_queue(window)
    result["checks"]["queue"] = queue
    result["screenshots"]["queue_1920"] = save_screenshot(window, "etiket-studio-production-step3-queue-1920.png")

    print_state = run_print_warning(window)
    result["checks"]["safe_print"] = print_state
    run_js(window, "(() => { closeSafePrintModal?.(); return { closed: true }; })()")

    window.resize(1366, 768)
    wait(700)
    run_js(window, "(() => { showSection('label'); setManualZoom('fit'); if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel(); return { ok: true }; })()")
    wait(800)
    result["checks"]["state_1366"] = snapshot(window)
    result["screenshots"]["state_1366"] = save_screenshot(window, "etiket-studio-production-step3-1366.png")

    result["status"] = "PASSED"
    return result


def main() -> int:
    suppress_message_boxes()
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.show()
    outcome: dict[str, object] = {"status": "ERROR", "message": "not started"}

    def start() -> None:
        nonlocal outcome
        try:
            outcome = run_gate(window)
        except Exception as exc:  # noqa: BLE001
            outcome = {"status": "ERROR", "message": str(exc)}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        window.close()
        app.quit()

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5200, start))
    code = app.exec()
    return 0 if code == 0 and outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
