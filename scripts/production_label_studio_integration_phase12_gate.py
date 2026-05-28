from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_label_studio_integration_phase12"
RESULT_PATH = OUTPUT_DIR / "production_label_studio_integration_phase12_gate_result.json"
PRINT_QUEUE_PATH = PROJECT_ROOT / "data" / "print_queue.json"

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


def backup_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def restore_file(path: Path, backup: str | None) -> None:
    if backup is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(backup, encoding="utf-8")


def read_queue_rows() -> list[dict[str, object]]:
    if not PRINT_QUEUE_PATH.exists():
        return []
    try:
        data = json.loads(PRINT_QUEUE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def seed_bulk_gallery(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(800)
    return run_js(window, """
    (() => {
      window.alert = message => {
        window.__phase12Alerts = window.__phase12Alerts || [];
        window.__phase12Alerts.push(String(message || ""));
      };
      const model = currentLabelModels.find(item => item.path && (item.fields_summary || []).length)
        || currentLabelModels.find(item => item.path)
        || null;
      if (!model) return { activePage: "", error: "label model yok" };
      const ready = {
        item_id: "phase12-ready-bulk",
        row_number: 12,
        source_type: "excel",
        source_label: "Excel",
        order_no: "BULK-2026-012",
        customer_name: "Ayse Yilmaz",
        product_name: "Gold Rulo Etiket",
        barcode: "869000012",
        sku: "GLD-012",
        label_text: "Ayşe & Mehmet",
        date_text: "12.05.2026",
        note_text: "Söz Hatırası",
        quantity: 2,
        model_name: model.model_name || model.title || "01 A Gold Rulo Etiket",
        model_path: model.path,
        model_status: "FOUND",
        size_text: model.size_text || "50 x 30 mm",
        name_cut_text: "Ayşe & Mehmet",
        status: "READY",
        layout_quality_score: 92,
        warnings: [],
        errors: []
      };
      const missingModel = { ...ready, item_id: "phase12-missing-model", row_number: 13, model_name: "", model_path: "", model_status: "MISSING", status: "ERROR", errors: ["Model eksik."] };
      const emptyName = { ...ready, item_id: "phase12-empty-name", row_number: 14, label_text: "", customer_name: "", status: "ERROR", errors: ["İsim alanı boş."] };
      currentState.readiness = "OK";
      bulkGalleryItems = [ready, missingModel, emptyName];
      selectedBulkGalleryItemId = "phase12-ready-bulk";
      setBulkProductionStep(4);
      setBulkGalleryFilter("all");
      showSection("bulkLabel");
      renderBulkGallery();
      document.querySelector(".main")?.scrollTo({ top: 0, left: 0, behavior: "auto" });
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        cardCount: document.querySelectorAll("#bulkGalleryGrid .bulk-gallery-item").length,
        hasStudioButton: Boolean([...document.querySelectorAll("#bulkGalleryGrid button")].find(button => /Studio’da Aç/.test(button.textContent || ""))),
        modelPath: model.path
      };
    })()
    """)


def open_ready_in_studio(window: WebMainWindow) -> dict[str, object]:
    run_js(window, '(() => { openBulkItemInLabelStudio("phase12-ready-bulk"); return true; })()')
    wait(1400)
    return run_js(window, """
    (() => {
      const payload = manualPayload();
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        mode: labelStudioEntryMode,
        session: labelStudioSession,
        sourceContext: studioOrderContext,
        title: document.getElementById("labelStudioPageTitle")?.textContent || "",
        badge: document.getElementById("corelStudioModeBadge")?.textContent || "",
        name: document.getElementById("manualText")?.value || "",
        date: document.getElementById("manualDateText")?.value || "",
        note: document.getElementById("manualNoteText")?.value || "",
        qty: document.getElementById("manualQty")?.value || "",
        laser: document.getElementById("manualLaserName")?.value || "",
        outputSummary: document.getElementById("manualOutputControlSummary")?.textContent || "",
        payloadSource: payload._queue_source || "",
        payloadOrigin: payload._origin_source || "",
        payloadSourceItem: payload._source_item_id || "",
        text: document.body.innerText || ""
      };
    })()
    """)


def blocked_open_checks(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      window.__phase12Alerts = [];
      showSection("bulkLabel");
      const idsBefore = bulkGalleryItems.map(item => `${item.item_id}:${item.label_text || ""}:${item.model_path || ""}`);
      window.__phase12Alerts = [];
      openBulkItemInLabelStudio(2);
      const emptyStatus = document.getElementById("bulkRowPreviewStatus")?.textContent || "";
      const emptyAlert = (window.__phase12Alerts || []).slice(-1)[0] || "";
      window.__phase12Alerts = [];
      openBulkItemInLabelStudio(1);
      const missingStatus = document.getElementById("bulkRowPreviewStatus")?.textContent || "";
      const missingAlert = (window.__phase12Alerts || []).slice(-1)[0] || "";
      return { idsBefore, missingStatus, missingAlert, emptyStatus, emptyAlert, activePage: document.querySelector(".page.active")?.id || "" };
    })()
    """)


def render_output(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      window.__phase12Render = null;
      renderManual({
        silent: true,
        silentPreflight: true,
        onComplete: (result, ok) => { window.__phase12Render = { ok, result }; }
      });
      return true;
    })()
    """)
    wait(6000)
    return run_js(window, """
    (() => {
      const render = window.__phase12Render || {};
      return {
        ok: Boolean(render.ok),
        status: render.result?.status || "",
        pdf: render.result?.batch_pdf_path || render.result?.pdf_path || "",
        png: render.result?.png_path || "",
        validation: render.result?.output_validation?.status || "",
        outputSummary: document.getElementById("manualOutputControlSummary")?.textContent || "",
        filesText: document.getElementById("manualOutputControlFiles")?.innerText || "",
        noFakeSuccess: !/sahte|dummy/i.test(document.body.innerText || "")
      };
    })()
    """)


