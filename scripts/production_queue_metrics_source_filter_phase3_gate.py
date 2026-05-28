from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_queue_metrics_source_filter_phase3"
RESULT_PATH = OUTPUT_DIR / "production_queue_metrics_source_filter_phase3_gate_result.json"

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


def set_source_filter(window: WebMainWindow, value: str) -> dict:
    return run_js(window, f"""
    (() => {{
      showSection("printQueue");
      const filter = document.getElementById("queueTypeFilter");
      if (!filter) throw new Error("queueTypeFilter bulunamadi");
      filter.value = "{value}";
      if (typeof refreshPrintQueueFilters === "function") refreshPrintQueueFilters();
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      const badges = Array.from(document.querySelectorAll("#printQueueList .source-badge")).map(node => ({{
        text: node.textContent.trim(),
        className: node.className
      }}));
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        filterValue: filter.value,
        renderedRows: document.querySelectorAll("#printQueueList .queue-job-card").length,
        emptyText: document.getElementById("printQueueList")?.innerText || "",
        badges,
        metrics: {{
          next: document.getElementById("queueNext")?.textContent || "",
          nextMeta: document.getElementById("queueNextMeta")?.textContent || "",
          totalJobs: document.getElementById("queueTotalJobs")?.textContent || "",
          totalQty: document.getElementById("queueQty")?.textContent || "",
          pending: document.getElementById("queuePending")?.textContent || "",
          printed: document.getElementById("queuePrinted")?.textContent || "",
          review: document.getElementById("queueReview")?.textContent || ""
        }}
      }};
    }})()
    """)


def inject_legacy_record(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      const old = {
        id: "phase3-source-less-old-record",
        created_at: "2026-05-21 10:30:00",
        job_name: "Eski Manuel Kayit",
        job_type: "Manuel",
        quantity: "1",
        file_type: "PDF",
        relative_path: "output/legacy/phase3_old_manual_record.pdf",
        status: "Beklemede",
        validation_status: "OK",
        model_name: "01 A Gold Rulo Etiket",
        label_text: "Eski Kayit",
        date_text: "12.05.2026",
        note_text: "Source fallback kontrol",
        size_text: "50 x 30 mm"
      };
      currentState.printQueue = [
        old,
        ...(currentState.printQueue || []).filter(row => row.id !== old.id)
      ];
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      return { ok: true, total: (currentState.printQueue || []).length };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    run_js(window, """(() => { showSection("printQueue"); if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters(); return true; })()""")
    outcome["checks"]["all_1920"] = set_source_filter(window, "all")
    outcome["screenshots"]["all_1920"] = save_screenshot(window, "queue-phase3-all-1920.png")

    window.resize(1366, 768)
    wait(700)
    outcome["checks"]["all_1366"] = set_source_filter(window, "all")
    outcome["screenshots"]["all_1366"] = save_screenshot(window, "queue-phase3-all-1366.png")

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["studio"] = set_source_filter(window, "etiket_studio")
    outcome["screenshots"]["studio"] = save_screenshot(window, "queue-phase3-source-filter-studio.png")

    outcome["checks"]["manual"] = set_source_filter(window, "manual_label")
    outcome["screenshots"]["manual"] = save_screenshot(window, "queue-phase3-source-filter-manual.png")

    outcome["checks"]["legacy_injected"] = inject_legacy_record(window)
    outcome["checks"]["legacy"] = set_source_filter(window, "legacy")
    outcome["screenshots"]["legacy"] = save_screenshot(window, "queue-phase3-source-filter-legacy.png")

    checks = outcome["checks"]
    if checks["all_1920"]["activePage"] != "printQueue":
      raise AssertionError("Yazdirma Sirasi aktif degil")
    if checks["studio"]["renderedRows"] and not all("source-badge--studio" in b["className"] for b in checks["studio"]["badges"]):
      raise AssertionError("Etiket Studio filtresi sadece studio rozetleri gostermiyor")
    if checks["manual"]["renderedRows"] and not all("source-badge--manual" in b["className"] for b in checks["manual"]["badges"]):
      raise AssertionError("Manuel Etiket filtresi sadece manual rozetleri gostermiyor")
    if not checks["legacy"]["renderedRows"]:
      raise AssertionError("Eski kayit filtresi hic satir gostermedi")
    if not all(("source-badge--legacy" in b["className"] or "source-badge--unknown" in b["className"]) for b in checks["legacy"]["badges"]):
      raise AssertionError("Eski kayit filtresi legacy/unknown rozet standardini kullanmiyor")
    if not checks["all_1920"]["metrics"]["totalJobs"]:
      raise AssertionError("Metrik kartlari okunamadi")

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
