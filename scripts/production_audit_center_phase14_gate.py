from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_center_phase14"
RESULT_PATH = OUTPUT_DIR / "production_audit_center_phase14_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import name_cut_queue_api, print_queue_api, production_audit_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "production_audit_log.json",
    PROJECT_ROOT / "data" / "print_queue.json",
    PROJECT_ROOT / "data" / "name_cut_queue.json",
    PROJECT_ROOT / "data" / "name_cut_transfer_history.json",
    PROJECT_ROOT / "data" / "name_cut_export_history.json",
    PROJECT_ROOT / "data" / "production_history.json",
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


def backup_data() -> dict[Path, str | None]:
    return {path: path.read_text(encoding="utf-8") if path.exists() else None for path in DATA_FILES}


def restore_data(backup: dict[Path, str | None]) -> None:
    for path, content in backup.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def write_minimal_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace("(", "[").replace(")", "]")
    path.write_text(
        f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 160] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 64 >> stream
BT /F1 14 Tf 24 90 Td ({safe_title}) Tj 0 -22 Td (Audit Gate) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000356 00000 n 
trailer << /Root 1 0 R /Size 6 >>
startxref
426
%%EOF
""",
        encoding="latin-1",
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def seed_sources() -> None:
    for path in DATA_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data" / "production_audit_log.json").write_text("[]", encoding="utf-8")
    (PROJECT_ROOT / "data" / "print_queue.json").write_text("[]", encoding="utf-8")
    out_dir = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_center_phase14" / "seed"
    ready_pdf = out_dir / "audit_ready.pdf"
    bulk_pdf = out_dir / "audit_bulk.pdf"
    label_pdf = out_dir / "audit_label.pdf"
    export_svg = out_dir / "namecut_plate.svg"
    manifest = out_dir / "manifest.json"
    write_minimal_pdf(ready_pdf, "Audit Ready")
    write_minimal_pdf(bulk_pdf, "Audit Bulk")
    write_minimal_pdf(label_pdf, "Audit Label")
    export_svg.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='100' height='40'></svg>", encoding="utf-8")
    manifest.write_text(json.dumps({"export_batch_id": "AUDIT-EXPORT-1"}, ensure_ascii=False), encoding="utf-8")

    queue_items = [
        {
            "job_name": "Etiket Studio - Ayşe & Mehmet",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "origin_source": "bulk_production",
            "origin_source_label": "Toplu Üretim",
            "source_item_id": "audit-label-source",
            "customer_name": "Ayşe Yılmaz",
            "order_no": "LS-AUDIT-1",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Ayşe & Mehmet",
            "quantity": "2",
            "relative_path": relative(label_pdf),
            "file_type": "PDF",
            "batch_id": "AUDIT-BATCH-1",
            "duplicate_key": "label_studio:audit-label-source",
        },
        {
            "job_name": "Toplu Üretim - Yağmur & Efe",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "audit-bulk-source",
            "customer_name": "Yağmur Efe",
            "order_no": "BULK-AUDIT-42",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Yağmur & Efe",
            "quantity": "4",
            "relative_path": relative(bulk_pdf),
            "file_type": "PDF",
            "batch_id": "AUDIT-BATCH-2",
            "duplicate_key": "bulk_production:audit-bulk-source",
        },
        {
            "job_name": "Eksik Çıktı",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "audit-missing-output",
            "customer_name": "Eksik Dosya",
            "order_no": "MISS-AUDIT-1",
            "model_name": "01 A Gold Rulo Etiket",
            "label_text": "Eksik Çıktı",
            "quantity": "1",
            "relative_path": "output/2026-05-21/production_audit_center_phase14/seed/missing.pdf",
            "file_type": "PDF",
            "batch_id": "AUDIT-BATCH-3",
            "duplicate_key": "bulk_production:audit-missing-output",
        },
        {
            "job_name": "Blocked Kayıt",
            "source": "manual_label",
            "source_label": "Manuel Etiket",
            "source_item_id": "audit-blocked",
            "customer_name": "Blocked Müşteri",
            "order_no": "BLOCK-AUDIT-1",
            "model_name": "",
            "label_text": "",
            "quantity": "0",
            "relative_path": "",
            "file_type": "PDF",
            "status": "Üretime Engel",
            "status_key": "blocked",
            "batch_id": "AUDIT-BATCH-4",
            "duplicate_key": "manual_label:audit-blocked",
        },
    ]
    added = [print_queue_api.add_to_print_queue(PROJECT_ROOT, item) for item in queue_items]
    rows = print_queue_api.list_print_queue(PROJECT_ROOT)
    ready = next(row for row in rows if row.get("source_item_id") == "audit-label-source")
    print_queue_api.mark_queue_item_printed(PROJECT_ROOT, ready["id"])
    rows = print_queue_api.list_print_queue(PROJECT_ROOT)
    duplicate_row = next(row for row in rows if row.get("source_item_id") == "audit-bulk-source")
    duplicate_row.setdefault("queue_history", []).append({
        "event": "duplicate_seen",
        "status_key": duplicate_row.get("status_key"),
        "message": "Aynı iş tekrar kuyruğa eklenmeye çalışıldı.",
        "created_at": "2026-05-21 12:05:00",
    })
    print_queue_api.save_print_queue(PROJECT_ROOT, rows)

    transfer_history = [
        {
            "transfer_batch_id": "AUDIT-TRANSFER-1",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "found": 5,
            "added": 3,
            "review": 1,
            "blocked": 1,
            "duplicate": 1,
            "created_at": "2026-05-21 11:00:00",
        }
    ]
    namecut_queue = [
        {
            "id": "audit-namecut-1",
            "item_id": "audit-namecut-1",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": "77",
            "order_no": "NC-AUDIT-1",
            "customer_name": "Merve Kaya",
            "laser_name": "Merve & Ali",
            "quantity": 2,
            "label_model": "01 A Gold Rulo Etiket",
            "laser_model": "01 A Gold Lazer Kesim",
            "status": "pending_preparation",
            "safety_flags": ["turkish_mark_review"],
            "transfer_batch_id": "AUDIT-TRANSFER-1",
            "duplicate_key": "bulk_production:77:Merve & Ali",
            "created_at": "2026-05-21 11:01:00",
            "updated_at": "2026-05-21 11:01:00",
        }
    ]
    export_history = [
        {
            "export_batch_id": "AUDIT-EXPORT-1",
            "source": "name_cut",
            "source_label": "İsim Kesim",
            "status": "exported",
            "format": "SVG",
            "item_count": 1,
            "quantity_total": 2,
            "cut_direction": "mirror_horizontal",
            "manifest_path": relative(manifest),
            "exported_files": [relative(export_svg)],
            "created_at": "2026-05-21 11:20:00",
            "quality_summary": {"single_piece": "OK", "collision": "OK"},
        }
    ]
    name_cut_queue_api.save_name_cut_queue(PROJECT_ROOT, namecut_queue)
    name_cut_queue_api.save_transfer_history(PROJECT_ROOT, transfer_history)
    name_cut_queue_api.save_name_cut_export_history(PROJECT_ROOT, export_history)
    production_history = [
        {
            "id": "audit-label-output-1",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "studio_session_id": "AUDIT-STUDIO-1",
            "label_text": "Ayşe & Mehmet",
            "customer_name": "Ayşe Yılmaz",
            "order_no": "LS-AUDIT-1",
            "model_name": "01 A Gold Rulo Etiket",
            "quantity": 2,
            "pdf_path": relative(ready_pdf),
            "created_at": "2026-05-21 10:40:00",
            "output_validation": {"status": "OK"},
        }
    ]
    (PROJECT_ROOT / "data" / "production_history.json").write_text(json.dumps(production_history, ensure_ascii=False, indent=2), encoding="utf-8")
    print_queue_api.list_print_queue(PROJECT_ROOT)
    production_audit_api.rebuild_production_audit_from_existing_sources(PROJECT_ROOT)


def inspect_backend() -> dict[str, object]:
    rebuilt = production_audit_api.rebuild_production_audit_from_existing_sources(PROJECT_ROOT)
    events = production_audit_api.list_production_audit_events(PROJECT_ROOT)
    event_types = {row.get("event_type") for row in events}
    duplicate_before = len(events)
    production_audit_api.rebuild_production_audit_from_existing_sources(PROJECT_ROOT)
    duplicate_after = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    return {
        "rebuilt": rebuilt,
        "count": len(events),
        "event_types": sorted(event_types),
        "summary": production_audit_api.list_production_audit_summary(PROJECT_ROOT),
        "bulk_filter": len(production_audit_api.list_production_audit_events(PROJECT_ROOT, {"source": "bulk_production"})),
        "duplicate_filter": len(production_audit_api.list_production_audit_events(PROJECT_ROOT, {"event_type": "duplicate_detected"})),
        "blocked_filter": len(production_audit_api.list_production_audit_events(PROJECT_ROOT, {"only_blocked": True})),
        "missing_filter": len(production_audit_api.list_production_audit_events(PROJECT_ROOT, {"event_type": "output_missing"})),
        "search_order": len(production_audit_api.list_production_audit_events(PROJECT_ROOT, {"query": "BULK-AUDIT-42"})),
        "rebuild_count_before": duplicate_before,
        "rebuild_count_after": duplicate_after,
    }


def inspect_ui(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      showSection("productionAudit");
      if (typeof updateProductionAudit === "function") updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {});
      const body = document.getElementById("productionAudit")?.innerText || "";
      const cards = document.querySelectorAll("#productionAuditTimeline .audit-event-card");
      const kpis = document.querySelectorAll("#productionAuditKpis .audit-kpi");
      const detail = document.getElementById("productionAuditDetail")?.innerText || "";
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        timelineCards: cards.length,
        kpiCards: kpis.length,
        hasTitle: body.includes("Üretim Geçmişi"),
        hasSafety: body.includes("Yazıcı, lazer ve RDWorks otomatik başlamaz"),
        hasDuplicate: body.includes("Duplicate") || body.includes("tekrar"),
        hasBlocked: body.includes("Engellenen") || body.includes("Üretime engel"),
        hasMissing: body.includes("Eksik çıktı") || body.includes("Çıktı dosyası eksik"),
        hasDetail: detail.includes("Raw Metadata") && detail.includes("Event Detayı"),
        noAutoStart: !/otomatik başladı|RDWorks otomatik başladı|lazer otomatik başladı|yazıcı otomatik başladı/i.test(body)
      };
    })()
    """)


