from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_queue_integration_phase6"
RESULT_PATH = OUTPUT_DIR / "production_bulk_queue_integration_phase6_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import print_queue_api  # noqa: E402


MOCK_ITEMS = [
    {
        "item_id": "phase6-ready",
        "row_number": 2,
        "source_type": "excel",
        "source_label": "Excel",
        "label_text": "Ayşe & Mehmet",
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "quantity": 2,
        "model_name": "01 A Gold Rulo Etiket",
        "model_no": "01",
        "model_status": "FOUND",
        "status": "READY",
        "layout_quality_score": 92,
        "warnings": [],
        "errors": [],
    },
    {
        "item_id": "phase6-warning",
        "row_number": 3,
        "source_type": "trendyol",
        "source_label": "Trendyol",
        "label_text": "Mustafa Kemal & Yağmur",
        "date_text": "25.05.2026",
        "note_text": "İsim Hatırası",
        "quantity": 1,
        "model_name": "01 A Gold Rulo Etiket",
        "model_no": "01",
        "model_status": "FOUND",
        "status": "WARNING",
        "layout_quality_score": 61,
        "warnings": ["Yazı taşıyor olabilir.", "Yazısı küçük görünebilir."],
        "errors": [],
    },
    {
        "item_id": "phase6-error",
        "row_number": 4,
        "source_type": "excel",
        "source_label": "Excel",
        "label_text": "Modeli Eksik Satır",
        "date_text": "01.06.2026",
        "note_text": "Kontrol",
        "quantity": 1,
        "model_name": "",
        "model_no": "",
        "model_status": "MISSING",
        "status": "ERROR",
        "layout_quality_score": 35,
        "warnings": [],
        "errors": ["Model bulunamadı."],
    },
    {
        "item_id": "phase6-laser-ready",
        "row_number": 5,
        "source_type": "manual",
        "source_label": "Manuel",
        "label_text": "Yağmur & Efe",
        "date_text": "19.05.2026",
        "note_text": "Nişan Hatırası",
        "quantity": 1,
        "model_name": "01 A Gold Rulo Etiket",
        "model_no": "01",
        "model_status": "FOUND",
        "laser_name": "Yağmur & Efe",
        "status": "READY",
        "layout_quality_score": 90,
        "warnings": [],
        "errors": [],
    },
]


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


