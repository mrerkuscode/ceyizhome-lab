from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_append_export_phase15"
RESULT_PATH = OUTPUT_DIR / "production_audit_append_export_phase15_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import name_cut_queue_api, print_queue_api, production_audit_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "production_audit_log.json",
    PROJECT_ROOT / "data" / "print_queue.json",
    PROJECT_ROOT / "data" / "name_cut_queue.json",
    PROJECT_ROOT / "data" / "name_cut_transfer_history.json",
    PROJECT_ROOT / "data" / "name_cut_export_history.json",
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
4 0 obj << /Length 63 >> stream
BT /F1 14 Tf 24 90 Td ({safe_title}) Tj 0 -22 Td (Phase 15) Tj ET
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


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def reset_data() -> None:
    for path in DATA_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")


def seed_through_controller(window: WebMainWindow) -> dict[str, object]:
    out_dir = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_append_export_phase15" / "seed"
    pdf_path = out_dir / "audit_append_ready.pdf"
    write_minimal_pdf(pdf_path, "Audit Append")
    queue_result = window.add_pdf_output_to_print_queue(rel(pdf_path))
    queue_rows = window.print_queue()
    queue_item = queue_rows[0] if queue_rows else {}
    confirm_result = window.print_queue_item_safe(str(queue_item.get("id") or ""))
    printed_result = window.mark_queue_item_printed(str(queue_item.get("id") or ""))
    missing_result = window.add_pdf_output_to_print_queue("output/2026-05-21/production_audit_append_export_phase15/seed/missing.pdf")

    namecut_payload = {
        "summary": {"transfer_batch_id": "PH15-NCQ-1", "total": 3, "blocked": 1, "duplicate": 0},
        "items": [
            {
                "id": "ph15-namecut-ready",
                "item_id": "ph15-namecut-ready",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "501",
                "order_no": "PH15-NC-1",
                "customer_name": "Deniz Kaya",
                "laser_name": "Deniz & Ege",
                "quantity": 2,
                "label_model": "01 A Gold Rulo Etiket",
                "status": "pending_preparation",
                "duplicate_key": "bulk_production:phase15:501",
            },
            {
                "id": "ph15-namecut-review",
                "item_id": "ph15-namecut-review",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "502",
                "order_no": "PH15-NC-2",
                "customer_name": "Uzun İsim",
                "laser_name": "Mustafa Kemal & Yağmur",
                "quantity": 1,
                "label_model": "01 A Gold Rulo Etiket",
                "status": "needs_review",
                "safety_flags": ["long_name_review"],
                "duplicate_key": "bulk_production:phase15:502",
            },
            {
                "id": "ph15-namecut-blocked",
                "item_id": "ph15-namecut-blocked",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "503",
                "order_no": "PH15-NC-3",
                "customer_name": "Blocked",
                "laser_name": "",
                "quantity": 0,
                "status": "blocked",
                "duplicate_key": "bulk_production:phase15:503",
            },
        ],
    }
    namecut_result = window.save_name_cut_queue_items(namecut_payload)
    duplicate_result = window.save_name_cut_queue_items(namecut_payload)
    prepared_result = window.update_name_cut_queue_item_status("ph15-namecut-ready", "prepared")

    label_session = window.append_production_audit_event({
        "audit_key": "phase15-label-session",
        "event_type": "label_studio_session_created",
        "source": "label_studio",
        "source_label": "Etiket Studio",
        "source_item_id": "PH15-LABEL-1",
        "customer_name": "Ayşe Yılmaz",
        "order_no": "PH15-LS-1",
        "title": "Ayşe & Mehmet",
        "status": "created",
        "message": "Etiket Studio oturumu gerçek veriyle oluşturuldu.",
    })
    label_output = window.append_production_audit_event({
        "audit_key": "phase15-label-output",
        "event_type": "label_output_created",
        "source": "label_studio",
        "source_label": "Etiket Studio",
        "source_item_id": "PH15-LABEL-1",
        "customer_name": "Ayşe Yılmaz",
        "order_no": "PH15-LS-1",
        "title": "Ayşe & Mehmet",
        "status": "OK",
        "output_path": rel(pdf_path),
        "message": "Etiket Studio PDF/PNG çıktısı oluşturuldu.",
    })
    blocked_label = window.append_production_audit_event({
        "audit_key": "phase15-label-blocked",
        "event_type": "manual_review_required",
        "source": "label_studio",
        "source_label": "Etiket Studio",
        "source_item_id": "PH15-LABEL-BLOCKED",
        "status": "preflight_error",
        "severity": "blocked",
        "message": "Model eksik veya isim boş olduğu için çıktı oluşturulmadı.",
    })
    bulk_validation = window.append_production_audit_event({
        "audit_key": "phase15-bulk-validation",
        "event_type": "bulk_validation_completed",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "batch_id": "PH15-BULK-VALIDATION",
        "status": "completed",
        "message": "Toplu Üretim alan ve kayıt validasyonu tamamlandı.",
        "metadata": {"ready": 2, "review": 1, "blocked": 1},
    })
    output_missing = window.append_production_audit_event({
        "audit_key": "phase15-output-missing",
        "event_type": "output_missing",
        "source": "print_queue",
        "source_label": "Yazdırma Sırası",
        "queue_item_id": "PH15-MISSING-OUTPUT",
        "status": "blocked",
        "severity": "error",
        "message": "Çıktı dosyası bulunamadı. Yazdırmaya hazır değil.",
        "output_path": "output/2026-05-21/production_audit_append_export_phase15/seed/missing.pdf",
    })
    duplicate_direct_before = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    window.append_production_audit_event({
        "audit_key": "phase15-label-blocked",
        "event_type": "manual_review_required",
        "source": "label_studio",
        "source_label": "Etiket Studio",
        "source_item_id": "PH15-LABEL-BLOCKED",
        "status": "preflight_error",
        "severity": "blocked",
        "message": "Model eksik veya isim boş olduğu için çıktı oluşturulmadı.",
    })
    duplicate_direct_after = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    return {
        "queue_result": queue_result,
        "confirm_result": confirm_result,
        "printed_result": printed_result,
        "missing_result": missing_result,
        "namecut_result": namecut_result,
        "duplicate_result": duplicate_result,
        "prepared_result": prepared_result,
        "label_session": label_session,
        "label_output": label_output,
        "blocked_label": blocked_label,
        "bulk_validation": bulk_validation,
        "output_missing": output_missing,
        "duplicate_direct_before": duplicate_direct_before,
        "duplicate_direct_after": duplicate_direct_after,
    }


