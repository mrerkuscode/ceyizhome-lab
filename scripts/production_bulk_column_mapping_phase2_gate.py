from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_column_mapping_phase2"
RESULT_PATH = OUTPUT_DIR / "production_bulk_column_mapping_phase2_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


MOCK_MAPPING = {
    "status": "OK",
    "message": "Excel kolon eşleştirmesi hazır.",
    "missing_required": [],
    "columns": [
        {"source": "Sipariş Kodu", "mapped": "order_no", "role": "zorunlu", "status": "mapped"},
        {"source": "model_no", "mapped": "model_no", "role": "zorunlu", "status": "mapped"},
        {"source": "template_no", "mapped": "template_no", "role": "zorunlu", "status": "mapped"},
        {"source": "Yazılacak İsim", "mapped": "label_text", "role": "zorunlu", "status": "mapped"},
        {"source": "Nikah Tarihi", "mapped": "date_text", "role": "zorunlu", "status": "mapped"},
        {"source": "Açıklama", "mapped": "note_text", "role": "opsiyonel", "status": "mapped"},
        {"source": "Miktar", "mapped": "quantity", "role": "zorunlu", "status": "mapped"},
        {"source": "Lazer Yazısı", "mapped": "laser_text", "role": "opsiyonel", "status": "mapped"},
        {"source": "Ürün Kodu", "mapped": "sku", "role": "yardımcı", "status": "mapped"},
        {"source": "Barkod No", "mapped": "barcode", "role": "yardımcı", "status": "mapped"},
    ],
}


MISSING_MAPPING = {
    "status": "WARNING",
    "message": "Bazı zorunlu kolonlar eksik.",
    "missing_required": ["label_text", "quantity"],
    "columns": [
        {"source": "Sipariş Kodu", "mapped": "order_no", "role": "zorunlu", "status": "mapped"},
        {"source": "model_no", "mapped": "model_no", "role": "zorunlu", "status": "mapped"},
        {"source": "Nikah Tarihi", "mapped": "date_text", "role": "zorunlu", "status": "mapped"},
        {"source": "Açıklama", "mapped": "note_text", "role": "opsiyonel", "status": "mapped"},
    ],
}


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


def open_mapping_step(window: WebMainWindow, mapping: dict[str, object]) -> dict[str, object]:
    mapping_json = json.dumps(mapping, ensure_ascii=False)
    result = run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      setBulkProductionStep(2);
      currentState.bulkColumnMapping = {mapping_json};
      bulkGalleryItems = [
        {{ row_number: 1, label_text: "Ayşe & Mehmet", date_text: "12.05.2026", note_text: "Söz Hatırası", quantity: 2, laser_name: "Ayşe & Mehmet", status: "READY" }},
        {{ row_number: 2, label_text: "Yağmur & Efe", date_text: "", note_text: "Nişan Hatırası", quantity: 1, laser_name: "Yağmur & Efe", status: "WARNING" }}
      ];
      updateBulkColumnMapping(currentState.bulkColumnMapping);
      renderBulkProductionSummary();
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      const page = document.querySelector("#bulkLabel");
      const panel = document.querySelector("#bulkColumnMappingPanel");
      const text = panel?.innerText || "";
      const panelClone = panel?.cloneNode(true);
      panelClone?.querySelectorAll("details").forEach(node => node.remove());
      const visibleTechnicalText = panelClone?.textContent || "";
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: page?.querySelector(".bulk-wizard-step.active")?.innerText || "",
        title: page?.querySelector('[data-bulk-step-panel="2"] h2')?.textContent || "",
        panelText: text,
        visibleTechnicalText,
        cards: panel?.querySelectorAll(".operator-field-card").length || 0,
        matched: panel?.querySelectorAll(".operator-field-card.matched").length || 0,
        missing: panel?.querySelectorAll(".operator-field-card.missing").length || 0,
        review: panel?.querySelectorAll(".operator-field-card.review").length || 0,
        summaryMapped: document.getElementById("bulkSummaryMappedFields")?.textContent || "",
        summaryMissing: document.getElementById("bulkSummaryMissingFields")?.textContent || "",
        sampleRows: panel?.querySelectorAll(".bulk-sample-row").length || 0,
        hasDryRunButton: Boolean([...page.querySelectorAll("button")].find(button => (button.textContent || "").includes("Kontrol Et"))),
        hasGallery: Boolean(document.getElementById("bulkGalleryGrid")),
        hasQueueAction: Boolean(String(generateReadyBulkGalleryItems).includes("bulk_generate_gallery_items_and_add_to_queue"))
      }};
    }})()
    """)
    wait(500)
    if result.get("activePage") != "bulkLabel":
        raise RuntimeError(f"Toplu Uretim acilamadi: {result}")
    return result


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(600)
    outcome["checks"]["mapping_1920"] = open_mapping_step(window, MOCK_MAPPING)
    outcome["screenshots"]["mapping_1920"] = save_screenshot(window, "bulk-column-mapping-1920.png")

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["mapping_1366"] = open_mapping_step(window, MOCK_MAPPING)
    outcome["screenshots"]["mapping_1366"] = save_screenshot(window, "bulk-column-mapping-1366.png")

    window.resize(1920, 1080)
    wait(600)
    outcome["checks"]["missing_required"] = open_mapping_step(window, MISSING_MAPPING)
    outcome["screenshots"]["missing_required"] = save_screenshot(window, "bulk-column-mapping-missing-required.png")

    check = outcome["checks"]["mapping_1920"]
    combined = "\n".join([check.get("title", ""), check.get("activeStep", ""), check.get("panelText", "")])
    for expected in [
        "Alanları Kontrol Et",
        "Türkçe Kolon Eşleştirme",
        "İsim",
        "Tarih",
        "Not",
        "Adet",
        "Etiket Modeli",
        "Lazer İsim",
        "Eşleşti",
        "Zorunlu",
        "Örnek Satır Önizleme",
        "Ayşe & Mehmet",
    ]:
        if expected not in combined:
            raise AssertionError(f"Beklenen mapping metni eksik: {expected}")
    if check.get("cards", 0) < 10:
        raise AssertionError("Turkce operator alan kartlari eksik.")
    if check.get("sampleRows", 0) < 2:
        raise AssertionError("Ornek satir onizleme eksik.")
    visible = check.get("visibleTechnicalText", "")
    if visible.count("label_text") > 1 or visible.count("quantity") > 1:
        raise AssertionError("Teknik alan adlari ana operator ekraninda baskin gorunuyor.")
    missing = outcome["checks"]["missing_required"]
    if missing.get("missing", 0) < 1 or "Eksik zorunlu alan" not in missing.get("panelText", ""):
        raise AssertionError("Eksik zorunlu alan durumu gorunmuyor.")
    if not check.get("hasDryRunButton") or not check.get("hasGallery") or not check.get("hasQueueAction"):
        raise AssertionError("Excel/dry-run veya galeri/queue akisi DOM/handler olarak korunmuyor.")

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
