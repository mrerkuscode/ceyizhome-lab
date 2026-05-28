from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-20" / "production_queue_flow_qa"
RESULT_PATH = OUTPUT_DIR / "production_queue_flow_qa_gate_result.json"
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
        raise RuntimeError(f"JavaScript timed out: {script[:180]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def poll_js(window: WebMainWindow, script: str, predicate, timeout_ms: int = 90000, interval_ms: int = 300):
    elapsed = 0
    last = None
    while elapsed <= timeout_ms:
        last = run_js(window, script, timeout_ms=60000)
        if predicate(last):
            return last
        wait(interval_ms)
        elapsed += interval_ms
    raise RuntimeError(f"Polling timed out. Last value: {last}")


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    wait(450)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def inject_test_helpers(window: WebMainWindow) -> None:
    run_js(window, """
    (() => {
      window.__lastAlert = "";
      window.alert = (message) => { window.__lastAlert = String(message || ""); };
      window.__queueFlowSnapshot = () => ({
        activePage: document.querySelector(".page.active")?.id || "",
        title: document.getElementById("labelStudioPageTitle")?.textContent || "",
        entryMode: window.labelStudioEntryMode || labelStudioEntryMode,
        manualText: document.getElementById("manualText")?.value || "",
        manualDateText: document.getElementById("manualDateText")?.value || "",
        manualNoteText: document.getElementById("manualNoteText")?.value || "",
        manualQty: document.getElementById("manualQty")?.value || "",
        manualLaserName: document.getElementById("manualLaserName")?.value || "",
        liveStatus: document.getElementById("manualLiveStatus")?.textContent || "",
        controlText: document.getElementById("manualOutputControlCard")?.innerText || "",
        summaryText: document.getElementById("manualProductionSummaryPanel")?.innerText || "",
        queueModalOpen: !document.getElementById("queueAddedModal")?.hidden,
        lastAlert: window.__lastAlert || "",
        outputCurrent: typeof manualOutputIsCurrent === "function" ? manualOutputIsCurrent() : false,
        queueCurrent: typeof manualQueueIsCurrent === "function" ? manualQueueIsCurrent() : false,
        queueCount: (currentState.printQueue || []).length
      });
      window.__queueRowsFor = (needle) => (currentState.printQueue || []).filter(item => {
        const history = typeof queueItemHistory === "function" ? queueItemHistory(item) : null;
        const path = typeof queueItemPath === "function" ? queueItemPath(item) : (item.relative_path || "");
        const haystack = [
          path,
          item.job_type,
          item.job_name,
          typeof queueItemSourceLabel === "function" ? queueItemSourceLabel(item) : "",
          typeof queueItemModelLabel === "function" ? queueItemModelLabel(item, history) : "",
          typeof queueItemLabelText === "function" ? queueItemLabelText(item, history) : "",
          typeof queueItemDateText === "function" ? queueItemDateText(item, history) : "",
          typeof queueItemNoteText === "function" ? queueItemNoteText(item, history) : "",
          typeof queueItemQuantity === "function" ? queueItemQuantity(item, history) : ""
        ].join(" ").toLocaleLowerCase("tr-TR");
        return haystack.includes(String(needle || "").toLocaleLowerCase("tr-TR"));
      }).map(item => {
        const history = typeof queueItemHistory === "function" ? queueItemHistory(item) : null;
        return {
          id: item.id || "",
          path: typeof queueItemPath === "function" ? queueItemPath(item) : (item.relative_path || ""),
          jobType: item.job_type || "",
          source: typeof queueItemSourceLabel === "function" ? queueItemSourceLabel(item) : (item.job_type || ""),
          model: typeof queueItemModelLabel === "function" ? queueItemModelLabel(item, history) : "",
          label: typeof queueItemLabelText === "function" ? queueItemLabelText(item, history) : "",
          date: typeof queueItemDateText === "function" ? queueItemDateText(item, history) : "",
          note: typeof queueItemNoteText === "function" ? queueItemNoteText(item, history) : "",
          quantity: typeof queueItemQuantity === "function" ? queueItemQuantity(item, history) : "",
          status: item.status || ""
        };
      });
      return { ok: true };
    })()
    """)


def setup_model(window: WebMainWindow, manual: bool) -> dict:
    action = "openManualLabelStudio()" if manual else "openLabelStudio()"
    result = run_js(window, f"""
    (() => {{
      {action};
      if (typeof setupManualLiveBindings === "function") setupManualLiveBindings();
      const target = {json.dumps(TEMPLATE_SUFFIX)};
      const normal = value => String(value || "").replace(/\\\\/g, "/");
      const model = (currentLabelModels || []).find(item => normal(item.path).endsWith(target)) || (currentLabelModels || [])[0] || null;
      if (model?.path) useModelForManual(model.path);
      {action};
      if (typeof setManualZoom === "function") setManualZoom("fit");
      if (typeof updateManualOutputControlPanel === "function") updateManualOutputControlPanel();
      return {{
        ok: Boolean(selectedLabelModel),
        title: document.getElementById("labelStudioPageTitle")?.textContent || "",
        entryMode: labelStudioEntryMode,
        modelName: selectedLabelModel?.model_name || selectedLabelModel?.title || ""
      }};
    }})()
    """, timeout_ms=60000)
    wait(1000)
    if not result.get("ok"):
        raise RuntimeError(f"Model seçimi başarısız: {result}")
    return result


def set_fields(window: WebMainWindow, name: str, date_text: str, note: str, qty: str, laser: str | None = None) -> dict:
    payload = {"name": name, "date": date_text, "note": note, "qty": qty, "laser": name if laser is None else laser}
    return run_js(window, f"""
    (() => {{
      const data = {json.dumps(payload, ensure_ascii=False)};
      const setInput = (id, value) => {{
        const el = document.getElementById(id);
        if (!el) return false;
        el.value = value;
        el.dispatchEvent(new Event("input", {{ bubbles: true }}));
        el.dispatchEvent(new Event("change", {{ bubbles: true }}));
        return true;
      }};
      window.__lastAlert = "";
      setInput("manualText", data.name);
      setInput("manualDateText", data.date);
      setInput("manualNoteText", data.note);
      setInput("manualQty", data.qty);
      setInput("manualLaserName", data.laser);
      if (typeof syncManualValuesFromInputs === "function") syncManualValuesFromInputs();
      if (typeof showManualPreviewPlaceholder === "function") showManualPreviewPlaceholder();
      if (typeof updateManualOutputControlPanel === "function") updateManualOutputControlPanel();
      return window.__queueFlowSnapshot();
    }})()
    """)


def render_manual(window: WebMainWindow, token: str) -> dict:
    run_js(window, f"""
    (() => {{
      window[{json.dumps(token + "_done")}] = false;
      window[{json.dumps(token + "_result")}] = null;
      renderManual({{
        silent: true,
        silentPreflight: false,
        skipStateRefresh: false,
        onComplete: (result, ok) => {{
          window[{json.dumps(token + "_done")}] = true;
          window[{json.dumps(token + "_result")}] = {{ ok, result, snapshot: window.__queueFlowSnapshot() }};
        }}
      }});
      return {{ started: true }};
    }})()
    """)
    return poll_js(
        window,
        f"(() => ({{ done: Boolean(window[{json.dumps(token + '_done')}]), payload: window[{json.dumps(token + '_result')}] || null }}))()",
        lambda value: value.get("done") is True,
    )


def add_to_queue(window: WebMainWindow) -> dict:
    run_js(window, """
    (() => {
      window.__queueFlowQueueStartedAt = Date.now();
      lastManualQueueResult = null;
      renderManualToQueue();
      return { started: true };
    })()
    """)
    return poll_js(
        window,
        "(() => ({ queueOk: Boolean(lastManualQueueResult), snapshot: window.__queueFlowSnapshot(), result: lastManualQueueResult || null }))()",
        lambda value: value.get("queueOk") is True,
    )


def show_queue_filtered(window: WebMainWindow, query: str) -> dict:
    result = run_js(window, f"""
    (() => {{
      if (typeof closeQueueAddedModal === "function") closeQueueAddedModal();
      showSection("printQueue");
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      const search = document.getElementById("queueSearch");
      if (search) search.value = {json.dumps(query, ensure_ascii=False)};
      if (typeof refreshPrintQueueFilters === "function") refreshPrintQueueFilters();
      const first = document.querySelector("#printQueueList .queue-job-card");
      if (first) first.scrollIntoView({{ block: "center", inline: "nearest" }});
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        rowsText: document.getElementById("printQueueList")?.innerText || "",
        detailText: document.getElementById("queueDetailInfo")?.innerText || "",
        summaryText: document.querySelector("#printQueue .queue-summary")?.innerText || "",
        renderedRows: document.querySelectorAll("#printQueueList .queue-job-card").length,
        queueRows: window.__queueRowsFor({json.dumps(query, ensure_ascii=False)})
      }};
    }})()
    """)
    wait(700)
    return result


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    window.resize(1920, 1080)
    wait(500)
    inject_test_helpers(window)

    # A) Etiket Studio source.
    outcome["checks"]["studio_setup"] = setup_model(window, manual=False)
    outcome["checks"]["studio_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "2", "Ayşe & Mehmet")
    outcome["checks"]["studio_render"] = render_manual(window, "queue_flow_studio_render")
    outcome["checks"]["studio_queue"] = add_to_queue(window)
    studio_path = (outcome["checks"]["studio_queue"].get("result") or {}).get("batch_pdf_path") or ""
    outcome["checks"]["studio_rows"] = run_js(window, f"(() => window.__queueRowsFor({json.dumps(studio_path or 'Ayşe & Mehmet', ensure_ascii=False)}))()")
    outcome["checks"]["studio_queue_view"] = show_queue_filtered(window, "Ayşe & Mehmet")
    outcome["screenshots"]["etiket_studio_source_1920"] = save_screenshot(window, "queue-flow-etiket-studio-source-1920.png")

    # B) Manuel Etiket source.
    outcome["checks"]["manual_setup"] = setup_model(window, manual=True)
    outcome["checks"]["manual_fields"] = set_fields(window, "Yağmur & Efe", "19.05.2026", "Nişan Hatırası", "1", "Yağmur & Efe")
    outcome["checks"]["manual_render"] = render_manual(window, "queue_flow_manual_render")
    outcome["checks"]["manual_queue"] = add_to_queue(window)
    manual_path = (outcome["checks"]["manual_queue"].get("result") or {}).get("batch_pdf_path") or ""
    outcome["checks"]["manual_rows"] = run_js(window, f"(() => window.__queueRowsFor({json.dumps(manual_path or 'Yağmur & Efe', ensure_ascii=False)}))()")
    outcome["checks"]["manual_queue_view"] = show_queue_filtered(window, "Yağmur & Efe")
    outcome["screenshots"]["manuel_source_1920"] = save_screenshot(window, "queue-flow-manuel-source-1920.png")

    # C) State cleanup after empty laser warning.
    setup_model(window, manual=True)
    outcome["checks"]["laser_empty_fields"] = set_fields(window, "Abdurrahman & Yağmur", "25.05.2026", "Nişan Hatırası", "2", "")
    outcome["checks"]["laser_empty_warning"] = run_js(window, "(() => { prepareManualLaserTransfer(); return window.__queueFlowSnapshot(); })()")
    outcome["checks"]["laser_recovered_fields"] = set_fields(window, "Abdurrahman & Yağmur", "25.05.2026", "Nişan Hatırası", "2", "Abdurrahman & Yağmur")
    outcome["checks"]["laser_recovered_render"] = render_manual(window, "queue_flow_laser_recovered")
    outcome["checks"]["laser_recovered_queue"] = add_to_queue(window)
    outcome["checks"]["laser_recovered_snapshot"] = run_js(window, "(() => window.__queueFlowSnapshot())()")
    show_queue_filtered(window, "Abdurrahman")
    outcome["screenshots"]["state_cleanup_1920"] = save_screenshot(window, "queue-flow-state-cleanup-1920.png")

    # D) Quantity 0 recovery.
    setup_model(window, manual=True)
    outcome["checks"]["qty_zero_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "0", "Ayşe & Mehmet")
    outcome["checks"]["qty_zero_render"] = render_manual(window, "queue_flow_qty_zero")
    outcome["checks"]["qty_recovered_fields"] = set_fields(window, "Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "2", "Ayşe & Mehmet")
    outcome["checks"]["qty_recovered_render"] = render_manual(window, "queue_flow_qty_recovered")
    outcome["checks"]["qty_recovered_queue"] = add_to_queue(window)
    outcome["checks"]["qty_recovered_snapshot"] = run_js(window, "(() => window.__queueFlowSnapshot())()")

    # E) Existing Yazdırma Sırası view and 1366.
    outcome["checks"]["existing_print_queue_view"] = show_queue_filtered(window, "")
    outcome["screenshots"]["existing_yazdirma_sirasi_1920"] = save_screenshot(window, "queue-flow-existing-yazdirma-sirasi-1920.png")
    window.resize(1366, 768)
    wait(900)
    outcome["checks"]["state_1366"] = show_queue_filtered(window, "Yağmur")
    outcome["screenshots"]["state_1366"] = save_screenshot(window, "queue-flow-1366.png")

    # Assertions kept after screenshots so failures still leave visual evidence where possible.
    studio_rows = outcome["checks"]["studio_rows"]
    manual_rows = outcome["checks"]["manual_rows"]
    if not studio_rows or "Etiket Studio" not in studio_rows[0].get("source", ""):
        raise AssertionError(f"Etiket Studio queue kaynağı ayrışmadı: {studio_rows}")
    if not manual_rows or "Manuel Etiket" not in manual_rows[0].get("source", ""):
        raise AssertionError(f"Manuel Etiket queue kaynağı ayrışmadı: {manual_rows}")
    if "Yazıcı otomatik" not in outcome["checks"]["studio_queue"].get("snapshot", {}).get("summaryText", ""):
        raise AssertionError("Queue sonrası yazıcı güvenlik notu görünmüyor.")
    laser_snapshot = outcome["checks"]["laser_recovered_snapshot"]
    laser_text = f"{laser_snapshot.get('liveStatus', '')} {laser_snapshot.get('summaryText', '')} {laser_snapshot.get('lastAlert', '')}"
    if "Lazer isim boş" in laser_text:
        raise AssertionError(f"Lazer isim boş uyarısı dolu senaryoya taşındı: {laser_snapshot}")
    qty_snapshot = outcome["checks"]["qty_recovered_snapshot"]
    qty_text = f"{qty_snapshot.get('liveStatus', '')} {qty_snapshot.get('summaryText', '')} {qty_snapshot.get('lastAlert', '')}"
    if "Adet en az 1" in qty_text:
        raise AssertionError(f"Adet 0 uyarısı toparlanma sonrası kaldı: {qty_snapshot}")
    if "PDF/PNG henüz hazırlanmadı" in str(outcome["checks"]["manual_queue"].get("snapshot", {}).get("summaryText", "")):
        raise AssertionError("Queue sonrası çelişkili PDF/PNG hazırlanmadı metni kaldı.")

    outcome["status"] = "PASSED"
    return outcome


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
            outcome = {**outcome, "status": "ERROR", "message": str(exc)}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=True, indent=2))
        window.close()
        window.deleteLater()
        QTimer.singleShot(0, app.quit)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5200, start))
    QTimer.singleShot(240000, app.quit)
    code = app.exec()
    return 0 if code == 0 and outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