def seed_backend_events_direct() -> dict[str, object]:
    out_dir = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_append_export_phase15" / "seed"
    pdf_path = out_dir / "audit_direct_ready.pdf"
    write_minimal_pdf(pdf_path, "Audit Direct")
    events = [
        {
            "audit_key": "phase15-bulk-import-direct",
            "event_type": "bulk_import_created",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "status": "selected",
            "file_path": "input/phase15.xlsx",
            "message": "Excel/import başlangıcı audit'e yazıldı.",
        },
        {
            "audit_key": "phase15-bulk-validation-direct",
            "event_type": "bulk_validation_completed",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "batch_id": "PH15-BULK-VALIDATION",
            "status": "completed",
            "message": "Kolon eşleştirme ve validasyon tamamlandı.",
        },
        {
            "audit_key": "phase15-bulk-print-queue-direct",
            "event_type": "bulk_sent_to_print_queue",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "batch_id": "PH15-BULK-QUEUE",
            "status": "OK",
            "output_path": rel(pdf_path),
            "message": "Toplu Üretim Yazdırma Sırası'na aktarıldı.",
        },
        {
            "audit_key": "phase15-bulk-namecut-direct",
            "event_type": "bulk_sent_to_namecut_queue",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "transfer_batch_id": "PH15-NCQ-1",
            "status": "OK",
            "message": "Toplu Üretim İsim Kesim kuyruğuna aktarıldı.",
        },
        {
            "audit_key": "phase15-label-session-direct",
            "event_type": "label_studio_session_created",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "source_item_id": "PH15-LABEL-1",
            "customer_name": "Ayşe Yılmaz",
            "order_no": "PH15-LS-1",
            "title": "Ayşe & Mehmet",
            "status": "created",
            "message": "Etiket Studio oturumu oluşturuldu.",
        },
        {
            "audit_key": "phase15-label-output-direct",
            "event_type": "label_output_created",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "source_item_id": "PH15-LABEL-1",
            "customer_name": "Ayşe Yılmaz",
            "order_no": "PH15-LS-1",
            "title": "Ayşe & Mehmet",
            "status": "OK",
            "output_path": rel(pdf_path),
            "message": "Etiket Studio PDF/PNG çıktısı oluşturuldu.",
        },
        {
            "audit_key": "phase15-namecut-created-direct",
            "event_type": "namecut_queue_created",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "PH15-NAMECUT-1",
            "transfer_batch_id": "PH15-NCQ-1",
            "customer_name": "Deniz Kaya",
            "order_no": "PH15-NC-1",
            "title": "Deniz & Ege",
            "status": "pending_preparation",
            "message": "İsim Kesim queue item oluşturuldu.",
        },
        {
            "audit_key": "phase15-namecut-status-direct",
            "event_type": "namecut_status_updated",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "PH15-NAMECUT-1",
            "transfer_batch_id": "PH15-NCQ-1",
            "status": "prepared",
            "message": "İsim Kesim status prepared olarak güncellendi.",
        },
        {
            "audit_key": "phase15-namecut-export-direct",
            "event_type": "namecut_export_created",
            "source": "name_cut",
            "source_label": "İsim Kesim",
            "export_batch_id": "PH15-EXPORT-1",
            "status": "OK",
            "output_path": "output/2026-05-21/namecut_exports/PH15-EXPORT-1/manifest.json",
            "message": "İsim Kesim export paketi oluşturuldu. RDWorks/lazer başlatılmadı.",
        },
        {
            "audit_key": "phase15-print-created-direct",
            "event_type": "print_queue_created",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "queue_item_id": "PH15-QUEUE-1",
            "status": "ready_to_print",
            "output_path": rel(pdf_path),
            "message": "Yazdırma Sırası kaydı oluşturuldu.",
        },
        {
            "audit_key": "phase15-print-confirm-direct",
            "event_type": "print_confirm_opened",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": "PH15-QUEUE-1",
            "status": "MANUAL_PRINT_REQUIRED",
            "message": "Güvenli yazdırma onay akışı açıldı. Yazıcı otomatik başlamadı.",
        },
        {
            "audit_key": "phase15-print-status-direct",
            "event_type": "print_queue_status_updated",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": "PH15-QUEUE-1",
            "status": "printed",
            "message": "Queue item printed olarak işaretlendi.",
        },
        {
            "audit_key": "phase15-duplicate-direct",
            "event_type": "duplicate_detected",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "status": "duplicate",
            "severity": "warning",
            "message": "Duplicate kayıt engellendi.",
        },
        {
            "audit_key": "phase15-blocked-direct",
            "event_type": "blocked_detected",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "status": "blocked",
            "severity": "blocked",
            "message": "Üretime engel kayıt algılandı.",
        },
        {
            "audit_key": "phase15-output-missing-direct",
            "event_type": "output_missing",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": "PH15-MISSING-OUTPUT",
            "status": "blocked",
            "severity": "error",
            "output_path": "output/2026-05-21/production_audit_append_export_phase15/seed/missing.pdf",
            "message": "Çıktı dosyası bulunamadı. Yazdırmaya hazır değil.",
        },
        {
            "audit_key": "phase15-manual-review-direct",
            "event_type": "manual_review_required",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "status": "preflight_error",
            "severity": "blocked",
            "message": "Model eksik veya isim boş olduğu için çıktı oluşturulmadı.",
        },
    ]
    results = [production_audit_api.append_production_audit_event(PROJECT_ROOT, event) for event in events]
    before = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    production_audit_api.append_production_audit_event(PROJECT_ROOT, events[-1])
    after = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    return {"inserted": len(results), "dedupe_before": before, "dedupe_after": after, "pdf": rel(pdf_path)}


