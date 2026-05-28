from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-20" / "production_etiket_studio_step4_model_tuning"
RESULT_PATH = OUTPUT_DIR / "production_etiket_studio_step4_model_tuning_gate_result.json"
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
      if (typeof setManualZoom === 'function') setManualZoom('fit');
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      return {{
        ok: Boolean(selectedLabelModel),
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
        fields: (selectedLabelModel?.fields_summary || []).map(field => ({{ column: field.excel_column, x: field.x_mm, y: field.y_mm, width: field.width_mm, height: field.height_mm, font: field.font_size }}))
      }};
    }})()
    """, timeout_ms=60000)
    wait(1200)
    if not result.get("ok"):
        raise RuntimeError(f"Model seçimi başarısız: {result}")
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
      if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel();
      if (typeof showManualPreviewPlaceholder === 'function') showManualPreviewPlaceholder();
      return {{
        manualText: document.getElementById('manualText')?.value || '',
        manualDateText: document.getElementById('manualDateText')?.value || '',
        manualNoteText: document.getElementById('manualNoteText')?.value || '',
        manualQty: document.getElementById('manualQty')?.value || '',
        manualLaserName: document.getElementById('manualLaserName')?.value || '',
        badge: document.getElementById('manualOutputControlBadge')?.textContent || ''
      }};
    }})()
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
          window[{json.dumps(token + '_result')}] = {{ ok, result, controlText: document.getElementById('manualOutputControlCard')?.innerText || '' }};
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


def snapshot(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => ({
      modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
      manualText: document.getElementById('manualText')?.value || '',
      manualDateText: document.getElementById('manualDateText')?.value || '',
      manualNoteText: document.getElementById('manualNoteText')?.value || '',
      badge: document.getElementById('manualOutputControlBadge')?.textContent || '',
      controlText: document.getElementById('manualOutputControlCard')?.innerText || '',
      preflightText: document.getElementById('manualPreflightStatus')?.innerText || '',
      previewHasModelSelectText: (document.getElementById('manualPreview')?.innerText || '').includes('Model seçin'),
      labelBoxText: [...document.querySelectorAll('#manualPreview .field-box.text-layer')].map(box => box.querySelector('span')?.textContent || '')
    }))()
    """)


def preflight_status(render_result: dict) -> str:
    payload = render_result.get("payload") or {}
    result = payload.get("result") or {}
    return (result.get("preflight") or {}).get("status", "")


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    result["checks"]["setup"] = setup_label_studio(window)

    result["checks"]["ayse_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası")
    ayse_render = render_manual(window, "step4_ayse")
    result["checks"]["ayse_render"] = ayse_render
    result["checks"]["ayse_snapshot"] = snapshot(window)
    result["screenshots"]["ayse_mehmet_1920"] = save_screenshot(window, "etiket-studio-step4-ayse-mehmet-1920.png")

    result["checks"]["long_fields"] = set_fields(window, "Abdurrahman & Yağmur", "25.05.2026", "Nişan Hatırası")
    long_render = render_manual(window, "step4_long")
    result["checks"]["long_render"] = long_render
    result["checks"]["long_snapshot"] = snapshot(window)
    result["screenshots"]["uzun_isim_1920"] = save_screenshot(window, "etiket-studio-step4-uzun-isim-1920.png")

    result["checks"]["longer_fields"] = set_fields(window, "Mustafa Kemal & Yağmur", "25.05.2026", "İsim Hatırası")
    longer_render = render_manual(window, "step4_longer")
    result["checks"]["longer_render"] = longer_render
    result["checks"]["control_panel_snapshot"] = snapshot(window)
    result["screenshots"]["control_panel_1920"] = save_screenshot(window, "etiket-studio-step4-control-panel-1920.png")

    result["checks"]["preflight_summary"] = {
        "ayse": preflight_status(ayse_render),
        "abdurrahman": preflight_status(long_render),
        "mustafa": preflight_status(longer_render),
    }

    window.resize(1366, 768)
    wait(800)
    run_js(window, "(() => { showSection('label'); setManualZoom('fit'); if (typeof updateManualOutputControlPanel === 'function') updateManualOutputControlPanel(); return { ok: true }; })()")
    wait(800)
    result["checks"]["state_1366"] = snapshot(window)
    result["screenshots"]["state_1366"] = save_screenshot(window, "etiket-studio-step4-1366.png")

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
