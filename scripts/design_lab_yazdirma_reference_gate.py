from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "design_lab_yazdirma_reference"
RESULT_PATH = OUTPUT_DIR / "design_lab_yazdirma_reference_gate_result.json"

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


def open_yazdirma_reference(window: WebMainWindow) -> dict:
    result = run_js(window, """
    (() => {
      showSection("designLab");
      selectDesignLabView("queue");
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      const view = document.querySelector('[data-design-lab-view="queue"]');
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        queueActive: Boolean(view?.classList.contains("active")),
        title: view?.querySelector(".lab-print-header h2")?.textContent || "",
        sourceBadges: Array.from(view?.querySelectorAll(".source-badge") || []).map(item => item.textContent.trim()),
        commandbar: view?.querySelector(".lab-print-commandbar")?.innerText || "",
        filters: view?.querySelector(".lab-print-filterbar")?.innerText || "",
        detail: view?.querySelector(".lab-print-summary")?.innerText || "",
        rows: view?.querySelectorAll(".lab-print-job").length || 0
      };
    })()
    """)
    wait(900)
    if result.get("activePage") != "designLab" or not result.get("queueActive"):
        raise RuntimeError(f"Yazdırma Design Lab açılamadı: {result}")
    return result


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(600)
    outcome["checks"]["open_1920"] = open_yazdirma_reference(window)
    outcome["screenshots"]["reference_1920"] = save_screenshot(window, "yazdirma-reference-1920.png")

    window.resize(1366, 768)
    wait(900)
    outcome["checks"]["open_1366"] = open_yazdirma_reference(window)
    outcome["screenshots"]["reference_1366"] = save_screenshot(window, "yazdirma-reference-1366.png")

    badges = " ".join(outcome["checks"]["open_1920"].get("sourceBadges", []))
    for expected in ["Etiket Studio", "Manuel Etiket", "Trendyol", "Toplu Üretim", "Eski kayıt"]:
        if expected not in badges:
            raise AssertionError(f"Kaynak rozeti eksik: {expected} / {badges}")
    if "Yazıcı otomatik çalışmaz" not in outcome["checks"]["open_1920"].get("commandbar", ""):
        raise AssertionError("Güvenli yazdırma uyarısı görünmüyor.")
    if outcome["checks"]["open_1920"].get("rows", 0) < 6:
        raise AssertionError("Yazdırma referansı yeterli mock satır içermiyor.")

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
