from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_gallery_phase3"
RESULT_PATH = OUTPUT_DIR / "production_bulk_gallery_phase3_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


MOCK_ITEMS = [
    {
        "item_id": "phase3-ready",
        "row_number": 2,
        "source_type": "excel",
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
        "item_id": "phase3-warning",
        "row_number": 3,
        "source_type": "trendyol",
        "label_text": "Mustafa Kemal & Yağmur",
        "date_text": "25.05.2026",
        "note_text": "İsim Hatırası",
        "quantity": 1,
        "model_name": "01 A Gold Rulo Etiket",
        "model_status": "FOUND",
        "size_text": "50 x 30 mm",
        "status": "WARNING",
        "layout_quality_score": 61,
        "warnings": ["Yazı taşıyor olabilir. Baskıdan önce kontrol edin.", "Yazısı küçük görünebilir."],
        "errors": [],
    },
    {
        "item_id": "phase3-error",
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
        "item_id": "phase3-laser",
        "row_number": 5,
        "source_type": "manual",
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


def open_gallery(window: WebMainWindow, width: int, height: int, filter_name: str = "all") -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    items_json = json.dumps(MOCK_ITEMS, ensure_ascii=False)
    return run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkGalleryItems = {items_json};
      selectedBulkGalleryItemId = "phase3-ready";
      setBulkProductionStep(4);
      setBulkGalleryFilter("{filter_name}");
      renderBulkProductionSummary();
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      const page = document.querySelector("#bulkLabel");
      const grid = document.getElementById("bulkGalleryGrid");
      const text = page?.innerText || "";
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: page?.querySelector(".bulk-wizard-step.active")?.innerText || "",
        cardCount: grid?.querySelectorAll(".bulk-gallery-item").length || 0,
        phase3Cards: grid?.querySelectorAll(".bulk-gallery-item.phase3-card").length || 0,
        laserCards: grid?.querySelectorAll(".bulk-gallery-item.has-laser").length || 0,
        errorCards: grid?.querySelectorAll(".bulk-gallery-item.has-error").length || 0,
        placeholders: grid?.querySelectorAll(".bulk-gallery-placeholder").length || 0,
        hasStatusReason: text.includes("Kontrol gerekli") || text.includes("Model eksik"),
        hasFilters: ["Hazır", "Kontrol Gerekli", "Hatalı", "Lazer İsimli", "Yazı Taşıyan", "Yazısı Küçük", "AI Düzeltilen"].every(label => text.includes(label)),
        hasFields: ["Ayşe & Mehmet", "Tarih", "Adet", "Kaynak", "Kalite %", "Lazer var", "Akıllı Düzenle", "Hata Detayı"].every(label => text.includes(label)),
        hasNoFakeSuccessText: !/başarıyla ai|başarıyla onay/i.test(text),
        hasDryRunButton: Boolean([...page.querySelectorAll("button")].find(button => (button.textContent || "").includes("Kontrol Et"))),
        hasQueueAction: Boolean(String(generateReadyBulkGalleryItems).includes("bulk_generate_gallery_items_and_add_to_queue")),
        bodyText: text
      }};
    }})()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    outcome["checks"]["gallery_1920"] = open_gallery(window, 1920, 1080, "all")
    outcome["screenshots"]["gallery_1920"] = save_screenshot(window, "bulk-gallery-1920.png")

    outcome["checks"]["gallery_1366"] = open_gallery(window, 1366, 768, "all")
    outcome["screenshots"]["gallery_1366"] = save_screenshot(window, "bulk-gallery-1366.png")

    outcome["checks"]["error_filter"] = open_gallery(window, 1920, 1080, "error")
    outcome["screenshots"]["error_card"] = save_screenshot(window, "bulk-gallery-error-card.png")

    outcome["checks"]["laser_filter"] = open_gallery(window, 1920, 1080, "laser")
    outcome["screenshots"]["laser_card"] = save_screenshot(window, "bulk-gallery-laser-card.png")

    main = outcome["checks"]["gallery_1920"]
    if main.get("activePage") != "bulkLabel" or "Toplu Önizleme Galerisi" not in main.get("activeStep", ""):
        raise AssertionError("Toplu Uretim galeri adimi acilmadi.")
    if main.get("cardCount", 0) < 3 or main.get("phase3Cards", 0) < 3:
        raise AssertionError("Phase 3 galeri kartlari render edilmedi.")
    if not main.get("hasFilters") or not main.get("hasFields"):
        raise AssertionError("Galeri filtreleri veya kart bilgi hiyerarsisi eksik.")
    if main.get("laserCards", 0) < 1:
        raise AssertionError("Lazer rozetli kart gorunmuyor.")
    if main.get("errorCards", 0) < 1 or main.get("placeholders", 0) < 1:
        raise AssertionError("Hata karti veya eksik preview placeholder gorunmuyor.")
    if not main.get("hasNoFakeSuccessText"):
        raise AssertionError("Sahte basari dili tespit edildi.")
    if not main.get("hasDryRunButton") or not main.get("hasQueueAction"):
        raise AssertionError("Excel/dry-run veya mevcut queue handler akisi korunmuyor.")

    laser = outcome["checks"]["laser_filter"]
    if laser.get("cardCount", 0) < 1 or laser.get("laserCards", 0) < 1:
        raise AssertionError("Lazer filtre kartlari gosteremiyor.")

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
