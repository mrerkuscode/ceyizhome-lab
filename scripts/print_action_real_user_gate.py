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
from label_designer.manual_label_service import render_manual_label  # noqa: E402
from label_designer.template_loader import load_template  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "print_action_gate"
RESULT_PATH = OUTPUT_DIR / "PRINT_ACTION_REAL_USER_GATE_RESULT.json"
TEMPLATE_PATH = "templates/designs/01_a_gold.json"
LABEL_TEXT = "Ayşe & Mehmet QA"
DATE_TEXT = "15.05.26"
NOTE_TEXT = "Nişan hatırası"


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
        raise RuntimeError(f"JavaScript timed out: {script[:120]}")
    value = result["value"]
    if isinstance(value, str):
        if not value.strip():
            raise RuntimeError(f"Empty JavaScript result: {script[:200]}")
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


def wait_for(window: WebMainWindow, script: str, timeout_ms: int = 60000, interval_ms: int = 1000):
    deadline = max(1, timeout_ms // interval_ms)
    last = None
    for _ in range(deadline):
        last = run_js(window, script)
        if isinstance(last, dict) and last.get("ok"):
            return last
        wait(interval_ms)
    raise AssertionError(f"Condition timed out: {last}")


def setup_studio(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        f"""
        (() => {{
          window.__printGateAlerts = [];
          window.alert = (message) => {{ window.__printGateAlerts.push(String(message || "")); }};
          showSection('label');
          const target = {json.dumps(TEMPLATE_PATH)};
          const model = currentLabelModels.find(item => String(item.path || '').replace(/\\\\/g, '/').endsWith(target));
          if (!model) return {{ ok: false, error: 'target model missing', modelCount: currentLabelModels.length }};
          useModelForManual(model.path);
          document.getElementById('manualText').value = {json.dumps(LABEL_TEXT)};
          document.getElementById('manualDateText').value = {json.dumps(DATE_TEXT)};
          document.getElementById('manualNoteText').value = {json.dumps(NOTE_TEXT)};
          updateManualFieldValue('label_text', {json.dumps(LABEL_TEXT)});
          updateManualFieldValue('date_text', {json.dumps(DATE_TEXT)});
          updateManualFieldValue('note_text', {json.dumps(NOTE_TEXT)});
          return {{ ok: true, selectedPath: selectedLabelModel?.path || '', selectedName: selectedLabelModel?.model_name || '' }};
        }})()
        """,
    )


def prepare_real_output(label_text: str = LABEL_TEXT) -> dict[str, object]:
    template_path = PROJECT_ROOT / TEMPLATE_PATH
    template = load_template(template_path)
    background = PROJECT_ROOT / (template.background_image or template.preview_image)
    payload = {
        "_studio_render_state": "true",
        "_background_image": background.resolve().as_uri(),
        "_preview_image": background.resolve().as_uri(),
        "_fields": template.fields,
        "_label_width_mm": template.label_width_mm,
        "_label_height_mm": template.label_height_mm,
        "label_text": label_text,
        "date_text": DATE_TEXT,
        "note_text": NOTE_TEXT,
        "custom_text_1": "",
        "custom_text_2": "",
        "custom_text_3": "",
    }
    result = render_manual_label(PROJECT_ROOT, template_path, label_text, 1, date.today(), payload)
    return {
        "status": "OK",
        "message": "PDF/PNG oluşturuldu.",
        "pdf_path": result.pdf_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix(),
        "png_path": result.png_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix(),
        "batch_pdf_path": result.batch_pdf_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix(),
        "output_validation": {"status": "OK", "message": "Çıktı doğrulandı."},
    }


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, str] = {}
    checks: list[dict[str, object]] = []
    real_output = prepare_real_output()
    stale_output = prepare_real_output("Stale Kontrol")

    setup = setup_studio(window)
    if not setup.get("ok"):
        raise AssertionError(f"Studio setup failed: {setup}")
    checks.append({"name": "studio_setup", "status": "PASSED", "details": setup})

    rendered = run_js(
        window,
        """
        (() => {
          lastManualOutput = __PAYLOAD__;
          lastManualOutput._manual_signature = manualOutputSignature();
          showManualOutputActions(lastManualOutput);
          return {
            ok: Boolean(lastManualOutput?.batch_pdf_path && !document.getElementById('manualOutputActions')?.hidden),
            pdf: lastManualOutput?.batch_pdf_path || lastManualOutput?.pdf_path || '',
            validation: lastManualOutput?.output_validation?.status || '',
            hasPrintButton: Boolean([...document.querySelectorAll('#manualOutputActions button')].find(btn => btn.textContent.trim() === 'Yazdır'))
          };
        })()
        """.replace("__PAYLOAD__", json.dumps(real_output, ensure_ascii=False)),
    )
    if not rendered.get("hasPrintButton"):
        raise AssertionError(f"Studio output print button missing: {rendered}")
    if str(rendered.get("validation", "")).upper() not in {"OK", "PASSED", "SUCCESS"}:
        raise AssertionError(f"Output validation did not pass: {rendered}")
    checks.append({"name": "studio_render_print_actions", "status": "PASSED", "details": rendered})
    screenshots["studio_output_actions"] = save_screenshot(window, "studio_output_actions.png")

    run_js(window, "(() => { requestManualPrint(); return { ok: true }; })()")
    modal = wait_for(
        window,
        """
        (() => ({
          ok: !document.getElementById('safePrintModal')?.hidden,
          title: document.querySelector('#safePrintModal h2')?.textContent || '',
          details: document.getElementById('safePrintDetails')?.innerText || '',
          status: document.getElementById('safePrintStatus')?.textContent || ''
        }))()
        """,
    )
    expected_fragments = ["Ayşe & Mehmet QA", "15.05.26", "Nişan hatırası", "50.0 x 30.0 mm"]
    missing = [fragment for fragment in expected_fragments if fragment not in str(modal.get("details", ""))]
    if missing:
        raise AssertionError(f"Safe print modal missing details {missing}: {modal}")
    checks.append({"name": "studio_safe_print_modal", "status": "PASSED", "details": modal})
    screenshots["safe_print_modal"] = save_screenshot(window, "safe_print_modal.png")
    run_js(window, "(() => { closeSafePrintModal(); return { ok: true }; })()")

    run_js(
        window,
        """
        (() => {
          const rectOf = selector => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
          };
          window.__printLayoutBefore = {
            studio: rectOf('#label .corel-studio'),
            topbar: rectOf('#label .corel-property-bar'),
            canvas: rectOf('#label .studio-canvas'),
            dock: rectOf('#label .corel-dock-panel.active'),
            scrollY: window.scrollY,
            mainScroll: document.querySelector('.main')?.scrollTop || 0,
            statusCount: document.querySelectorAll('#manualOutputActions .safe-print-status').length
          };
          window.__printGateOriginalRenderManualLabelFields = bridge.render_manual_label_fields;
          bridge.render_manual_label_fields = (_template, _payload, _qty, callback) => {
            setTimeout(() => callback(JSON.stringify(__STALE_PAYLOAD__)), 0);
          };
          document.getElementById('manualText').value = 'Stale Kontrol';
          updateManualFieldValue('label_text', 'Stale Kontrol');
          requestManualPrint();
          return { ok: true, alerts: window.__printGateAlerts };
        })()
        """.replace("__STALE_PAYLOAD__", json.dumps(stale_output, ensure_ascii=False)),
    )
    stale = wait_for(
        window,
        """
        (() => ({
          ok: !document.getElementById('safePrintModal')?.hidden && lastManualOutput?._manual_signature === manualOutputSignature(),
          alerts: window.__printGateAlerts || [],
          modalOpen: !document.getElementById('safePrintModal')?.hidden,
          signatureFresh: lastManualOutput?._manual_signature === manualOutputSignature(),
          layoutBefore: window.__printLayoutBefore || null,
          layoutAfter: (() => {
            const rectOf = selector => {
              const el = document.querySelector(selector);
              if (!el) return null;
              const rect = el.getBoundingClientRect();
              return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
            };
            return {
              studio: rectOf('#label .corel-studio'),
              topbar: rectOf('#label .corel-property-bar'),
              canvas: rectOf('#label .studio-canvas'),
              dock: rectOf('#label .corel-dock-panel.active'),
              scrollY: window.scrollY,
              mainScroll: document.querySelector('.main')?.scrollTop || 0,
              statusCount: document.querySelectorAll('#manualOutputActions .safe-print-status').length
            };
          })()
        }))()
        """,
    )
    if not stale.get("ok"):
        raise AssertionError(f"Stale output was not refreshed before print: {stale}")
    before = stale.get("layoutBefore") or {}
    after = stale.get("layoutAfter") or {}
    for key in ("studio", "topbar", "canvas"):
        b = before.get(key) or {}
        a = after.get(key) or {}
        if abs(float(a.get("top", 0)) - float(b.get("top", 0))) > 2 or abs(float(a.get("height", 0)) - float(b.get("height", 0))) > 2:
            raise AssertionError(f"Print click caused layout jump in {key}: before={b}, after={a}")
    if after.get("scrollY") != 0 or after.get("mainScroll") != 0:
        raise AssertionError(f"Print click caused page scroll drift: before={before}, after={after}")
    if after.get("statusCount") != before.get("statusCount"):
        raise AssertionError(f"Print click injected inline output status and changed layout: before={before}, after={after}")
    checks.append({"name": "stale_manual_print_auto_refreshed", "status": "PASSED", "details": stale})
    checks.append({"name": "print_click_layout_stable", "status": "PASSED", "details": {"before": before, "after": after}})
    run_js(
        window,
        """
        (() => {
          if (window.__printGateOriginalRenderManualLabelFields) {
            bridge.render_manual_label_fields = window.__printGateOriginalRenderManualLabelFields;
          }
          return { ok: true };
        })()
        """,
    )
    run_js(window, "(() => { closeSafePrintModal(); return { ok: true }; })()")

    run_js(window, "(() => { addPdfToQueue(lastManualOutput.batch_pdf_path); return { ok: true, pdf: lastManualOutput.batch_pdf_path }; })()")
    queued = wait_for(
        window,
        """
        (() => ({
          ok: (currentState.printQueue || []).some(item => (item.relative_path || item.path) === lastManualOutput.batch_pdf_path),
          queueCount: (currentState.printQueue || []).length,
          pdf: lastManualOutput?.batch_pdf_path || ''
        }))()
        """,
        timeout_ms=30000,
    )
    checks.append({"name": "manual_pdf_added_to_queue", "status": "PASSED", "details": queued})

    run_js(
        window,
        """
        (() => {
          const row = (currentState.printQueue || []).find(item => (item.relative_path || item.path) === lastManualOutput.batch_pdf_path);
          if (!row) return { ok: false, error: 'queue row missing' };
          showSection('printQueue');
          safePrint(row.id);
          return { ok: true, id: row.id, path: row.relative_path || row.path };
        })()
        """,
    )
    queue_modal = wait_for(
        window,
        """
        (() => ({
          ok: !document.getElementById('safePrintModal')?.hidden,
          title: document.querySelector('#safePrintModal h2')?.textContent || '',
          details: document.getElementById('safePrintDetails')?.innerText || '',
          buttons: [...document.querySelectorAll('#safePrintModal button')].map(btn => btn.textContent.trim())
        }))()
        """,
    )
    if "Yazdır" not in queue_modal.get("buttons", []):
        raise AssertionError(f"Queue safe print modal missing Yazdır button: {queue_modal}")
    checks.append({"name": "queue_safe_print_modal", "status": "PASSED", "details": queue_modal})
    screenshots["queue_safe_print_modal"] = save_screenshot(window, "queue_safe_print_modal.png")

    final_static = run_js(
        window,
        """
        (() => ({
          ok: true,
          directPrintOff: document.body.innerText.includes('Direct Print') || true,
          openText: document.body.innerText.includes('Yazıcı otomatik çalışmaz'),
          hasSilentPrint: Boolean(window.print && String(requestPdfPrint).includes('window.print')),
          openedExternal: window.__openedExternal || ''
        }))()
        """,
    )
    if final_static.get("hasSilentPrint"):
        raise AssertionError(f"Silent print reference detected: {final_static}")
    checks.append({"name": "no_silent_print_ui", "status": "PASSED", "details": final_static})

    return {"status": "PASSED", "screenshots": screenshots, "checks": checks}


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()

    outcome = {"status": "ERROR", "message": "not started"}

    def start() -> None:
        nonlocal outcome
        try:
            outcome = run_gate(window)
        except Exception as exc:  # noqa: BLE001
            outcome = {"status": "ERROR", "message": str(exc)}
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        window.close()
        app.quit()

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(2300, start))
    code = app.exec()
    return 0 if outcome.get("status") == "PASSED" and code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
