from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_namecut_queue_persistence_phase9"
RESULT_PATH = OUTPUT_DIR / "production_namecut_queue_persistence_phase9_gate_result.json"
QUEUE_PATH = PROJECT_ROOT / "data" / "name_cut_queue.json"
HISTORY_PATH = PROJECT_ROOT / "data" / "name_cut_transfer_history.json"

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


def read_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def backup_files() -> dict[Path, str | None]:
    return {
        QUEUE_PATH: QUEUE_PATH.read_text(encoding="utf-8") if QUEUE_PATH.exists() else None,
        HISTORY_PATH: HISTORY_PATH.read_text(encoding="utf-8") if HISTORY_PATH.exists() else None,
    }


def clear_test_files() -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text("[]", encoding="utf-8")
    HISTORY_PATH.write_text("[]", encoding="utf-8")


def restore_files(snapshot: dict[Path, str | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def seed_bulk_items(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    return run_js(window, """
    (() => {
      showSection("bulkLabel");
      currentState.readiness = "OK";
      bulkProductionSource = "excel";
      bulkGalleryFilter = "all";
      bulkGallerySearch = "";
      bulkGalleryVisibleLimit = 50;
      bulkLaserQueueTransferState = { found: 0, prepared: 0, review: 0, blocked: 0, duplicate: 0, updatedAt: "" };
      nameCutItems = [];
      nameCutTransferHistoryRows = [];
      selectedNameCutItemId = "";
      bulkGalleryItems = [
        {
          item_id: "phase9-ready-1",
          row_number: 1,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-P9-001",
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
          item_id: "phase9-review-2",
          row_number: 2,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-P9-002",
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
          item_id: "phase9-blocked-3",
          row_number: 3,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-P9-003",
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
          item_id: "phase9-empty-laser-4",
          row_number: 4,
          source_type: "excel",
          source_label: "Excel",
          order_no: "SIP-P9-004",
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
      selectedBulkGalleryItemId = "phase9-ready-1";
      setBulkProductionStep(4);
      ensureBulkProductionSummaryPanelState();
      renderBulkGallery();
      renderBulkProductionSummary();
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        items: bulkGalleryItems.length,
        laserCandidates: bulkGalleryItems.filter(item => bulkItemHasLaser(item)).length,
        emptyLaserHasCandidate: bulkItemHasLaser(bulkGalleryItems[3])
      };
    })()
    """, timeout_ms=60000)


def transfer_to_persistent_queue(window: WebMainWindow) -> dict[str, object]:
    run_js(window, "(() => { showSection('bulkLabel'); sendLaserBulkItemsToNameCutQueue(); return true; })()", timeout_ms=60000)
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
        hasBatch: bulkItems.every(item => Boolean(item.transfer_batch_id)),
        containsBlockedRow: bulkItems.some(item => item.bulk_row_id === "phase9-blocked-3"),
        containsEmptyLaserRow: bulkItems.some(item => item.bulk_row_id === "phase9-empty-laser-4"),
        historyRows: nameCutTransferHistoryRows.length,
        summarySent: document.getElementById("bulkSummaryNameCutSent")?.innerText || "",
        message: document.getElementById("bulkRowPreviewStatus")?.innerText || "",
        hasAutoStartText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
      };
    })()
    """, timeout_ms=60000)


def reset_and_reload(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      nameCutItems = [];
      nameCutTransferHistoryRows = [];
      selectedNameCutItemId = "";
      refreshNameCutStudioViews(currentNameCutLayout());
      refreshState();
      return true;
    })()
    """, timeout_ms=60000)
    wait(1400)
    return run_js(window, """
    (() => {
      const bulkItems = nameCutItems.filter(item => item.source === "bulk_production");
      return {
        restored: bulkItems.length,
        historyRows: nameCutTransferHistoryRows.length,
        selected: selectedNameCutItemId || "",
        hasBulkBadge: /Toplu Üretim/.test(document.getElementById("nameCutStudio")?.innerText || "")
      };
    })()
    """, timeout_ms=60000)


def duplicate_transfer(window: WebMainWindow) -> dict[str, object]:
    run_js(window, "(() => { showSection('bulkLabel'); sendLaserBulkItemsToNameCutQueue(); return true; })()", timeout_ms=60000)
    wait(1400)
    return run_js(window, """
    (() => {
      const bulkItems = nameCutItems.filter(item => item.source === "bulk_production");
      return {
        bulkNameCutCount: bulkItems.length,
        duplicate: bulkLaserQueueTransferState.duplicate,
        prepared: bulkLaserQueueTransferState.prepared,
        review: bulkLaserQueueTransferState.review,
        historyRows: nameCutTransferHistoryRows.length,
        message: document.getElementById("bulkRowPreviewStatus")?.innerText || ""
      };
    })()
    """, timeout_ms=60000)


