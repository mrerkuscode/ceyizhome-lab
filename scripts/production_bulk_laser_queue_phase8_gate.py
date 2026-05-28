from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_bulk_laser_queue_phase8"
RESULT_PATH = OUTPUT_DIR / "production_bulk_laser_queue_phase8_gate_result.json"
NAMECUT_QUEUE_PATH = PROJECT_ROOT / "data" / "name_cut_queue.json"
NAMECUT_HISTORY_PATH = PROJECT_ROOT / "data" / "name_cut_transfer_history.json"

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


def backup_namecut_files() -> dict[Path, str | None]:
    return {
        NAMECUT_QUEUE_PATH: NAMECUT_QUEUE_PATH.read_text(encoding="utf-8") if NAMECUT_QUEUE_PATH.exists() else None,
        NAMECUT_HISTORY_PATH: NAMECUT_HISTORY_PATH.read_text(encoding="utf-8") if NAMECUT_HISTORY_PATH.exists() else None,
    }


def reset_namecut_files() -> None:
    NAMECUT_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NAMECUT_QUEUE_PATH.write_text("[]", encoding="utf-8")
    NAMECUT_HISTORY_PATH.write_text("[]", encoding="utf-8")


def restore_namecut_files(snapshot: dict[Path, str | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def seed_bulk_laser_items(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    return run_js(window, """
    (() => {
      showSection("bulkLabel");
      currentState.readiness = "OK";
      currentState.bulkProductionSource = "excel";
      bulkProductionSource = "excel";
      bulkGalleryFilter = "all";
      bulkGallerySearch = "";
      bulkGalleryVisibleLimit = 50;
      bulkLaserQueueTransferState = { found: 0, prepared: 0, review: 0, blocked: 0, duplicate: 0, updatedAt: "" };
      nameCutItems = [];
      selectedNameCutItemId = "";
      bulkGalleryItems = [
        {
          item_id: "phase8-ready-1",
          row_number: 1,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-1001",
          customer_name: "Ayşe & Mehmet",
          label_text: "Ayşe & Mehmet",
          date_text: "12.05.2026",
          note_text: "Söz Hatırası",
          quantity: 2,
          model_name: "01 A Gold Rulo Etiket",
          model_key: "01",
          model_status: "FOUND",
          laser_name: "Ayşe & Mehmet",
          status: "READY",
          layout_quality_score: 92,
          warnings: [],
          errors: []
        },
        {
          item_id: "phase8-review-2",
          row_number: 2,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-1002",
          customer_name: "Abdurrahman & Yağmur",
          label_text: "Abdurrahman & Yağmur",
          date_text: "25.05.2026",
          note_text: "İsim Hatırası",
          quantity: 1,
          model_name: "01 A Gold Rulo Etiket",
          model_key: "01",
          model_status: "FOUND",
          laser_name: "Abdurrahman & Yağmur Çok Uzun İsim",
          status: "WARNING",
          layout_quality_score: 74,
          warnings: ["Uzun isim kontrolü önerilir."],
          errors: []
        },
        {
          item_id: "phase8-blocked-3",
          row_number: 3,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-1003",
          customer_name: "Mustafa Kemal & Yağmur",
          label_text: "Mustafa Kemal & Yağmur",
          date_text: "18.05.2026",
          note_text: "Model eksik",
          quantity: 2,
          model_name: "",
          model_key: "",
          model_status: "MISSING",
          laser_name: "Mustafa Kemal & Yağmur",
          status: "ERROR",
          layout_quality_score: 45,
          warnings: [],
          errors: ["Model bulunamadı."]
        },
        {
          item_id: "phase8-empty-laser-4",
          row_number: 4,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-1004",
          customer_name: "Can",
          label_text: "Can",
          date_text: "20.05.2026",
          note_text: "Lazer boş",
          quantity: 1,
          model_name: "01 A Gold Rulo Etiket",
          model_key: "01",
          model_status: "FOUND",
          laser_name: "",
          status: "READY",
          layout_quality_score: 94,
          warnings: [],
          errors: []
        }
      ];
      selectedBulkGalleryItemId = "phase8-ready-1";
      setBulkProductionStep(4);
      ensureBulkProductionSummaryPanelState();
      renderBulkGallery();
      renderBulkProductionSummary();
      const text = document.getElementById("bulkLabel")?.innerText || "";
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        items: bulkGalleryItems.length,
        laserCandidates: bulkGalleryItems.filter(item => bulkItemHasLaser(item)).length,
        emptyLaserHasCandidate: bulkItemHasLaser(bulkGalleryItems[3]),
        hasAutoStartText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
      };
    })()
    """, timeout_ms=60000)


def transfer_laser_queue(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      showSection("bulkLabel");
      sendLaserBulkItemsToNameCutQueue();
      return true;
    })()
    """, timeout_ms=60000)
    wait(1400)
    return run_js(window, """
    (() => {
      const bulkItems = nameCutItems.filter(item => item.source === "bulk_production");
      const text = document.body.innerText || "";
      return {
        bulkNameCutCount: bulkItems.length,
        prepared: bulkItems.filter(item => String(item.status).toUpperCase() === "PENDING_PREPARATION").length,
        review: bulkItems.filter(item => String(item.status).toUpperCase() === "NEEDS_REVIEW").length,
        blockedInQueue: bulkItems.filter(item => String(item.status).toUpperCase() === "BLOCKED").length,
        sourcesOk: bulkItems.every(item => item.source === "bulk_production" && item.source_label === "Toplu Üretim"),
        containsBlockedRow: bulkItems.some(item => item.bulk_row_id === "phase8-blocked-3"),
        containsEmptyLaserRow: bulkItems.some(item => item.bulk_row_id === "phase8-empty-laser-4"),
        selectedNameCut: selectedNameCutItemId,
        summarySent: document.getElementById("bulkSummaryNameCutSent")?.innerText || "",
        summaryReview: document.getElementById("bulkSummaryNameCutReview")?.innerText || "",
        summaryBlocked: document.getElementById("bulkSummaryLaserBlocked")?.innerText || "",
        runText: document.getElementById("selectedBulkRunCard")?.innerText || "",
        hasAutoStartText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
      };
    })()
    """, timeout_ms=60000)


def duplicate_transfer(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      sendLaserBulkItemsToNameCutQueue();
      return true;
    })()
    """, timeout_ms=60000)
    wait(1400)
    return run_js(window, """
    (() => {
      const bulkItems = nameCutItems.filter(item => item.source === "bulk_production");
      return {
        bulkNameCutCount: bulkItems.length,
        duplicate: bulkLaserQueueTransferState.duplicate,
        prepared: bulkLaserQueueTransferState.prepared,
        review: bulkLaserQueueTransferState.review,
        blocked: bulkLaserQueueTransferState.blocked,
        message: document.getElementById("bulkRowPreviewStatus")?.innerText || ""
      };
    })()
    """, timeout_ms=60000)


def show_namecut(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(600)
    return run_js(window, """
    (() => {
      showSection("nameCutStudio");
      refreshNameCutStudioViews(currentNameCutLayout());
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        hasBulkBadge: /Toplu Üretim/.test(text),
        hasSafetyText: /RDWorks|lazer otomatik/i.test(text),
        visibleCards: document.querySelectorAll("#nameCutStudio .name-cut-card").length,
        sourceRows: document.querySelectorAll("#nameCutStudio .name-cut-source-row").length
      };
    })()
    """)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = backup_namecut_files()
    reset_namecut_files()
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(1600)

    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    try:
        outcome["checks"]["seed_1920"] = seed_bulk_laser_items(window, 1920, 1080)
        outcome["screenshots"]["bulk_laser_before_1920"] = save_screenshot(window, "bulk-laser-before-1920.png")

        outcome["checks"]["transfer"] = transfer_laser_queue(window)
        outcome["screenshots"]["bulk_laser_result_summary_1920"] = save_screenshot(window, "bulk-laser-result-summary-1920.png")

        outcome["checks"]["namecut_1920"] = show_namecut(window, 1920, 1080)
        outcome["screenshots"]["bulk_laser_namecut_queue_1920"] = save_screenshot(window, "bulk-laser-namecut-queue-1920.png")

        outcome["checks"]["duplicate_seed"] = seed_bulk_laser_items(window, 1920, 1080)
        outcome["checks"]["duplicate"] = duplicate_transfer(window)
        outcome["screenshots"]["bulk_laser_duplicate_warning_1920"] = save_screenshot(window, "bulk-laser-duplicate-warning-1920.png")

        outcome["checks"]["seed_1366"] = seed_bulk_laser_items(window, 1366, 768)
        run_js(window, "(() => { toggleBulkProductionSummary(true); return { collapsed: document.getElementById('bulkLabel')?.classList.contains('bulk-summary-collapsed') || false }; })()")
        outcome["screenshots"]["bulk_laser_compact_1366"] = save_screenshot(window, "bulk-laser-compact-1366.png")

        failures: list[str] = []
        seed = outcome["checks"]["seed_1920"]
        transfer = outcome["checks"]["transfer"]
        duplicate = outcome["checks"]["duplicate"]
        namecut = outcome["checks"]["namecut_1920"]
        if seed["laserCandidates"] != 3:
            failures.append(f"Lazer aday sayısı beklenen değil: {seed['laserCandidates']}")
        if seed["emptyLaserHasCandidate"]:
            failures.append("Boş lazer isimli kayıt aday sayıldı")
        if transfer["bulkNameCutCount"] != 2:
            failures.append(f"İsim Kesim kuyruğuna beklenen 2 kayıt yerine {transfer['bulkNameCutCount']} kayıt eklendi")
        if transfer["prepared"] != 1:
            failures.append("Hazır lazer kayıt pending_preparation olmadı")
        if transfer["review"] != 1:
            failures.append("Kontrol gerekli lazer kayıt needs_review olmadı")
        if transfer["blockedInQueue"] != 0 or transfer["containsBlockedRow"]:
            failures.append("Hatalı/model eksik kayıt kuyruğa eklendi")
        if transfer["containsEmptyLaserRow"]:
            failures.append("Boş lazer isimli kayıt kuyruğa eklendi")
        if not transfer["sourcesOk"]:
            failures.append("source/source_label Toplu Üretim standardı yazılmadı")
        if transfer["hasAutoStartText"] or seed["hasAutoStartText"]:
            failures.append("Otomatik yazıcı/lazer/RDWorks başlatma dili göründü")
        if duplicate["bulkNameCutCount"] != 2 or duplicate["duplicate"] < 2:
            failures.append("Duplicate gönderim engeli çalışmadı")
        if not namecut["hasBulkBadge"]:
            failures.append("İsim Kesim ekranında Toplu Üretim kaynak rozeti görünmedi")
        if not namecut["hasSafetyText"]:
            failures.append("İsim Kesim güvenlik dili görünmedi")

        if failures:
            outcome["status"] = "FAILED"
            outcome["failures"] = failures
            RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            return 1

        outcome["status"] = "PASSED"
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    finally:
        window.close()
        app.quit()
        restore_namecut_files(snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