def queue_output(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      window.__phase12QueueStart = Date.now();
      renderManualToQueue();
      return true;
    })()
    """)
    wait(7000)
    rows = read_queue_rows()
    match = next((row for row in reversed(rows) if row.get("source_item_id") == "phase12-ready-bulk" or row.get("bulk_row_id") == "12"), {})
    ui = run_js(window, """
    (() => ({
      modalOpen: Boolean(document.getElementById("queueAddedModal") && !document.getElementById("queueAddedModal").hidden),
      modalText: document.getElementById("queueAddedModal")?.innerText || "",
      outputSummary: document.getElementById("manualOutputControlSummary")?.textContent || "",
      bodyHasAutoStart: /yazıcı otomatik başladı|lazer otomatik başladı|RDWorks açıldı/i.test(document.body.innerText || "")
    }))()
    """)
    return {"row": match, "ui": ui}


def main() -> int:
    suppress_message_boxes()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    queue_backup = backup_file(PRINT_QUEUE_PATH)
    app = QApplication.instance() or QApplication(sys.argv)
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(2600)

    checks: dict[str, object] = {}
    screenshots: dict[str, str] = {}
    try:
      checks["seed"] = seed_bulk_gallery(window, 1920, 1080)
      if checks["seed"].get("error"):
          raise RuntimeError(str(checks["seed"]["error"]))
      screenshots["bulk_before"] = save_screenshot(window, "label-studio-phase12-bulk-before-1920.png")

      checks["studio_open"] = open_ready_in_studio(window)
      screenshots["studio_filled_1920"] = save_screenshot(window, "label-studio-phase12-filled-1920.png")
      if checks["studio_open"]["activePage"] != "label":
          raise RuntimeError("Etiket Studio açılmadı.")
      if checks["studio_open"]["name"] != "Ayşe & Mehmet" or checks["studio_open"]["date"] != "12.05.2026" or checks["studio_open"]["note"] != "Söz Hatırası" or checks["studio_open"]["qty"] != "2":
          raise RuntimeError(f"Alan aktarımı hatalı: {checks['studio_open']}")
      if checks["studio_open"]["payloadSource"] != "label_studio" or checks["studio_open"]["payloadOrigin"] != "bulk_production":
          raise RuntimeError(f"Studio queue/origin payload hatalı: {checks['studio_open']}")
      if "Veri Hazır" not in checks["studio_open"]["outputSummary"] or "Önizleme Eksik" not in checks["studio_open"]["outputSummary"]:
          raise RuntimeError(f"Önizleme eksik durumu net değil: {checks['studio_open']['outputSummary']}")

      checks["blocked"] = blocked_open_checks(window)
      screenshots["blocked_warning"] = save_screenshot(window, "label-studio-phase12-blocked-warning.png")
      if "model" not in (checks["blocked"]["missingStatus"] + checks["blocked"]["missingAlert"]).lower():
          raise RuntimeError(f"Eksik model engeli görünmedi: {checks['blocked']}")
      if "alanı boş" not in (checks["blocked"]["emptyStatus"] + checks["blocked"]["emptyAlert"]).lower():
          raise RuntimeError(f"Boş isim engeli görünmedi: {checks['blocked']}")

      checks["studio_open_again"] = open_ready_in_studio(window)
      checks["render"] = render_output(window)
      screenshots["output_status"] = save_screenshot(window, "label-studio-phase12-output-status-1920.png")
      if not checks["render"]["ok"]:
          raise RuntimeError(f"PDF/PNG render başarısız: {checks['render']}")
      if not checks["render"]["pdf"] or not checks["render"]["png"]:
          raise RuntimeError(f"PDF/PNG gerçek yol dönmedi: {checks['render']}")
      if "Çıktı Hazır" not in checks["render"]["outputSummary"]:
          raise RuntimeError(f"Çıktı durumu net değil: {checks['render']['outputSummary']}")

      checks["queue"] = queue_output(window)
      screenshots["queue_summary"] = save_screenshot(window, "label-studio-phase12-queue-summary-1920.png")
      row = checks["queue"]["row"]
      if not row:
          raise RuntimeError(f"Queue kaydı bulunamadı: {checks['queue']}")
      if row.get("source") != "label_studio" or row.get("source_label") != "Etiket Studio":
          raise RuntimeError(f"Queue source standardı hatalı: {row}")
      if row.get("origin_source") != "bulk_production":
          raise RuntimeError(f"Origin source eksik: {row}")
      if checks["queue"]["ui"].get("bodyHasAutoStart"):
          raise RuntimeError("Yazıcı/lazer/RDWorks otomatik başlama metni göründü.")

      window.resize(1366, 768)
      wait(900)
      screenshots["studio_1366"] = save_screenshot(window, "label-studio-phase12-1366.png")
      window.resize(1920, 1080)
      wait(700)
      screenshots["studio_1920"] = save_screenshot(window, "label-studio-phase12-1920.png")

      result = {"status": "PASSED", "checks": checks, "screenshots": screenshots}
    except Exception as exc:  # noqa: BLE001
      result = {"status": "FAILED", "error": str(exc), "checks": checks, "screenshots": screenshots}
    finally:
      restore_file(PRINT_QUEUE_PATH, queue_backup)
      RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
      window.close()

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
