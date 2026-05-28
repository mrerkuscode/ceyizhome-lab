from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_error_panel_phase5"
RESULT_PATH = OUTPUT_DIR / "production_bulk_error_panel_phase5_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


MOCK_ITEMS = [
    {
        "item_id": "phase5-ready",
        "row_number": 2,
        "source_type": "excel",
        "source_label": "Excel",
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
        "item_id": "phase5-overflow",
        "row_number": 3,
        "source_type": "trendyol",
        "source_label": "Trendyol",
        "order_no": "TY-5531",
        "label_text": "Mustafa Kemal & Yağmur",
        "date_text": "25.05.2026",
        "note_text": "İsim Hatırası",
        "quantity": 1,
        "model_name": "01 A Gold Rulo Etiket",
        "model_status": "FOUND",
        "status": "WARNING",
        "layout_quality_score": 58,
        "warnings": ["Yazı taşıyor olabilir. Baskıdan önce kontrol edin.", "Yazısı küçük görünebilir."],
        "errors": [],
    },
    {
        "item_id": "phase5-error",
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
        "item_id": "phase5-laser",
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


def seed_error_panel(window: WebMainWindow, width: int, height: int, filter_name: str = "all") -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    items_json = json.dumps(MOCK_ITEMS, ensure_ascii=False)
    return run_js(window, f"""
    (() => {{
      showSection("bulkLabel");
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkGalleryItems = {items_json};
      selectedBulkGalleryItemId = "phase5-error";
      setBulkProductionStep(5);
      setBulkErrorFilter("{filter_name}");
      document.querySelector(".main")?.scrollTo({{ top: 0, left: 0, behavior: "auto" }});
      const panel = document.querySelector("#bulkLabel [data-bulk-step-panel='5']");
      const text = panel?.innerText || "";
      return {{
        activePage: document.querySelector(".page.active")?.id || "",
        activeStep: document.querySelector("#bulkLabel .bulk-wizard-step.active")?.innerText || "",
        errorCards: panel?.querySelectorAll(".bulk-error-card").length || 0,
        kpis: panel?.querySelectorAll(".bulk-error-kpi").length || 0,
        filters: panel?.querySelectorAll("[data-bulk-error-filter]").length || 0,
        text,
        hasCategories: ["Model Eksik", "Yazı Taşıyor", "Yazısı Küçük", "Lazer Kontrolü"].every(label => text.includes(label)),
        hasFields: ["Satır", "Önerilen aksiyon", "Önizle", "Hata Detayı", "Düzeltildi olarak işaretle"].every(label => text.includes(label)),
        hasNoFakeSuccess: !/başarıyla onay|başarıyla düzelt|lazer başladı|rdworks açıldı/i.test(document.body.innerText || "")
      }};
    }})()
    """)


def click_error_action(window: WebMainWindow, label: str) -> dict[str, object]:
    return run_js(window, f"""
    (() => {{
      const button = [...document.querySelectorAll("#bulkWarningList .bulk-error-card button")].find(item => (item.textContent || "").includes("{label}"));
      if (!button) return {{ clicked: false }};
      button.click();
      const modal = document.getElementById("bulkPreviewModal");
      return {{
        clicked: true,
        modalOpen: Boolean(modal && !modal.hidden),
        activeTab: [...document.querySelectorAll("#bulkPreviewModal .bulk-preview-tab")].find(item => item.classList.contains("active"))?.textContent || "",
        modalText: modal?.innerText || "",
        bodyText: document.body.innerText || ""
      }};
    }})()
    """)


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    outcome["checks"]["panel_1920"] = seed_error_panel(window, 1920, 1080, "all")
    outcome["screenshots"]["panel_1920"] = save_screenshot(window, "bulk-error-panel-1920.png")

    outcome["checks"]["model_missing"] = seed_error_panel(window, 1920, 1080, "model_missing")
    outcome["screenshots"]["model_missing"] = save_screenshot(window, "bulk-error-panel-model-missing.png")

    outcome["checks"]["laser_warning"] = seed_error_panel(window, 1920, 1080, "laser_check")
    outcome["screenshots"]["laser_warning"] = save_screenshot(window, "bulk-error-panel-laser-warning.png")

    outcome["checks"]["preview_modal"] = click_error_action(window, "Önizle")
    wait(300)
    run_js(window, "(() => { closeBulkPreviewModal(); return true; })()")
    outcome["checks"]["error_modal"] = click_error_action(window, "Hata Detayı")

    outcome["checks"]["panel_1366"] = seed_error_panel(window, 1366, 768, "all")
    outcome["screenshots"]["panel_1366"] = save_screenshot(window, "bulk-error-panel-1366.png")

    main = outcome["checks"]["panel_1920"]
    if main.get("activePage") != "bulkLabel" or "Hataları Düzelt" not in main.get("activeStep", ""):
        raise AssertionError("Hataları Düzelt adımı açılmadı.")
    if main.get("errorCards", 0) < 3 or main.get("kpis", 0) < 6 or main.get("filters", 0) < 8:
        raise AssertionError("Hata paneli kartları, metrikleri veya filtreleri eksik.")
    if not main.get("hasCategories") or not main.get("hasFields"):
        raise AssertionError("Hata kategorileri veya kart bilgi hiyerarşisi eksik.")
    if not main.get("hasNoFakeSuccess"):
        raise AssertionError("Sahte success veya otomatik lazer/RDWorks dili tespit edildi.")
    if outcome["checks"]["model_missing"].get("errorCards", 0) < 1:
        raise AssertionError("Model eksik filtresi kayıt göstermiyor.")
    if outcome["checks"]["laser_warning"].get("errorCards", 0) < 1:
        raise AssertionError("Lazer kontrol filtresi kayıt göstermiyor.")
    if not outcome["checks"]["preview_modal"].get("modalOpen"):
        raise AssertionError("Hata kartından Önizle modalı açılmadı.")
    if "Uyarılar" not in outcome["checks"]["error_modal"].get("activeTab", ""):
        raise AssertionError("Hata Detayı modalı Uyarılar / Hatalar sekmesiyle açılmadı.")

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
