from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_print_queue_hardening_phase13"
RESULT_PATH = OUTPUT_DIR / "production_print_queue_hardening_phase13_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import print_queue_api  # noqa: E402


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


def write_minimal_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace("(", "[").replace(")", "]")
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 160] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 68 >> stream
BT /F1 14 Tf 24 90 Td ({safe_title}) Tj 0 -22 Td (CeyizHome Lab Phase 13) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000360 00000 n 
trailer << /Root 1 0 R /Size 6 >>
startxref
430
%%EOF
"""
    path.write_text(pdf, encoding="latin-1")


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def seed_queue() -> dict[str, object]:
    queue_path = print_queue_api.queue_path(PROJECT_ROOT)
    original = queue_path.read_text(encoding="utf-8") if queue_path.exists() else ""
    output_dir = PROJECT_ROOT / "output" / "2026-05-21" / "phase13"
    outputs = {
        "label": output_dir / "label_studio_ayse_mehmet.pdf",
        "bulk": output_dir / "bulk_yagmur_efe.pdf",
        "manual": output_dir / "manual_mustafa_yagmur.pdf",
        "trendyol": output_dir / "trendyol_helin_cemal.pdf",
        "namecut": output_dir / "namecut_export_control.pdf",
    }
    for key, path in outputs.items():
        write_minimal_pdf(path, key)
    queue_path.write_text("[]", encoding="utf-8")
    seeded = []
    rows = [
        {
            "job_name": "Etiket Studio - Ayşe & Mehmet",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "origin_source": "bulk_production",
            "origin_source_label": "Toplu Üretim",
            "source_item_id": "phase13-label-source",
            "customer_name": "Ayşe Yılmaz",
            "order_no": "LS-13",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe & Mehmet",
            "quantity": "2",
            "relative_path": relative(outputs["label"]),
            "file_type": "PDF",
            "batch_id": "PH13-A",
            "duplicate_key": "label_studio:phase13-label-source",
        },
        {
            "job_name": "Toplu Üretim - Yağmur & Efe",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "phase13-bulk-source",
            "bulk_row_id": "42",
            "customer_name": "Yağmur Efe",
            "order_no": "BULK-42",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Yağmur & Efe",
            "quantity": "4",
            "relative_path": relative(outputs["bulk"]),
            "file_type": "PDF",
            "batch_id": "PH13-B",
            "duplicate_key": "bulk_production:phase13-bulk-source",
        },
        {
            "job_name": "Manuel Etiket - Mustafa & Yağmur",
            "source": "manual_label",
            "source_label": "Manuel Etiket",
            "source_item_id": "phase13-manual-source",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Mustafa Kemal & Yağmur",
            "quantity": "1",
            "relative_path": relative(outputs["manual"]),
            "file_type": "PDF",
            "batch_id": "PH13-C",
            "duplicate_key": "manual_label:phase13-manual-source",
        },
        {
            "job_name": "Trendyol - Helin Cemal",
            "source": "trendyol",
            "source_label": "Trendyol",
            "source_item_id": "phase13-trendyol-source",
            "customer_name": "Helin Cemal",
            "order_no": "TY-13001",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Helin Cemal",
            "quantity": "3",
            "relative_path": relative(outputs["trendyol"]),
            "file_type": "PDF",
            "batch_id": "PH13-D",
            "duplicate_key": "trendyol:phase13-trendyol-source",
        },
        {
            "job_name": "İsim Kesim Export Kontrol",
            "source": "laser",
            "source_label": "İsim Kesim",
            "source_item_id": "phase13-namecut-source",
            "model_name": "01 A Gold Lazer Kesim",
            "label_text": "Ayşe Mehmet Lazer",
            "quantity": "2",
            "relative_path": relative(outputs["namecut"]),
            "file_type": "PDF",
            "batch_id": "PH13-E",
            "duplicate_key": "laser:phase13-namecut-source",
        },
        {
            "job_name": "Eksik Çıktı",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "phase13-missing-output",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Eksik Dosya",
            "quantity": "2",
            "relative_path": "output/2026-05-21/phase13/missing_output.pdf",
            "file_type": "PDF",
            "batch_id": "PH13-F",
            "duplicate_key": "bulk_production:phase13-missing-output",
        },
        {
            "job_name": "Blocked Kayıt",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "source_item_id": "phase13-blocked",
            "model_name": "",
            "label_text": "Model Yok",
            "quantity": "0",
            "relative_path": "",
            "file_type": "PDF",
            "status": "Üretime Engel",
            "status_key": "blocked",
            "batch_id": "PH13-G",
            "duplicate_key": "label_studio:phase13-blocked",
        },
    ]
    for row in rows:
        seeded.append(print_queue_api.add_to_print_queue(PROJECT_ROOT, row))
    duplicate = print_queue_api.add_to_print_queue(PROJECT_ROOT, rows[0])
    return {"original": original, "queue_path": queue_path, "seeded": seeded, "duplicate": duplicate}


def restore_queue(seed: dict[str, object]) -> None:
    queue_path = seed["queue_path"]
    original = seed["original"]
    if isinstance(queue_path, Path):
        if original:
            queue_path.write_text(str(original), encoding="utf-8")
        elif queue_path.exists():
            queue_path.unlink()


def inspect_backend(seed: dict[str, object]) -> dict[str, object]:
    rows = print_queue_api.list_print_queue(PROJECT_ROOT)
    by_source = {row.get("source", ""): row for row in rows}
    missing = next(row for row in rows if row.get("source_item_id") == "phase13-missing-output")
    blocked = next(row for row in rows if row.get("source_item_id") == "phase13-blocked")
    ready_rows = [row for row in rows if row.get("status_key") == "ready_to_print"]
    printed = print_queue_api.mark_queue_item_printed(PROJECT_ROOT, ready_rows[0]["id"])
    requeued = print_queue_api.mark_queue_item_pending(PROJECT_ROOT, ready_rows[0]["id"])
    safe_ready = print_queue_api.print_queue_item_safe(PROJECT_ROOT, ready_rows[1]["id"])
    safe_missing = print_queue_api.print_queue_item_safe(PROJECT_ROOT, missing["id"])
    rows_after = print_queue_api.list_print_queue(PROJECT_ROOT)
    history_row = next(row for row in rows_after if row.get("id") == ready_rows[0]["id"])
    return {
        "row_count": len(rows),
        "sources": sorted(by_source.keys()),
        "duplicate_status": seed["duplicate"].get("status") if isinstance(seed.get("duplicate"), dict) else "",
        "ready_count": len(ready_rows),
        "missing_status": missing.get("status_key"),
        "missing_flags": missing.get("safety_flags", []),
        "blocked_status": blocked.get("status_key"),
        "blocked_flags": blocked.get("safety_flags", []),
        "safe_ready": safe_ready,
        "safe_missing": safe_missing,
        "printed": printed,
        "requeued": requeued,
        "history_events": [entry.get("event") for entry in history_row.get("queue_history", [])],
    }


def inspect_ui(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      showSection("printQueue");
      if (typeof clearPrintQueueFilters === "function") clearPrintQueueFilters();
      if (typeof updatePrintQueue === "function") updatePrintQueue(currentState.printQueue || []);
      const rows = Array.from(document.querySelectorAll("#printQueueList .queue-job-card"));
      const detail = document.getElementById("queueDetailInfo")?.innerText || "";
      const status = document.getElementById("queueDetailStatus")?.innerText || "";
      const badges = rows.map(row => row.querySelector(".source-badge")?.innerText || "");
      const statuses = rows.map(row => row.querySelector(".queue-quality")?.innerText || "");
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        rowCount: rows.length,
        badges,
        statuses,
        hasOrigin: rows.some(row => row.innerText.includes("Origin: Toplu Üretim")),
        hasReady: document.body.innerText.includes("Yazdırmaya Hazır"),
        hasBlocked: document.body.innerText.includes("Üretime Engel"),
        hasMissingWarning: document.body.innerText.includes("Çıktı dosyası bulunamadı") || document.body.innerText.includes("Çıktı dosyası"),
        detailHasHistory: status.includes("Geçmiş Logları") || document.body.innerText.includes("Geçmiş Logları"),
        detail,
        status,
        bodyHasAutoStart: /otomatik başla(?!maz)|RDWorks otomatik başladı|lazer otomatik başladı|yazıcı otomatik başladı/i.test(document.body.innerText)
      };
    })()
    """)


