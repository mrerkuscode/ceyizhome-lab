from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-20" / "production_etiket_studio_step2_runtime_test"
RESULT_PATH = OUTPUT_DIR / "production_etiket_studio_step2_runtime_gate_result.json"
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
      if (typeof scheduleFieldOverlaySync === 'function') scheduleFieldOverlaySync();
      if (typeof renderStudioOrderPanels === 'function') renderStudioOrderPanels();
      return {{
        ok: Boolean(selectedLabelModel),
        modelCount: (currentLabelModels || []).length,
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
        modelPath: selectedLabelModel?.path || '',
        selectedModelButton: document.getElementById('manualSelectedModelName')?.textContent || '',
        previewText: document.getElementById('manualPreview')?.innerText || '',
        saveState: document.getElementById('corelSaveState')?.textContent || '',
        fieldCount: (selectedLabelModel?.fields_summary || []).length
      }};
    }})()
    """, timeout_ms=60000)
    wait(1200)
    if not result.get("ok"):
        raise RuntimeError(f"Model seçimi başarısız: {result}")
    return result


def snapshot_label_state(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const inputValue = id => document.getElementById(id)?.value || '';
      const preview = document.getElementById('manualPreview');
      const boxes = [...document.querySelectorAll('#manualPreview .field-box.text-layer')].map(box => ({
        hidden: box.hidden,
        text: box.querySelector('span')?.textContent || '',
        column: (selectedLabelModel?.fields_summary || [])[Number(box.dataset.fieldIndex || -1)]?.excel_column || '',
        className: String(box.className || '')
      }));
      const duplicateInputIds = [...document.querySelectorAll('#label input[id]')]
        .map(input => input.id)
        .filter((id, index, ids) => ids.indexOf(id) !== index);
      return {
        activeSection: document.querySelector('.page.active')?.id || '',
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
        modelPath: selectedLabelModel?.path || '',
        previewHasModelSelectText: (preview?.innerText || '').includes('Model seçin'),
        previewText: preview?.innerText || '',
        manualText: inputValue('manualText'),
        manualDateText: inputValue('manualDateText'),
        manualNoteText: inputValue('manualNoteText'),
        manualQty: inputValue('manualQty'),
        manualLaserName: inputValue('manualLaserName'),
        payload: typeof manualPayload === 'function' ? manualPayload() : {},
        visibleTextBoxes: boxes.filter(box => !box.hidden),
        duplicateInputIds,
        saveState: document.getElementById('corelSaveState')?.textContent || '',
        liveStatus: document.getElementById('manualLiveStatus')?.textContent || '',
        outputActionsHidden: document.getElementById('manualOutputActions')?.hidden ?? null,
        outputActionsText: document.getElementById('manualOutputActions')?.innerText || '',
        preflightText: document.getElementById('manualPreflightStatus')?.innerText || '',
        safePrintVisible: !(document.getElementById('safePrintModal')?.hidden ?? true),
        safePrintStatus: document.getElementById('safePrintStatus')?.textContent || '',
        queueAddedVisible: !(document.getElementById('queueAddedModal')?.hidden ?? true),
        queueAddedText: document.getElementById('queueAddedText')?.textContent || '',
        zoomLabel: document.getElementById('manualZoomLabel')?.textContent || ''
      };
    })()
    """)


def run_render(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      window.__step2RenderDone = false;
      window.__step2RenderResult = null;
      renderManual({
        silent: true,
        silentPreflight: true,
        skipStateRefresh: false,
        onComplete: (result, ok) => {
          window.__step2RenderDone = true;
          window.__step2RenderResult = { ok, result };
        }
      });
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ done: Boolean(window.__step2RenderDone), payload: window.__step2RenderResult || null }))()",
        lambda value: value.get("done") is True,
        timeout_ms=90000,
    )


def run_queue(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      window.__step2QueueModalBefore = !(document.getElementById('queueAddedModal')?.hidden ?? true);
      renderManualToQueue();
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ visible: !(document.getElementById('queueAddedModal')?.hidden ?? true), text: document.getElementById('queueAddedText')?.textContent || '', file: document.getElementById('queueAddedFile')?.textContent || '' }))()",
        lambda value: value.get("visible") is True or "eklenemedi" in str(value.get("text", "")).lower(),
        timeout_ms=90000,
    )