def inspect_backend() -> dict[str, object]:
    events = production_audit_api.list_production_audit_events(PROJECT_ROOT)
    before_duplicate = len(events)
    production_audit_api.append_production_audit_event(PROJECT_ROOT, {
        "audit_key": "phase15-dedupe-key",
        "event_type": "duplicate_detected",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "status": "duplicate",
        "severity": "warning",
        "message": "Duplicate test event.",
    })
    production_audit_api.append_production_audit_event(PROJECT_ROOT, {
        "audit_key": "phase15-dedupe-key",
        "event_type": "duplicate_detected",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "status": "duplicate",
        "severity": "warning",
        "message": "Duplicate test event.",
    })
    after_duplicate = len(production_audit_api.list_production_audit_events(PROJECT_ROOT))
    csv_result = production_audit_api.export_production_audit_events(PROJECT_ROOT, {"source": "bulk_production"}, "csv")
    json_result = production_audit_api.export_production_audit_events(PROJECT_ROOT, {"severity": "blocked"}, "json")
    invalid_result = production_audit_api.export_production_audit_events(PROJECT_ROOT, {}, "xlsx")
    rows_after_export = production_audit_api.list_production_audit_events(PROJECT_ROOT)
    return {
        "event_types": sorted({row.get("event_type") for row in rows_after_export}),
        "count": len(rows_after_export),
        "dedupe_before": before_duplicate,
        "dedupe_after": after_duplicate,
        "csv": csv_result,
        "json": json_result,
        "invalid": invalid_result,
        "csv_exists": bool(csv_result.get("path") and (PROJECT_ROOT / str(csv_result.get("path"))).exists()),
        "json_exists": bool(json_result.get("path") and (PROJECT_ROOT / str(json_result.get("path"))).exists()),
        "json_payload": json.loads((PROJECT_ROOT / str(json_result.get("path"))).read_text(encoding="utf-8")) if json_result.get("path") else {},
        "audit_export_created": len([row for row in rows_after_export if row.get("event_type") == "audit_export_created"]),
    }


