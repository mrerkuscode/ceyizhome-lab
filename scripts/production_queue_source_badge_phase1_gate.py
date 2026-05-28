from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_queue_source_badge_phase1"
RESULT_PATH = OUTPUT_DIR / "production_queue_source_badge_phase1_gate_result.json"

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


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    wait(650)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def open_print_queue(window: WebMainWindow) -> dict:
    result = run_js(window, """
    (() => {
      showSection("printQueue");
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        rows: document.querySelectorAll("#printQueueList .queue-job-card").length,
        badges: Array.from(document.querySelectorAll("#printQueueList .source-badge")).map(node => ({
          text: node.textContent.trim(),
          className: node.className,
          title: node.getAttribute("title") || ""
        })),
        detailSource: document.querySelector("#queueDetailInfo .source-badge")?.textContent.trim() || "",
        safeNote: document.querySelector("#queueDetailStatus")?.innerText || ""
      };
    })()
    """)
    wait(800)
    if result.get("activePage") != "printQueue":
        raise RuntimeError(f"Yazdırma Sırası açılamadı: {result}")
    return result


def ensure_visual_rows(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const rows = currentState.printQueue || [];
      const hasStudio = rows.some(item => item.source === "etiket_studio" || item.source_label === "Etiket Studio");
      const hasManual = rows.some(item => item.source === "manual_label" || item.source_label === "Manuel Etiket");
      const visualRows = [];
      if (!hasStudio) {
        visualRows.push({
          id: "qa-source-badge-studio",
          created_at: "2026-05-21 09:00:00",
          job_name: "01 A Gold Rulo Etiket",
          job_type: "Manuel",
          source: "etiket_studio",
          source_label: "Etiket Studio",
          quantity: "2",
          file_type: "PDF",
          relative_path: "output/2026-05-21/qa/etiket_studio_ayse_mehmet.pdf",
          status: "Beklemede",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Ayşe & Mehmet",
          size_text: "50 x 30 mm"
        });
      }
      if (!hasManual) {
        visualRows.push({
          id: "qa-source-badge-manual",
          created_at: "2026-05-21 09:05:00",
          job_name: "01 A Gold Rulo Etiket",
          job_type: "Manuel",
          source: "manual_label",
          source_label: "Manuel Etiket",
          quantity: "1",
          file_type: "PDF",
          relative_path: "output/2026-05-21/qa/manual_yagmur_efe.pdf",
          status: "Beklemede",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Yağmur & Efe",
          size_text: "50 x 30 mm"
        });
      }
      currentState.printQueue = [...visualRows, ...rows];
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      return { injected: visualRows.length, total: currentState.printQueue.length };
    })()
    """)


def show_legacy_fallback(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const old = {
        id: "qa-source-badge-legacy",
        created_at: "2026-05-21 09:15:00",
        job_name: "Eski Manuel Kayıt",
        job_type: "Manuel",
        quantity: "1",
        file_type: "PDF",
        relative_path: "output/legacy/manual_old_record.pdf",
        status: "Beklemede",
        validation_status: "OK",
        output_validation_status: "OK",
        model_name: "01 A Gold Rulo Etiket",
        label_text: "Eski Manuel KayÄ±t",
        date_text: "12.05.2026",
        note_text: "Fallback kontrol",
        size_text: "50 x 30 mm"
      };
      currentState.printQueue = [old, ...(currentState.printQueue || []).filter(item => item.id !== old.id)];
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      const search = document.getElementById("queueSearch");
      if (search) search.value = "Eski Manuel Kayıt";
      if (typeof refreshPrintQueueFilters === "function") refreshPrintQueueFilters();
      return {
        badges: Array.from(document.querySelectorAll("#printQueueList .source-badge")).map(node => ({
          text: node.textContent.trim(),
          className: node.className,
          title: node.getAttribute("title") || ""
        })),
        rowsText: document.getElementById("printQueueList")?.innerText || ""
      };
    })()
    """)

