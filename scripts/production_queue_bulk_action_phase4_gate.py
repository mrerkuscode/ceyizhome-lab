from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_queue_bulk_action_phase4"
RESULT_PATH = OUTPUT_DIR / "production_queue_bulk_action_phase4_gate_result.json"

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


def seed_queue(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      showSection("printQueue");
      currentState.printQueue = [
        {
          id: "phase4-studio-1",
          created_at: "2026-05-21 10:10:00",
          job_type: "Manuel",
          source: "etiket_studio",
          source_label: "Etiket Studio",
          relative_path: "output/2026-05-21/manual/01_a_gold_ayse_mehmet_2adet.pdf",
          file_type: "PDF",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Ayşe & Mehmet",
          date_text: "12.05.2026",
          note_text: "Söz Hatırası",
          quantity: 2,
          status: "Beklemede",
          validation_status: "OK",
          size_text: "50 x 30 mm"
        },
        {
          id: "phase4-manual-1",
          created_at: "2026-05-21 10:15:00",
          job_type: "Manuel",
          source: "manual_label",
          source_label: "Manuel Etiket",
          relative_path: "output/2026-05-21/manual/yagmur_efe_1adet.pdf",
          file_type: "PDF",
          model_name: "01 A Gold Rulo Etiket",
          label_text: "Yağmur & Efe",
          date_text: "19.05.2026",
          note_text: "Nişan Hatırası",
          quantity: 1,
          status: "Yazdırıldı",
          validation_status: "OK",
          size_text: "50 x 30 mm"
        },
        {
          id: "phase4-review-1",
          created_at: "2026-05-21 10:20:00",
          job_type: "Manuel",
          relative_path: "output/legacy/phase4_old_record.pdf",
          file_type: "PDF",
          model_name: "Eski Gold Şablon",
          label_text: "Eski kayıt",
          date_text: "12.05.2026",
          note_text: "Fallback kontrol",
          quantity: 1,
          status: "Beklemede",
          validation_status: "MISSING",
          size_text: "50 x 30 mm"
        }
      ];
      selectedPrintQueueIds.clear();
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue);
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return { rows: currentState.printQueue.length };
    })()
    """)


def inspect_bulk(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        selectedCount: document.getElementById("queueSelectedCount")?.textContent || "",
        selectedSummary: document.getElementById("queueSelectedSummary")?.textContent || "",
        actionText: Array.from(document.querySelectorAll(".queue-bulk-action-group button, #queueBulkRemove")).map(node => ({
          id: node.id,
          text: node.textContent.trim(),
          className: node.className,
          ariaDisabled: node.getAttribute("aria-disabled"),
          title: node.getAttribute("title") || ""
        })),
        barClass: document.querySelector("#printQueue .queue-bulk-actions")?.className || ""
      };
    })()
    """)


def click_without_selection(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      window.__phase4AlertMessage = "";
      const oldAlert = window.alert;
      window.alert = (message) => { window.__phase4AlertMessage = String(message || ""); };
      try {
        document.getElementById("queueBulkPrint")?.click();
      } finally {
        window.alert = oldAlert;
      }
      return { alert: window.__phase4AlertMessage || "" };
    })()
    """)


def select_rows(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      selectedPrintQueueIds.clear();
      togglePrintQueueSelection("phase4-studio-1", true);
      togglePrintQueueSelection("phase4-manual-1", true);
      return {
        selectedCount: document.getElementById("queueSelectedCount")?.textContent || "",
        selectedSummary: document.getElementById("queueSelectedSummary")?.textContent || "",
        printTitle: document.getElementById("queueBulkPrint")?.getAttribute("title") || "",
        printText: document.getElementById("queueBulkPrint")?.textContent.trim() || ""
      };
    })()
    """)