def mark_prepared(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      showSection("nameCutStudio");
      const first = nameCutItems.find(item => item.source === "bulk_production");
      if (!first) return { started: false };
      markNameCutQueueItemPrepared(first.item_id);
      return { started: true, itemId: first.item_id };
    })()
    """, timeout_ms=60000)
    wait(1400)
    return run_js(window, """
    (() => {
      const first = nameCutItems.find(item => item.source === "bulk_production");
      return {
        status: first?.status || "",
        exportStatus: document.getElementById("nameCutStudioExportStatus")?.innerText || document.getElementById("nameCutExportStatus")?.innerText || ""
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
      renderNameCutTransferHistory(nameCutTransferHistoryRows);
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      const historyText = document.getElementById("nameCutTransferHistory")?.innerText || "";
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        hasBulkBadge: /Toplu Üretim/.test(text),
        hasHistory: /Toplu Üretim Aktarımları|Aktarım geçmişi/.test(historyText),
        historyText,
        hasSafetyText: /RDWorks|lazer otomatik/i.test(text),
        visibleCards: document.querySelectorAll("#nameCutStudio .name-cut-card").length,
        sourceRows: document.querySelectorAll("#nameCutStudio .name-cut-source-row").length
      };
    })()
    """)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = backup_files()
    clear_test_files()
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(1700)

    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    try:
        outcome["checks"]["seed_1920"] = seed_bulk_items(window, 1920, 1080)
        outcome["screenshots"]["bulk_transfer_before_1920"] = save_screenshot(window, "namecut-persistence-bulk-before-1920.png")

        outcome["checks"]["transfer"] = transfer_to_persistent_queue(window)
        queue_rows = read_json_list(QUEUE_PATH)
        history_rows = read_json_list(HISTORY_PATH)
        outcome["checks"]["queue_file"] = {
            "rows": len(queue_rows),
            "history": len(history_rows),
            "sourcesOk": all(row.get("source") == "bulk_production" and row.get("source_label") == "Toplu Üretim" for row in queue_rows),
            "hasBatch": all(bool(row.get("transfer_batch_id")) for row in queue_rows),
            "statuses": sorted({str(row.get("status") or "") for row in queue_rows}),
        }
        outcome["screenshots"]["bulk_transfer_result_1920"] = save_screenshot(window, "namecut-persistence-bulk-summary-1920.png")

        outcome["checks"]["reload"] = reset_and_reload(window)
        outcome["checks"]["namecut_1920"] = show_namecut(window, 1920, 1080)
        outcome["screenshots"]["namecut_queue_1920"] = save_screenshot(window, "namecut-persistence-namecut-queue-1920.png")

        outcome["checks"]["duplicate_seed"] = seed_bulk_items(window, 1920, 1080)
        outcome["checks"]["duplicate"] = duplicate_transfer(window)
        outcome["screenshots"]["duplicate_warning"] = save_screenshot(window, "namecut-persistence-duplicate-warning.png")

        outcome["checks"]["prepared_update"] = mark_prepared(window)
        outcome["screenshots"]["transfer_history"] = save_screenshot(window, "namecut-persistence-transfer-history.png")

        outcome["checks"]["namecut_1366"] = show_namecut(window, 1366, 768)
        outcome["screenshots"]["namecut_1366"] = save_screenshot(window, "namecut-persistence-1366.png")

        failures: list[str] = []
        seed = outcome["checks"]["seed_1920"]
        transfer = outcome["checks"]["transfer"]
        queue_file = outcome["checks"]["queue_file"]
        reload_check = outcome["checks"]["reload"]
        duplicate = outcome["checks"]["duplicate"]
        prepared = outcome["checks"]["prepared_update"]
        namecut = outcome["checks"]["namecut_1920"]

        if seed["laserCandidates"] != 3:
            failures.append(f"Lazer aday sayısı beklenen değil: {seed['laserCandidates']}")
        if seed["emptyLaserHasCandidate"]:
            failures.append("Boş lazer isimli kayıt aday sayıldı")
        if transfer["bulkNameCutCount"] != 2 or queue_file["rows"] != 2:
            failures.append("Kalıcı İsim Kesim kuyruğuna beklenen 2 kayıt yazılmadı")
        if transfer["prepared"] != 1 or "pending_preparation" not in queue_file["statuses"]:
            failures.append("Hazır lazer kayıt pending_preparation olarak saklanmadı")
        if transfer["review"] != 1 or "needs_review" not in queue_file["statuses"]:
            failures.append("Kontrol gerekli lazer kayıt needs_review olarak saklanmadı")
        if transfer["blockedInQueue"] or transfer["containsBlockedRow"] or transfer["containsEmptyLaserRow"]:
            failures.append("Hatalı, blocked veya boş lazer isimli kayıt kuyruğa yazıldı")
        if not transfer["sourcesOk"] or not queue_file["sourcesOk"]:
            failures.append("source/source_label Toplu Üretim standardı kalıcı yazılmadı")
        if not transfer["hasBatch"] or not queue_file["hasBatch"] or queue_file["history"] < 1:
            failures.append("transfer_batch_id veya aktarım geçmişi oluşmadı")
        if reload_check["restored"] != 2 or not reload_check["hasBulkBadge"]:
            failures.append("State reset sonrası kalıcı kayıtlar İsim Kesim ekranına geri yüklenmedi")
        if duplicate["bulkNameCutCount"] != 2 or duplicate["duplicate"] < 2:
            failures.append("Kalıcı duplicate kontrolü state reset sonrası çalışmadı")
        prepared_status = str(prepared.get("status", "")).upper()
        if prepared_status:
            if prepared_status != "PREPARED":
                failures.append(f"Hazırlandı durum güncellemesi beklenen değil: {prepared_status}")
        else:
            failures.append("Hazırlandı durum güncellemesi sonuç üretmedi")
        if not namecut["hasBulkBadge"] or not namecut["hasHistory"]:
            failures.append("İsim Kesim ekranında kaynak rozeti veya aktarım geçmişi görünmedi")
        if transfer["hasAutoStartText"] or not namecut["hasSafetyText"]:
            failures.append("Yazıcı/lazer/RDWorks güvenlik dili bozuldu")

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
        restore_files(snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
