from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_source_stepper_phase1"
RESULT_PATH = OUTPUT_DIR / "production_bulk_source_stepper_phase1_gate_result.json"

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


def open_bulk_page(window: WebMainWindow) -> dict:
    result = run_js(window, """
    (() => {
      showSection("bulkLabel");
      setBulkProductionStep(1);
      setBulkProductionSource("excel");
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      const page = document.querySelector("#bulkLabel");
      const head = page?.querySelector(".bulk-production-head");
      const stepper = page?.querySelector(".bulk-wizard-steps");
      const sourceCards = Array.from(page?.querySelectorAll(".bulk-source-card") || []);
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        title: page?.querySelector(".page-title")?.textContent?.trim() || "",
        subtitle: page?.querySelector(".page-subtitle")?.textContent?.trim() || "",
        actions: head?.innerText || "",
        stepCount: page?.querySelectorAll(".bulk-wizard-step").length || 0,
        activeStep: page?.querySelector(".bulk-wizard-step.active")?.innerText || "",
        doneSteps: page?.querySelectorAll(".bulk-wizard-step.done").length || 0,
        pendingSteps: page?.querySelectorAll(".bulk-wizard-step.pending").length || 0,
        sourceCount: sourceCards.length,
        sourceTexts: sourceCards.map(card => card.innerText).join("\\n---\\n"),
        selectedSource: page?.querySelector(".bulk-source-card.selected")?.dataset?.bulkSource || "",
        excelButton: Boolean(page?.querySelector('[data-bulk-source="excel"] button.primary')),
        plannedButtons: Array.from(page?.querySelectorAll(".btn.planned")).map(button => button.textContent.trim()),
        summaryVisible: Boolean(page?.querySelector(".bulk-production-summary-panel")),
        galleryPresent: Boolean(page?.querySelector("#bulkGalleryGrid")),
        shellWidth: Math.round(page?.querySelector(".bulk-production-shell")?.getBoundingClientRect().width || 0)
      };
    })()
    """)
    wait(600)
    if result.get("activePage") != "bulkLabel":
        raise RuntimeError(f"Toplu Uretim production sayfasi acilamadi: {result}")
    return result


def check_warning_language(window: WebMainWindow) -> dict:
    result = run_js(window, """
    (() => {
      const originalAlert = window.alert;
      const alerts = [];
      window.alert = message => alerts.push(String(message || ""));
      showBulkFeatureNotConnected("Çoklu manuel giriş");
      const plannedMessage = alerts.at(-1) || "";
      importBulkFromTrendyol();
      const trendyolMessage = alerts.at(-1) || "";
      showSection("bulkLabel");
      setBulkProductionStep(1);
      window.alert = originalAlert;
      return {
        plannedMessage,
        trendyolMessage,
        activePageAfter: document.querySelector(".page.active")?.id || ""
      };
    })()
    """)
    wait(500)
    return result


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(600)
    outcome["checks"]["open_1920"] = open_bulk_page(window)
    outcome["screenshots"]["bulk_1920"] = save_screenshot(window, "bulk-source-stepper-1920.png")

    warning_check = check_warning_language(window)
    outcome["checks"]["warning_language"] = warning_check

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["open_1366"] = open_bulk_page(window)
    outcome["screenshots"]["bulk_1366"] = save_screenshot(window, "bulk-source-stepper-1366.png")

    check = outcome["checks"]["open_1920"]
    combined = "\n".join([
        check.get("title", ""),
        check.get("subtitle", ""),
        check.get("actions", ""),
        check.get("activeStep", ""),
        check.get("sourceTexts", ""),
    ])
    for expected in [
        "Toplu Üretim Studio",
        "Excel, Trendyol ve manuel kaynaklardan gelen etiket/lazer işlerini toplu olarak hazırlayın.",
        "Örnek Excel İndir",
        "Rehber Video",
        "Geçmiş İşlemler",
        "Kaynak Seç",
        "Excel’den Yükle",
        "Trendyol Siparişlerine Git",
        "Manuel Satır Ekle",
        "Çoklu giriş",
        "Kopyala/Yapıştır",
    ]:
        if expected not in combined:
            raise AssertionError(f"Beklenen metin eksik: {expected}")
    if check.get("stepCount") != 6:
        raise AssertionError("Toplu Uretim stepper 6 adim icermiyor.")
    if check.get("sourceCount") != 3:
        raise AssertionError("Toplu Uretim kaynak kartlari 3 adet degil.")
    if not check.get("excelButton"):
        raise AssertionError("Excel Dosyasi Sec butonu bulunamadi.")
    if len(check.get("plannedButtons") or []) < 2:
        raise AssertionError("Bagli olmayan manuel butonlar planli/pasif gorunumde degil.")
    if "sahte başarı" not in warning_check.get("plannedMessage", ""):
        raise AssertionError("Bagli olmayan buton uyarisi sahte success vermeme dilini icermiyor.")
    if "canlı import başlatmaz" not in warning_check.get("trendyolMessage", ""):
        raise AssertionError("Trendyol butonu canli import yapmadigini aciklamiyor.")
    if outcome["checks"]["open_1366"].get("sourceCount") != 3:
        raise AssertionError("1366 gorunumde kaynak kartlari eksik.")
    if not check.get("galleryPresent"):
        raise AssertionError("Production galeri bolumu DOM'da korunmuyor.")

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
