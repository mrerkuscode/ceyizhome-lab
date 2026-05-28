from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-20" / "production_manuel_etiket_step1"
RESULT_PATH = OUTPUT_DIR / "production_manuel_etiket_step1_gate_result.json"
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
        raise RuntimeError(f"Screenshot could not be saved: {path}")
    return str(path)


def setup_manual_label(window: WebMainWindow) -> dict:
    result = run_js(window, f"""
    (() => {{
      if (typeof openManualLabelStudio === 'function') openManualLabelStudio();
      else showSection('label');
      if (typeof setupManualLiveBindings === 'function') setupManualLiveBindings();
      const target = {json.dumps(TEMPLATE_SUFFIX)};
      const normal = value => String(value || '').replace(/\\\\/g, '/');
      const model = (currentLabelModels || []).find(item => normal(item.path).endsWith(target)) || (currentLabelModels || [])[0] || null;
      if (model?.path) useModelForManual(model.path);
      if (typeof openManualLabelStudio === 'function') openManualLabelStudio();
      if (typeof setManualZoom === 'function') setManualZoom('fit');
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return {{
        ok: Boolean(selectedLabelModel),
        title: document.getElementById('labelStudioPageTitle')?.textContent || '',
        entryMode: labelStudioEntryMode,
        manualClass: document.getElementById('label')?.classList.contains('manual-entry-mode') || false,
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
        summaryVisible: getComputedStyle(document.getElementById('manualProductionSummaryPanel')).display !== 'none'
      }};
    }})()
    """, timeout_ms=60000)
    wait(1200)
    if not result.get("ok"):
        raise RuntimeError(f"Manual model setup failed: {result}")
    return result


def set_fields(window: WebMainWindow, name: str, date: str, note: str, qty: str = "2", laser: str | None = None) -> dict:
    return run_js(window, f"""
    (() => {{
      const data = {json.dumps({"name": name, "date": date, "note": note, "qty": qty, "laser": laser if laser is not None else name}, ensure_ascii=False)};
      const setInput = (id, value) => {{
        const el = document.getElementById(id);
        if (!el) return false;
        el.value = value;
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return true;
      }};
      setInput('manualText', data.name);
      setInput('manualDateText', data.date);
      setInput('manualNoteText', data.note);
      setInput('manualQty', data.qty);
      setInput('manualLaserName', data.laser);
      if (typeof syncManualValuesFromInputs === 'function') syncManualValuesFromInputs();
      if (typeof showManualPreviewPlaceholder === 'function') showManualPreviewPlaceholder();
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return snapshotManualStep1();
    }})()
    """)


def inject_snapshot_helper(window: WebMainWindow) -> None:
    run_js(window, """
    (() => {
      window.__lastAlert = '';
      window.alert = (message) => { window.__lastAlert = String(message || ''); };
      window.snapshotManualStep1 = () => ({
        title: document.getElementById('labelStudioPageTitle')?.textContent || '',
        entryMode: labelStudioEntryMode,
        activeManualNav: document.querySelector('.nav-btn[data-page="manualLabel"]')?.classList.contains('active') || false,
        manualText: document.getElementById('manualText')?.value || '',
        manualDateText: document.getElementById('manualDateText')?.value || '',
        manualNoteText: document.getElementById('manualNoteText')?.value || '',
        manualQty: document.getElementById('manualQty')?.value || '',
        manualLaserName: document.getElementById('manualLaserName')?.value || '',
        badge: document.getElementById('manualOutputControlBadge')?.textContent || '',
        summaryText: document.getElementById('manualProductionSummaryPanel')?.innerText || '',
        controlText: document.getElementById('manualOutputControlCard')?.innerText || '',
        previewHasModelSelectText: (document.getElementById('manualPreview')?.innerText || '').includes('Model seçin'),
        labelBoxText: [...document.querySelectorAll('#manualPreview .field-box.text-layer')].map(box => box.querySelector('span')?.textContent || ''),
        lastOutputOk: Boolean(lastManualOutput),
        queueOk: Boolean(lastManualQueueResult),
        liveStatus: document.getElementById('manualLiveStatus')?.textContent || '',
        lastAlert: window.__lastAlert || ''
      });
      return { ok: true };
    })()
    """)


def render_manual(window: WebMainWindow, token: str) -> dict:
    run_js(window, f"""
    (() => {{
      window[{json.dumps(token + '_done')}] = false;
      window[{json.dumps(token + '_result')}] = null;
      renderManual({{
        silent: true,
        silentPreflight: false,
        skipStateRefresh: false,
        onComplete: (result, ok) => {{
          window[{json.dumps(token + '_done')}] = true;
          window[{json.dumps(token + '_result')}] = {{ ok, result, snapshot: snapshotManualStep1() }};
        }}
      }});
      return {{ started: true }};
    }})()
    """)
    return poll_js(
        window,
        f"(() => ({{ done: Boolean(window[{json.dumps(token + '_done')}]), payload: window[{json.dumps(token + '_result')}] || null }}))()",
        lambda value: value.get("done") is True,
        timeout_ms=90000,
    )


def add_to_queue(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      lastManualQueueResult = null;
      renderManualToQueue();
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ queueOk: Boolean(lastManualQueueResult), snapshot: snapshotManualStep1() }))()",
        lambda value: value.get("queueOk") is True,
        timeout_ms=90000,
    )


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    inject_snapshot_helper(window)
    result["checks"]["setup"] = setup_manual_label(window)

    result["checks"]["ayse_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "2")
    result["checks"]["ayse_render"] = render_manual(window, "manual_step1_ayse")
    result["screenshots"]["state_1920"] = save_screenshot(window, "manuel-etiket-production-step1-1920.png")

    result["checks"]["warning_fields"] = set_fields(window, "Mustafa Kemal & Yağmur", "25.05.2026", "İsim Hatırası", "2")
    result["checks"]["warning_render"] = render_manual(window, "manual_step1_warning")
    result["screenshots"]["warning_1920"] = save_screenshot(window, "manuel-etiket-production-step1-warning-1920.png")

    result["checks"]["quantity_zero_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "0")
    result["checks"]["quantity_zero_render"] = render_manual(window, "manual_step1_qty0")

    result["checks"]["laser_empty"] = set_fields(window, "Abdurrahman & Yağmur", "25.05.2026", "Nişan Hatırası", "2", "")
    run_js(window, "(() => { prepareManualLaserTransfer(); return snapshotManualStep1(); })()")
    result["checks"]["laser_empty_snapshot"] = run_js(window, "(() => snapshotManualStep1())()")

    result["checks"]["queue_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "2")
    result["checks"]["queue_result"] = add_to_queue(window)
    result["screenshots"]["queue_1920"] = save_screenshot(window, "manuel-etiket-production-step1-queue-1920.png")

    window.resize(1366, 768)
    wait(900)
    run_js(window, "(() => { if (typeof closeQueueAddedModal === 'function') closeQueueAddedModal(); openManualLabelStudio(); setManualZoom('fit'); updateManualOutputControlPanel(); return snapshotManualStep1(); })()")
    wait(700)
    result["checks"]["state_1366"] = run_js(window, "(() => snapshotManualStep1())()")
    result["screenshots"]["state_1366"] = save_screenshot(window, "manuel-etiket-production-step1-1366.png")

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
