from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_preview_modal_phase4"
RESULT_PATH = OUTPUT_DIR / "production_bulk_preview_modal_phase4_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


MOCK_ITEMS = [
    {
        "item_id": "phase4-ready",
        "row_number": 2,
        "source_type": "excel",
        "source_label": "Excel",
        "order_no": "EX-1024",
        "customer_name": "Ayse Yilmaz",
        "product_name": "Gold Rulo Etiket",
        "barcode": "8690000001024",
        "sku": "GLD-50-30",
        "label_text": "Ayşe & Mehmet",
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "quantity": 2,
        "model_name": "01 A Gold Rulo Etiket",
        "model_status": "FOUND",
        "size_text": "50 x 30 mm",
        "name_cut_text": "Ayşe & Mehmet",
        "status": "READY",
        "layout_quality_score": 92,
        "warnings": [],
        "errors": [],
    },
    {
        "item_id": "phase4-error",
        "row_number": 4,
        "source_type": "excel",
        "label_text": "Modeli Eksik Satır",
        "date_text": "01.06.2026",
        "note_text": "Kontrol",
        "quantity": 1,
        "model_name": "",
        "model_status": "MISSING",
        "status": "ERROR",
        "layout_quality_score": 35,
        "warnings": [],
        "errors": ["Model bulunamadı. Üretime alınmadan önce model seçin."],
    },
    {
        "item_id": "phase4-laser",
        "row_number": 5,
        "source_type": "manual",
        "source_label": "Manuel",
        "label_text": "Abdurrahman & Yağmur",
        "date_text": "19.05.2026",
        "note_text": "Nişan Hatırası",
        "quantity": 1,
        "model_name": "01 A Gold Lazer Kesim",
        "model_status": "FOUND",
        "size_text": "80 x 22 mm",
        "laser_name": "Abdurrahman & Yağmur",
        "status": "WARNING",
        "layout_quality_score": 72,
        "warnings": ["Uzun lazer isim için minimum boşluk kontrolü önerilir."],
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


def seed_gallery(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    items_json = json.dumps(MOCK_ITEMS, ensure_ascii=False)
    return run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkGalleryItems = {items_json};
      selectedBulkGalleryItemId = "phase4-ready";
      setBulkProductionStep(4);
      setBulkGalleryFilter("all");
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: document.querySelector("#bulkLabel .bulk-wizard-step.active")?.innerText || "",
        cardCount: document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-item").length,
        hasPreviewButton: Boolean([...document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-card-actions button")].find(button => /Önizle/.test(button.textContent || "")))
      }};
    }})()
    """)


def modal_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      const modal = document.getElementById("bulkPreviewModal");
      const text = modal?.innerText || "";
      return {
        open: Boolean(modal && !modal.hidden),
        title: document.getElementById("bulkPreviewModalTitle")?.textContent || "",
        tabText: document.getElementById("bulkPreviewModalTabs")?.innerText || "",
        stageText: document.getElementById("bulkPreviewModalStage")?.innerText || "",
        sideText: document.getElementById("bulkPreviewModalSide")?.innerText || "",
        actionText: document.getElementById("bulkPreviewModalActions")?.innerText || "",
        text,
        activeTab: [...document.querySelectorAll("#bulkPreviewModal .bulk-preview-tab")].find(button => button.classList.contains("active"))?.textContent || "",
        hasNoFakeSuccess: !/başarıyla onay|başarıyla aç|lazer başladı|rdworks açıldı/i.test(text),
        bodyHasAutoLaser: /RDWorks otomatik başlatıldı|lazer otomatik başladı/i.test(document.body.innerText || "")
      };
    })()
    """)


def open_by_preview_button(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      const button = [...document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-card-actions button")].find(item => /Önizle/.test(item.textContent || ""));
      if (!button) return { clicked: false };
      button.click();
      const modal = document.getElementById("bulkPreviewModal");
      return { clicked: true, open: Boolean(modal && !modal.hidden), text: modal?.innerText || "" };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    outcome["checks"]["seed_1920"] = seed_gallery(window, 1920, 1080)
    outcome["checks"]["open_by_preview_button"] = open_by_preview_button(window)
    wait(400)
    outcome["checks"]["label_tab_1920"] = modal_state(window)
    outcome["screenshots"]["modal_1920"] = save_screenshot(window, "bulk-preview-modal-1920.png")

    run_js(window, "(() => { setBulkPreviewTab('laser'); return true; })()")
    wait(300)
    outcome["checks"]["laser_tab"] = modal_state(window)
    outcome["screenshots"]["laser_tab"] = save_screenshot(window, "bulk-preview-modal-laser-tab.png")

    run_js(window, "(() => { openBulkPreviewModal(1, 'errors', 'errors'); return true; })()")
    wait(300)
    outcome["checks"]["error_tab"] = modal_state(window)
    outcome["screenshots"]["error_tab"] = save_screenshot(window, "bulk-preview-modal-error-tab.png")

    outcome["checks"]["seed_1366"] = seed_gallery(window, 1366, 768)
    run_js(window, "(() => { openBulkPreviewModal(0, 'label'); return true; })()")
    wait(400)
    outcome["checks"]["label_tab_1366"] = modal_state(window)
    outcome["screenshots"]["modal_1366"] = save_screenshot(window, "bulk-preview-modal-1366.png")

    label = outcome["checks"]["label_tab_1920"]
    if not outcome["checks"]["open_by_preview_button"].get("open"):
      raise AssertionError("Önizle aksiyonu modal açmadı.")
    required_tabs = ["Etiket Önizleme", "Lazer Önizleme", "Alanlar", "Uyarılar / Hatalar"]
    if not all(tab in label.get("tabText", "") for tab in required_tabs):
        raise AssertionError("Modal sekmeleri eksik.")
    if not all(text in label.get("text", "") for text in ["Ayşe & Mehmet", "12.05.2026", "Söz Hatırası", "01 A Gold Rulo Etiket"]):
        raise AssertionError("Etiket önizleme modalında temel üretim bilgileri eksik.")
    laser = outcome["checks"]["laser_tab"]
    if "Lazer" not in laser.get("activeTab", "") or "Ayşe & Mehmet" not in laser.get("text", ""):
        raise AssertionError("Lazer önizleme sekmesi doğru veri göstermiyor.")
    error = outcome["checks"]["error_tab"]
    if "Uyarılar" not in error.get("activeTab", "") or "Model" not in error.get("text", ""):
        raise AssertionError("Hata sekmesi model eksik uyarısını göstermiyor.")
    if not label.get("hasNoFakeSuccess") or label.get("bodyHasAutoLaser"):
        raise AssertionError("Sahte success veya otomatik lazer/RDWorks dili tespit edildi.")

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