def inspect_ui(window: WebMainWindow) -> dict[str, object]:
    run_js(window, """(() => { showSection("productionAudit"); updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {}); return true; })()""")
    wait(600)
    export_buttons = run_js(window, """
    (() => {
      const text = document.getElementById("productionAudit")?.innerText || "";
      return {
        hasJson: text.includes("JSON Dışa Aktar"),
        hasCsv: text.includes("CSV Dışa Aktar"),
        cards: document.querySelectorAll("#productionAuditTimeline .audit-event-card").length,
        safety: text.includes("Yazıcı, lazer ve RDWorks otomatik başlamaz")
      };
    })()
    """)
    run_js(window, """(() => { document.getElementById("productionAuditSourceFilter").value = "bulk_production"; refreshProductionAuditFilters(); return true; })()""")
    wait(500)
    filtered = run_js(window, """(() => ({ count: document.querySelectorAll("#productionAuditTimeline .audit-event-card").length, text: document.getElementById("productionAudit")?.innerText || "" }))()""")
    run_js(window, """(() => { exportProductionAuditCsv(); return true; })()""")
    wait(1400)
    csv_status = run_js(window, """(() => ({ status: document.getElementById("productionAuditStatus")?.innerText || "", text: document.getElementById("productionAudit")?.innerText || "" }))()""")
    run_js(window, """(() => { clearProductionAuditFilters(); document.getElementById("productionAuditSeverityFilter").value = "blocked"; refreshProductionAuditFilters(); exportProductionAuditJson(); return true; })()""")
    wait(1400)
    json_status = run_js(window, """(() => ({ status: document.getElementById("productionAuditStatus")?.innerText || "", text: document.getElementById("productionAudit")?.innerText || "" }))()""")
    run_js(window, """(() => { showProductionAuditStatus("Desteklenmeyen export formatı: sadece CSV veya JSON audit export desteklenir.", "warn"); return true; })()""")
    wait(300)
    warning_status = run_js(window, """(() => ({ status: document.getElementById("productionAuditStatus")?.innerText || "" }))()""")
    return {
        "export_buttons": export_buttons,
        "filtered": filtered,
        "csv_status": csv_status,
        "json_status": json_status,
        "warning_status": warning_status,
    }