def seed_bulk_phase6(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    items_json = json.dumps(MOCK_ITEMS, ensure_ascii=False)
    return run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkGalleryItems = {items_json};
      selectedBulkGalleryItemId = "phase6-ready";
      bridge = Object.assign({{}}, bridge || {{}}, {{
        bulk_generate_gallery_items_and_add_to_queue(payload, callback) {{
          window.__phase6Payload = JSON.parse(payload || "[]");
          callback(JSON.stringify({{
            status: "STARTED",
            message: `${{window.__phase6Payload.length}} hazır kayıt için test üretim akışı başlatıldı.`
          }}));
        }}
      }});
      setBulkProductionStep(4);
      renderBulkGallery();
      generateReadyBulkGalleryItems();
      const payload = window.__phase6Payload || [];
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: document.querySelector("#bulkLabel .bulk-wizard-step.active")?.innerText || "",
        capturedCount: payload.length,
        capturedStatuses: payload.map(item => item.status),
        capturedLabels: payload.map(item => item.label_text),
        hasErrorItem: payload.some(item => item.status === "ERROR" || item.model_status === "MISSING"),
        hasWarningItem: payload.some(item => item.status === "WARNING"),
        hasLaserReady: payload.some(item => String(item.laser_name || item.name_cut_text || "").trim()),
        statusText: document.getElementById("bulkRowPreviewStatus")?.textContent || "",
        runText: document.getElementById("selectedBulkRunCard")?.innerText || "",
        bodyHasAutoPrint: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(document.body.innerText || "")
      }};
    }})()
    """)


def render_bulk_source_queue(window: WebMainWindow) -> dict[str, object]:
    queue_path = print_queue_api.queue_path(PROJECT_ROOT)
    original = queue_path.read_text(encoding="utf-8") if queue_path.exists() else None
    try:
        print_queue_api.add_to_print_queue(
            PROJECT_ROOT,
            {
                "job_name": "01 A Gold Rulo Etiket",
                "job_type": "Toplu",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "quantity": "2",
                "file_type": "Rulo Batch PDF",
                "relative_path": "output/2026-05-21/phase6/bulk_source_demo.pdf",
                "model_name": "01 A Gold Rulo Etiket",
                "label_text": "Ayşe & Mehmet",
                "size_text": "50 x 30 mm",
            },
        )
        rows = print_queue_api.list_print_queue(PROJECT_ROOT)
        rows_json = json.dumps(rows, ensure_ascii=False)
        result = run_js(window, f"""
        (() => {{
          showSection("printQueue");
          currentState.printQueue = {rows_json};
          selectedPrintQueueIds = new Set();
          printQueueFilterState.type = "bulk_production";
          printQueueFilterState.includeTestArchive = true;
          updatePrintQueue(currentState.printQueue);
          const text = document.getElementById("printQueue")?.innerText || "";
          const badge = document.querySelector("#printQueue .source-badge--bulk")?.innerText || "";
          return {{
            activePage: document.querySelector(".page.active")?.id || "",
            text,
            badge,
            hasBulkSource: text.includes("Toplu Üretim") && badge.includes("Toplu Üretim"),
            autoPrintText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
          }};
        }})()
        """)
        return result
    finally:
        if original is None:
            if queue_path.exists():
                queue_path.unlink()
        else:
            queue_path.write_text(original, encoding="utf-8")


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    outcome["checks"]["bulk_1920"] = seed_bulk_phase6(window, 1920, 1080)
    outcome["screenshots"]["bulk_1920"] = save_screenshot(window, "bulk-queue-integration-1920.png")

    outcome["checks"]["skip_errors"] = outcome["checks"]["bulk_1920"]
    outcome["screenshots"]["skip_errors"] = save_screenshot(window, "bulk-queue-skip-errors.png")

    outcome["checks"]["bulk_1366"] = seed_bulk_phase6(window, 1366, 768)
    outcome["screenshots"]["bulk_1366"] = save_screenshot(window, "bulk-queue-integration-1366.png")

    outcome["checks"]["queue_source"] = render_bulk_source_queue(window)
    outcome["screenshots"]["queue_source"] = save_screenshot(window, "bulk-queue-toplu-uretim-source.png")

    main = outcome["checks"]["bulk_1920"]
    if main.get("capturedCount") != 2:
        raise AssertionError(f"Hazır kayıt filtresi beklenen 2 kaydı göndermedi: {main}")
    if main.get("hasErrorItem") or main.get("hasWarningItem"):
        raise AssertionError("Hatalı veya kontrol gerekli kayıt queue payload içine girdi.")
    if not main.get("hasLaserReady"):
        raise AssertionError("Lazer isimli hazır kayıt tespit edilmedi.")
    if "atlandı" not in main.get("statusText", "") and "bekletildi" not in main.get("statusText", ""):
        raise AssertionError("Atlanan/kontrol gerekli kayıt özeti görünmüyor.")
    if main.get("bodyHasAutoPrint"):
        raise AssertionError("Otomatik yazıcı/lazer başlatma dili tespit edildi.")
    queue_source = outcome["checks"]["queue_source"]
    if not queue_source.get("hasBulkSource"):
        raise AssertionError("Yazdırma Sırası Toplu Üretim source rozeti göstermiyor.")
    if queue_source.get("autoPrintText"):
        raise AssertionError("Yazdırma Sırası otomatik üretim/yazdırma dili gösteriyor.")

    outcome["status"] = "PASSED"
    return outcome


def main() -> int:
    suppress_message_boxes()
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.show()
    outcome: dict[str, object] = {"status": "ERROR", "message": "not started"}
    started = {"value": False}

    def start() -> None:
        if started["value"]:
            return
        started["value"] = True
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
    QTimer.singleShot(9000, start)
    QTimer.singleShot(90000, app.quit)
    code = app.exec()
    return 0 if code == 0 and outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