def apply_filter(window: WebMainWindow, script: str) -> dict[str, object]:
    return run_js(window, f"""
    (() => {{
      {script}
      const rows = Array.from(document.querySelectorAll("#printQueueList .queue-job-card"));
      return {{
        rowCount: rows.length,
        text: document.body.innerText,
        badges: rows.map(row => row.querySelector(".source-badge")?.innerText || ""),
        statuses: rows.map(row => row.querySelector(".queue-quality")?.innerText || "")
      }};
    }})()
    """)


def open_print_modal(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """
    (() => {
      const row = (currentState.printQueue || []).find(item => item.status_key === "ready_to_print");
      if (!row) return { ok: false, reason: "ready row missing" };
      if (typeof safePrint === "function") safePrint(row.id);
      return { ok: true, id: row.id };
    })()
    """)
    wait(2200)
    return run_js(window, """
    (() => ({
      open: !document.getElementById("safePrintModal")?.hidden,
      text: document.getElementById("safePrintModal")?.innerText || "",
      bodyHasAutoStart: /otomatik başla(?!maz)|RDWorks otomatik başladı|lazer otomatik başladı|yazıcı otomatik başladı/i.test(document.body.innerText)
    }))()
    """, timeout_ms=10000)


def run_gate() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suppress_message_boxes()
    seed = seed_queue()
    app = QApplication.instance() or QApplication(sys.argv)
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    screenshots: dict[str, str] = {}
    try:
        backend = inspect_backend(seed)
        window.resize(1920, 1080)
        window.show()
        wait(2500)
        ui_1920 = inspect_ui(window)
        screenshots["overview_1920"] = save_screenshot(window, "print-queue-hardening-1920.png")
        source_filter = apply_filter(window, 'document.getElementById("queueTypeFilter").value = "bulk_production"; refreshPrintQueueFilters();')
        screenshots["source_filters"] = save_screenshot(window, "print-queue-hardening-source-filters.png")
        missing = apply_filter(window, 'document.getElementById("queueStatusFilter").value = "blocked"; refreshPrintQueueFilters();')
        screenshots["missing_output"] = save_screenshot(window, "print-queue-hardening-missing-output.png")
        apply_filter(window, 'clearPrintQueueFilters(); selectedPrintQueueIds.clear(); (currentState.printQueue || []).filter(item => ["ready_to_print","output_ready","pending"].includes(queueItemStatusKey(item, queueItemHistory(item))) && queueItemCanPrint(item, queueItemHistory(item))).slice(0, 3).forEach(item => selectedPrintQueueIds.add(item.id)); updatePrintQueue(currentState.printQueue || []);')
        screenshots["bulk_actions"] = save_screenshot(window, "print-queue-hardening-bulk-actions.png")
        modal = open_print_modal(window)
        screenshots["print_modal"] = save_screenshot(window, "print-queue-hardening-print-confirm.png")
        window.resize(1366, 768)
        wait(900)
        ui_1366 = inspect_ui(window)
        screenshots["overview_1366"] = save_screenshot(window, "print-queue-hardening-1366.png")
        history = apply_filter(window, 'clearPrintQueueFilters(); selectPrintQueueItem((currentState.printQueue || [])[0]?.id || "");')
        screenshots["history"] = save_screenshot(window, "print-queue-hardening-history-log.png")
    finally:
        window.close()
        restore_queue(seed)
    checks = {
        "backend": backend,
        "ui_1920": ui_1920,
        "source_filter": source_filter,
        "missing_output": missing,
        "print_modal": modal,
        "ui_1366": ui_1366,
        "history": history,
    }
    assertions = {
        "backend_row_count": backend["row_count"] >= 7,
        "label_studio_source": "label_studio" in backend["sources"],
        "bulk_source": "bulk_production" in backend["sources"],
        "manual_source": "manual_label" in backend["sources"],
        "trendyol_source": "trendyol" in backend["sources"],
        "laser_source": "laser" in backend["sources"],
        "duplicate_blocked": backend["duplicate_status"] == "EXISTS",
        "ready_count": backend["ready_count"] >= 5,
        "missing_blocked": backend["missing_status"] == "blocked",
        "blocked_status": backend["blocked_status"] == "blocked",
        "safe_ready_manual": backend["safe_ready"].get("status") == "MANUAL_PRINT_REQUIRED",
        "safe_missing_error": backend["safe_missing"].get("status") == "ERROR",
        "printed_history": "printed_marked" in backend["history_events"],
        "requeued_history": "requeued" in backend["history_events"],
        "ui_page": ui_1920["activePage"] == "printQueue",
        "ui_rows": ui_1920["rowCount"] >= 5,
        "ui_source_badges": all(label in " ".join(ui_1920["badges"]) for label in ["Etiket Studio", "Manuel Etiket", "Toplu Üretim", "Trendyol", "İsim Kesim"]),
        "ui_origin": bool(ui_1920["hasOrigin"]),
        "ui_ready": bool(ui_1920["hasReady"]),
        "ui_blocked": bool(ui_1920["hasBlocked"]),
        "ui_no_auto": not ui_1920["bodyHasAutoStart"],
        "source_filter_rows": source_filter["rowCount"] >= 1,
        "source_filter_badges": all(label == "Toplu Üretim" for label in source_filter["badges"]),
        "missing_rows": missing["rowCount"] >= 1,
        "missing_text": "Üretime Engel" in missing["text"],
        "modal_open": bool(modal["open"]),
        "modal_printer": "Yazıcı" in modal["text"],
        "modal_source": "Kaynak" in modal["text"] or "KAYNAK" in modal["text"],
        "modal_format": "Format" in modal["text"] or "FORMAT" in modal["text"],
        "modal_no_auto": not modal["bodyHasAutoStart"],
        "ui_1366_page": ui_1366["activePage"] == "printQueue",
        "ui_1366_no_auto": not ui_1366["bodyHasAutoStart"],
    }
    checks["assertions"] = assertions
    checks["failed_assertions"] = [key for key, ok in assertions.items() if not ok]
    return {"status": "PASSED" if all(assertions.values()) else "FAILED", "checks": checks, "screenshots": screenshots}


def main() -> None:
    result = run_gate()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result["status"] != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