def run_gate() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suppress_message_boxes()
    backup = backup_data()
    app = QApplication.instance() or QApplication(sys.argv)
    screenshots: dict[str, str] = {}
    try:
        seed_sources()
        backend = inspect_backend()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        try:
            window.resize(1920, 1080)
            window.show()
            wait(2500)
            ui = inspect_ui(window)
            screenshots["overview_1920"] = save_screenshot(window, "audit-center-1920.png")
            screenshots["kpis"] = save_screenshot(window, "audit-center-kpi.png")
            screenshots["timeline"] = save_screenshot(window, "audit-center-timeline.png")
            table = run_js(window, """(() => { setProductionAuditView("table"); return { tableVisible: !document.getElementById("productionAuditTable")?.hidden, rows: document.querySelectorAll("#productionAuditTable tbody tr").length }; })()""")
            screenshots["table"] = save_screenshot(window, "audit-center-table.png")
            detail = run_js(window, """(() => { setProductionAuditView("timeline"); const first = (currentState.productionAudit || [])[0]; if (first) selectProductionAuditEvent(first.id); return { detail: document.getElementById("productionAuditDetail")?.innerText || "" }; })()""")
            screenshots["detail"] = save_screenshot(window, "audit-center-detail-drawer.png")
            filters = run_js(window, """(() => { document.getElementById("productionAuditSourceFilter").value = "bulk_production"; refreshProductionAuditFilters(); return { text: document.getElementById("productionAudit")?.innerText || "", cards: document.querySelectorAll("#productionAuditTimeline .audit-event-card").length }; })()""")
            screenshots["filters"] = save_screenshot(window, "audit-center-filters.png")
            duplicate_blocked = run_js(window, """(() => { clearProductionAuditFilters(); document.getElementById("productionAuditOnlyDuplicate").checked = true; refreshProductionAuditFilters(); const duplicate = document.getElementById("productionAudit")?.innerText || ""; document.getElementById("productionAuditOnlyDuplicate").checked = false; document.getElementById("productionAuditOnlyBlocked").checked = true; refreshProductionAuditFilters(); const blocked = document.getElementById("productionAudit")?.innerText || ""; return { duplicate, blocked, cards: document.querySelectorAll("#productionAuditTimeline .audit-event-card").length }; })()""")
            screenshots["duplicate_blocked"] = save_screenshot(window, "audit-center-duplicate-blocked.png")
            window.resize(1366, 768)
            wait(900)
            run_js(window, """(() => { clearProductionAuditFilters(); showSection("productionAudit"); return true; })()""")
            screenshots["overview_1366"] = save_screenshot(window, "audit-center-1366.png")
        finally:
            window.close()
    finally:
        restore_data(backup)
    assertions = {
        "backend_has_events": backend["count"] >= 7,
        "bulk_batch_event": "bulk_sent_to_namecut_queue" in backend["event_types"],
        "namecut_queue_event": "namecut_queue_created" in backend["event_types"],
        "namecut_export_event": "namecut_export_created" in backend["event_types"],
        "print_queue_event": "print_queue_created" in backend["event_types"],
        "duplicate_event": "duplicate_detected" in backend["event_types"],
        "blocked_event": "blocked_detected" in backend["event_types"],
        "missing_output_event": "output_missing" in backend["event_types"],
        "label_output_event": "label_output_created" in backend["event_types"],
        "source_filter_works": backend["bulk_filter"] >= 1,
        "duplicate_filter_works": backend["duplicate_filter"] >= 1,
        "blocked_filter_works": backend["blocked_filter"] >= 1,
        "search_works": backend["search_order"] >= 1,
        "rebuild_no_duplicates": backend["rebuild_count_before"] == backend["rebuild_count_after"],
        "ui_page": ui["activePage"] == "productionAudit",
        "ui_kpis": ui["kpiCards"] >= 8,
        "ui_timeline": ui["timelineCards"] >= 1,
        "ui_title": ui["hasTitle"],
        "ui_safety": ui["hasSafety"],
        "ui_detail": ui["hasDetail"],
        "ui_table": table["tableVisible"] and table["rows"] >= 1,
        "ui_filter": filters["cards"] >= 1,
        "ui_duplicate_text": "Duplicate" in duplicate_blocked["duplicate"] or "tekrar" in duplicate_blocked["duplicate"],
        "ui_blocked_text": "Engellenen" in duplicate_blocked["blocked"] or "Üretime engel" in duplicate_blocked["blocked"],
        "no_auto_start": ui["noAutoStart"],
    }
    return {
        "status": "PASSED" if all(assertions.values()) else "FAILED",
        "checks": {
            "backend": backend,
            "ui": ui,
            "table": table,
            "filters": filters,
            "duplicate_blocked": duplicate_blocked,
            "assertions": assertions,
            "failed_assertions": [key for key, ok in assertions.items() if not ok],
        },
        "screenshots": screenshots,
    }


def main() -> None:
    result = run_gate()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result["status"] != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