def run_interaction_checks(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const before = selectedLabelModel?.fields_summary?.[selectedFieldIndex] ? { ...selectedLabelModel.fields_summary[selectedFieldIndex] } : null;
      if (typeof setManualZoom === 'function') setManualZoom('150');
      if (typeof applyColorSwatch === 'function') applyColorSwatch('#991b1b');
      const font = document.getElementById('corelFontFamily');
      if (font) {
        font.value = 'Georgia';
        if (typeof corelApplyTypography === 'function') corelApplyTypography();
      }
      const target = document.querySelector('.field-box.selected') || document.querySelector('.field-box[data-field-index="0"]');
      target?.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true }));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
      const after = selectedLabelModel?.fields_summary?.[selectedFieldIndex] ? { ...selectedLabelModel.fields_summary[selectedFieldIndex] } : null;
      return {
        zoomLabel: document.getElementById('manualZoomLabel')?.textContent || '',
        color: document.getElementById('corelColor')?.value || '',
        before,
        after,
        selectedFieldIndex,
        undoLength: manualUndoStack?.length || 0,
        redoLength: manualRedoStack?.length || 0
      };
    })()
    """)


def run_invalid_quantity_check(window: WebMainWindow) -> dict:
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
      const panelText = document.getElementById('manualPreflightStatus')?.innerText || '';
      qty.value = '2';
      qty.dispatchEvent(new Event('input', { bubbles: true }));
      return { callbackCalled, errorResult, panelText, qty: qty.value };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    model_result = setup_label_studio(window)
    result["checks"]["model_selection"] = model_result
    state_1920 = snapshot_label_state(window)
    result["checks"]["state_1920"] = state_1920
    result["screenshots"]["model_selected_1920"] = save_screenshot(window, "etiket-studio-production-step2-model-selected-1920.png")

    interaction = run_interaction_checks(window)
    result["checks"]["canvas_interaction"] = interaction
    result["screenshots"]["right_panel_1920"] = save_screenshot(window, "etiket-studio-production-step2-right-panel-1920.png")

    invalid_qty = run_invalid_quantity_check(window)
    result["checks"]["invalid_quantity"] = invalid_qty

    render = run_render(window)
    result["checks"]["render_pdf_png"] = render
    render_payload = render.get("payload") or {}
    if not render_payload.get("ok"):
        raise RuntimeError(f"PDF/PNG render başarısız: {render}")
    render_result = render_payload.get("result") or {}
    if not render_result.get("batch_pdf_path") and not render_result.get("pdf_path"):
        raise RuntimeError(f"PDF yolu dönmedi: {render_result}")
    if not render_result.get("png_path"):
        raise RuntimeError(f"PNG yolu dönmedi: {render_result}")

    queue = run_queue(window)
    result["checks"]["queue"] = queue

    run_js(window, "(() => { closeQueueAddedModal?.(); requestManualPrint(); return { requested: true }; })()")
    print_state = poll_js(
        window,
        "(() => ({ visible: !(document.getElementById('safePrintModal')?.hidden ?? true), status: document.getElementById('safePrintStatus')?.textContent || '', details: document.getElementById('safePrintDetails')?.innerText || '' }))()",
        lambda value: value.get("visible") is True,
        timeout_ms=60000,
    )
    result["checks"]["safe_print"] = print_state
    result["screenshots"]["print_warning_1920"] = save_screenshot(window, "etiket-studio-production-step2-print-warning-1920.png")
    run_js(window, "(() => { closeSafePrintModal?.(); return { closed: true }; })()")

    window.resize(1366, 768)
    wait(700)
    run_js(window, "(() => { showSection('label'); setManualZoom('fit'); return { ok: true }; })()")
    wait(800)
    state_1366 = snapshot_label_state(window)
    result["checks"]["state_1366"] = state_1366
    result["screenshots"]["model_selected_1366"] = save_screenshot(window, "etiket-studio-production-step2-model-selected-1366.png")

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