def show_legacy_fallback(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const rows = currentState.printQueue || [];
      const base = rows.find(item => !item.source && !item.source_label && item.job_type) || rows[0] || {};
      const old = {
        ...base,
        id: "qa-source-badge-legacy",
        created_at: base.created_at || "2026-05-21 09:15:00",
        job_name: base.job_name || base.model_name || "Eski Manuel Kayit",
        job_type: base.job_type || "Manuel",
        quantity: base.quantity || "1",
        file_type: base.file_type || "PDF",
        relative_path: base.relative_path || base.path || "output/legacy/manual_old_record.pdf",
        status: base.status || "Beklemede",
        validation_status: base.validation_status || "OK",
        output_validation_status: base.output_validation_status || "OK",
        model_name: base.model_name || "01 A Gold Rulo Etiket",
        label_text: base.label_text || "Eski Manuel Kayit",
        date_text: base.date_text || "12.05.2026",
        note_text: base.note_text || "Fallback kontrol",
        size_text: base.size_text || "50 x 30 mm"
      };
      delete old.source;
      delete old.source_label;
      currentState.printQueue = [old];
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      const search = document.getElementById("queueSearch");
      if (search) search.value = "";
      if (typeof refreshPrintQueueFilters === "function") refreshPrintQueueFilters();
      return {
        badges: Array.from(document.querySelectorAll("#printQueueList .source-badge")).map(node => ({
          text: node.textContent.trim(),
          className: node.className,
          title: node.getAttribute("title") || ""
        })),
        rowsText: document.getElementById("printQueueList")?.innerText || ""
      };
    })()
    """)


def show_legacy_fallback(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const rows = currentState.printQueue || [];
      const base = rows.find(item => !item.source && !item.source_label && item.job_type) || rows[0] || {};
      const old = {
        ...base,
        id: "source-badge-old-record",
        created_at: base.created_at || "2026-05-21 09:15:00",
        job_name: base.job_name || base.model_name || "Eski Manuel Kayit",
        job_type: base.job_type || "Manuel",
        quantity: base.quantity || "1",
        file_type: base.file_type || "PDF",
        relative_path: "output/2026-05-21/print/manual/old_manual_record.pdf",
        status: base.status || "Beklemede",
        validation_status: base.validation_status || "OK",
        output_validation_status: base.output_validation_status || "OK",
        model_name: "01 A Gold Rulo Etiket",
        label_text: "Eski Manuel Kayit",
        date_text: "12.05.2026",
        note_text: "Fallback kontrol",
        size_text: base.size_text || "50 x 30 mm"
      };
      delete old.source;
      delete old.source_label;
      currentState.printQueue = [old];
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      return {
        badges: Array.from(document.querySelectorAll("#printQueueList .source-badge")).map(node => ({
          text: node.textContent.trim(),
          className: node.className,
          title: node.getAttribute("title") || ""
        })),
        rowsText: document.getElementById("printQueueList")?.innerText || ""
      };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["visual_rows"] = ensure_visual_rows(window)
    outcome["checks"]["open_1920"] = open_print_queue(window)
    outcome["screenshots"]["badge_1920"] = save_screenshot(window, "queue-source-badge-1920.png")

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["open_1366"] = open_print_queue(window)
    outcome["screenshots"]["badge_1366"] = save_screenshot(window, "queue-source-badge-1366.png")

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["legacy"] = show_legacy_fallback(window)
    outcome["screenshots"]["legacy_fallback"] = save_screenshot(window, "queue-source-badge-legacy-fallback.png")

    all_badges = [
        *(outcome["checks"]["open_1920"].get("badges", [])),
        *(outcome["checks"]["legacy"].get("badges", [])),
    ]
    joined = " ".join(f"{item.get('text', '')} {item.get('className', '')}" for item in all_badges)
    for expected in ["Etiket Studio", "Manuel Etiket", "source-badge--studio", "source-badge--manual", "source-badge--legacy"]:
        if expected not in joined:
            raise AssertionError(f"Kaynak rozeti standardı eksik: {expected} / {joined}")
    if "Yazıcı otomatik çalışmaz" not in outcome["checks"]["open_1920"].get("safeNote", ""):
        raise AssertionError("Yazdırma güvenlik notu detay panelinde korunmuyor.")

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
            outcome = {"status": "ERROR", "message": str(exc), **outcome}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=True, indent=2))
        window.close()
        window.deleteLater()
        QTimer.singleShot(0, app.quit)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(5200, start))
    QTimer.singleShot(90000, app.quit)
    code = app.exec()
    return 0 if code == 0 and outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