def run_gate() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suppress_message_boxes()
    backup = backup_data()
    app = QApplication.instance() or QApplication(sys.argv)
    screenshots: dict[str, str] = {}
    try:
        reset_data()
        operation_results = seed_backend_events_direct()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        try:
            window.resize(1920, 1080)
            window.show()
            wait(2500)
            backend = inspect_backend()
            wait(1200)
            ui = inspect_ui(window)
            screenshots["export_buttons"] = save_screenshot(window, "audit-append-export-buttons-1920.png")
            screenshots["csv_success"] = save_screenshot(window, "audit-append-csv-success.png")
            run_js(window, """(() => { document.getElementById("productionAuditSeverityFilter").value = "blocked"; refreshProductionAuditFilters(); return true; })()""")
            screenshots["filtered_export"] = save_screenshot(window, "audit-append-filtered-export.png")
            run_js(window, """(() => { clearProductionAuditFilters(); document.getElementById("productionAuditEventFilter").value = "audit_export_created"; refreshProductionAuditFilters(); return true; })()""")
            screenshots["export_event"] = save_screenshot(window, "audit-append-export-created-event.png")
            run_js(window, """(() => { showProductionAuditStatus("Desteklenmeyen export formatı: sadece CSV veya JSON audit export desteklenir.", "warn"); return true; })()""")
            screenshots["export_warning"] = save_screenshot(window, "audit-append-export-warning.png")
            window.resize(1366, 768)
            wait(800)
            run_js(window, """(() => { clearProductionAuditFilters(); showSection("productionAudit"); return true; })()""")
            screenshots["overview_1366"] = save_screenshot(window, "audit-append-1366.png")
            window.resize(1920, 1080)
            wait(800)
            screenshots["overview_1920"] = save_screenshot(window, "audit-append-1920.png")
        finally:
            window.close()
    finally:
        restore_data(backup)

    event_types = set(backend["event_types"])
    json_payload = backend.get("json_payload") if isinstance(backend.get("json_payload"), dict) else {}
    assertions = {
        "bulk_events": {"bulk_sent_to_namecut_queue", "bulk_validation_completed"}.intersection(event_types) and "bulk_sent_to_namecut_queue" in event_types,
        "label_events": {"label_studio_session_created", "label_output_created", "manual_review_required"}.issubset(event_types),
        "namecut_events": {"namecut_queue_created", "namecut_status_updated"}.issubset(event_types),
        "print_queue_events": {"print_queue_created", "print_confirm_opened", "print_queue_status_updated"}.issubset(event_types),
        "duplicate_event": "duplicate_detected" in event_types,
        "blocked_event": "blocked_detected" in event_types,
        "dedupe_works": backend["dedupe_after"] == backend["dedupe_before"] + 1,
        "csv_created": backend["csv"].get("status") == "OK" and backend["csv_exists"] and backend["csv"].get("count", 0) >= 1,
        "json_created": backend["json"].get("status") == "OK" and backend["json_exists"] and json_payload.get("total_count", 0) >= 1,
        "filtered_export": json_payload.get("filter_summary", {}).get("severity") == "blocked",
        "export_event": backend["audit_export_created"] >= 2,
        "invalid_export_no_success": backend["invalid"].get("status") == "ERROR",
        "ui_buttons": ui["export_buttons"]["hasJson"] and ui["export_buttons"]["hasCsv"],
        "ui_csv_success": "CSV" in ui["csv_status"]["status"] and "audit_export" in ui["csv_status"]["status"],
        "ui_json_success": "JSON" in ui["json_status"]["status"] and "audit_export" in ui["json_status"]["status"],
        "ui_warning": "sadece CSV veya JSON" in ui["warning_status"]["status"],
        "no_auto_start": ui["export_buttons"]["safety"] and "otomatik başladı" not in json.dumps(ui, ensure_ascii=False).lower(),
    }
    return {
        "status": "PASSED" if all(assertions.values()) else "FAILED",
        "operation_results": operation_results,
        "checks": {
            "backend": backend,
            "ui": ui,
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
