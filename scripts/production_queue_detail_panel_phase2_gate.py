from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_queue_detail_panel_phase2"
RESULT_PATH = OUTPUT_DIR / "production_queue_detail_panel_phase2_gate_result.json"

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
    wait(700)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def open_queue_and_select(window: WebMainWindow, source: str) -> dict:
    return run_js(window, f"""
    (() => {{
      showSection("printQueue");
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      const rows = currentState.printQueue || [];
      let item = rows.find(row => row.source === "{source}");
      if (!item && "{source}" === "legacy") item = rows.find(row => !row.source && !row.source_label && row.job_type);
      if (!item && rows.length) item = rows[0];
      if (!item) throw new Error("Queue row bulunamadi");
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue || []);
      if (typeof selectPrintQueueItem === "function") selectPrintQueueItem(item.id);
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      return {{
        id: item.id || "",
        source: item.source || "",
        sourceLabel: item.source_label || "",
        activePage: document.querySelector(".page.active")?.id || "",
        detailText: document.getElementById("queueDetailInfo")?.innerText || "",
        statusText: document.getElementById("queueDetailStatus")?.innerText || "",
        actionsText: document.getElementById("queueDetailActions")?.innerText || "",
        sourceBadge: document.querySelector("#queueDetailInfo .source-badge")?.textContent.trim() || "",
        sourceBadgeClass: document.querySelector("#queueDetailInfo .source-badge")?.className || "",
        sectionCount: document.querySelectorAll("#queueDetailInfo .queue-detail-section, #queueDetailStatus .queue-detail-section").length,
        actionGroupCount: document.querySelectorAll("#queueDetailActions .queue-detail-action-group").length,
        previewText: document.getElementById("queueDetailPreview")?.innerText || ""
      }};
    }})()
    """)


def show_legacy_only(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const old = {
        id: "detail-panel-old-record",
        created_at: "2026-05-21 09:15:00",
        job_name: "Eski Manuel Kayit",
        job_type: "Manuel",
        quantity: "1",
        file_type: "PDF",
        relative_path: "output/2026-05-21/print/manual/old_manual_record.pdf",
        status: "Beklemede",
        validation_status: "OK",
        output_validation_status: "OK",
        model_name: "01 A Gold Rulo Etiket",
        label_text: "Eski Manuel Kayit",
        date_text: "12.05.2026",
        note_text: "Fallback kontrol",
        size_text: "50 x 30 mm"
      };
      currentState.printQueue = [old];
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      if (typeof selectPrintQueueItem === "function") selectPrintQueueItem(old.id);
      return {
        sourceBadge: document.querySelector("#queueDetailInfo .source-badge")?.textContent.trim() || "",
        sourceBadgeClass: document.querySelector("#queueDetailInfo .source-badge")?.className || "",
        detailText: document.getElementById("queueDetailInfo")?.innerText || "",
        statusText: document.getElementById("queueDetailStatus")?.innerText || "",
        actionsText: document.getElementById("queueDetailActions")?.innerText || ""
      };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["studio_1920"] = open_queue_and_select(window, "etiket_studio")
    outcome["screenshots"]["detail_1920"] = save_screenshot(window, "queue-detail-panel-1920.png")

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["manual_1366"] = open_queue_and_select(window, "manual_label")
    outcome["screenshots"]["detail_1366"] = save_screenshot(window, "queue-detail-panel-1366.png")

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["legacy"] = show_legacy_only(window)
    outcome["screenshots"]["legacy"] = save_screenshot(window, "queue-detail-panel-legacy.png")

    joined = json.dumps(outcome["checks"], ensure_ascii=False)
    required = [
        "Üretim Bilgisi",
        "Kaynak Bilgisi",
        "Kalite / Validasyon",
        "Queue Durumu",
        "Yazıcı otomatik çalışmaz",
        "PDF Aç",
        "Güvenli Yazdır",
        "Sıradan Kaldır",
        "source-badge",
    ]
    for text in required:
        if text not in joined:
            raise AssertionError(f"Detay paneli beklentisi eksik: {text}")

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