def capture_confirm(window: WebMainWindow) -> dict:
    return run_js(window, """
    (() => {
      window.__phase4ConfirmMessage = "";
      const oldConfirm = window.confirm;
      window.confirm = (message) => {
        window.__phase4ConfirmMessage = String(message || "");
        return false;
      };
      try {
        removeSelectedQueueItems();
      } finally {
        window.confirm = oldConfirm;
      }
      let box = document.getElementById("phase4ConfirmPreview");
      if (!box) {
        box = document.createElement("div");
        box.id = "phase4ConfirmPreview";
        document.body.appendChild(box);
      }
      box.setAttribute("style", "position:fixed;right:28px;bottom:28px;z-index:99999;width:420px;max-width:calc(100vw - 56px);padding:18px 20px;border:1px solid rgba(239,68,68,.32);border-radius:18px;background:#fff7f7;color:#7f1d1d;box-shadow:0 22px 60px rgba(15,23,42,.22);font:800 14px Inter, system-ui, sans-serif;");
      box.innerHTML = `<b style="display:block;margin-bottom:8px;color:#991b1b;">Confirm Önizleme</b><span>${window.__phase4ConfirmMessage}</span>`;
      return { confirm: window.__phase4ConfirmMessage || "" };
    })()
    """)


def run_gate(window: WebMainWindow) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["seed"] = seed_queue(window)
    outcome["checks"]["empty"] = inspect_bulk(window)
    outcome["checks"]["empty_click"] = click_without_selection(window)
    outcome["screenshots"]["empty_1920"] = save_screenshot(window, "queue-bulk-action-empty-1920.png")

    outcome["checks"]["selected"] = select_rows(window)
    outcome["checks"]["selected_inspect"] = inspect_bulk(window)
    outcome["screenshots"]["selected_1920"] = save_screenshot(window, "queue-bulk-action-selected-1920.png")

    window.resize(1366, 768)
    wait(800)
    outcome["checks"]["selected_1366"] = inspect_bulk(window)
    outcome["screenshots"]["selected_1366"] = save_screenshot(window, "queue-bulk-action-selected-1366.png")

    window.resize(1920, 1080)
    wait(500)
    outcome["checks"]["confirm"] = capture_confirm(window)
    outcome["screenshots"]["confirm"] = save_screenshot(window, "queue-bulk-action-confirm.png")

    empty = outcome["checks"]["empty"]
    selected = outcome["checks"]["selected_inspect"]
    confirm = outcome["checks"]["confirm"]["confirm"]
    if empty["activePage"] != "printQueue":
        raise AssertionError("Yazdirma Sirasi aktif degil")
    if "0 seçili" not in empty["selectedCount"]:
        raise AssertionError("Bos secim sayaci 0 secili degil")
    if "Önce en az bir iş seçin" not in outcome["checks"]["empty_click"]["alert"]:
        raise AssertionError("Bos secim uyarisi beklenen metni gostermiyor")
    if not all(item["ariaDisabled"] == "true" for item in empty["actionText"]):
        raise AssertionError("Bos secimde toplu aksiyonlar pasif gorunmuyor")
    if "2 seçili" not in selected["selectedCount"]:
        raise AssertionError("Coklu secim sayaci dogru degil")
    if not any("bekleyen" in selected["selectedSummary"] for _ in [0]):
        raise AssertionError("Secim ozeti bekleyen/yazdirildi bilgisini gostermiyor")
    if not all(item["ariaDisabled"] == "false" for item in selected["actionText"]):
        raise AssertionError("Secim varken toplu aksiyonlar aktif gorunmuyor")
    if "İlk Seçiliyi Yazdır" not in selected["actionText"][1]["text"]:
        raise AssertionError("Toplu print etiketi ilk secili davranisini anlatmiyor")
    if "Yazıcı otomatik çalışmaz" not in selected["actionText"][1]["title"]:
        raise AssertionError("Toplu print tooltip guvenli yazdirma dilini icermiyor")
    if "Seçili 2 iş yazdırma sırasından kaldırılacak" not in confirm:
        raise AssertionError("Kaldirma confirm metni guvenli dille guncellenmemis")
    if "yazıcıyı çalıştırmaz" not in confirm:
        raise AssertionError("Kaldirma confirm metni yazici guvenligini belirtmiyor")

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
