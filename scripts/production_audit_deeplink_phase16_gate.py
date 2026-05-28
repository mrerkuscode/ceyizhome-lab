from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_audit_deeplink_phase16"
RESULT_PATH = OUTPUT_DIR / "production_audit_deeplink_phase16_gate_result.json"

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


def reset_data() -> None:
    for path in DATA_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def write_minimal_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace("(", "[").replace(")", "]")
    path.write_text(
        f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 160] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 65 >> stream
BT /F1 14 Tf 24 90 Td ({safe_title}) Tj 0 -22 Td (Phase 16) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000358 00000 n 
trailer << /Root 1 0 R /Size 6 >>
startxref
428
%%EOF
""",
        encoding="latin-1",
    )


def seed_backend() -> dict[str, object]:
    seed_dir = OUTPUT_DIR / "seed"
    pdf_path = seed_dir / "phase16_queue.pdf"
    export_json = seed_dir / "audit_export_phase16.json"
    manifest = seed_dir / "manifest.json"
    write_minimal_pdf(pdf_path, "Audit Deep Link")
    export_json.parent.mkdir(parents=True, exist_ok=True)
    export_json.write_text(json.dumps({"phase": 16, "kind": "audit-export"}, indent=2), encoding="utf-8")
    manifest.write_text(json.dumps({"phase": 16, "kind": "manifest"}, indent=2), encoding="utf-8")

    queue_result = print_queue_api.add_pdf_output_to_queue(PROJECT_ROOT, rel(pdf_path))
    queue_rows = print_queue_api.list_print_queue(PROJECT_ROOT)
    queue_item = queue_rows[0] if queue_rows else {}

    namecut_payload = {
        "summary": {"transfer_batch_id": "PH16-NCQ", "total": 1},
        "items": [
            {
                "id": "ph16-namecut-1",
                "item_id": "ph16-namecut-1",
                "source": "bulk_production",
                "source_label": "Toplu Üretim",
                "bulk_row_id": "16",
                "order_no": "PH16-NC",
                "customer_name": "Derin Kaya",
                "laser_name": "Derin & Ege",
                "name_text": "Derin & Ege",
                "quantity": 1,
                "label_model": "01 A Gold Rulo Etiket",
                "status": "pending_preparation",
                "duplicate_key": "bulk_production:phase16:16",
            }
        ],
    }
    namecut_result = name_cut_queue_api.save_name_cut_queue_items(PROJECT_ROOT, namecut_payload)

    events = [
        {
            "audit_key": "phase16-print-queue",
            "event_type": "print_queue_created",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": queue_item.get("id"),
            "source_item_id": queue_item.get("source_item_id"),
            "title": "Phase 16 Print Queue",
            "status": "ready_to_print",
            "severity": "success",
            "message": "Yazdırma Sırası kaydı oluşturuldu.",
            "output_path": queue_item.get("output_path") or queue_item.get("relative_path"),
        },
        {
            "audit_key": "phase16-namecut-queue",
            "event_type": "namecut_queue_created",
            "source": "name_cut",
            "source_label": "İsim Kesim",
            "source_item_id": "ph16-namecut-1",
            "transfer_batch_id": "PH16-NCQ",
            "title": "Derin & Ege",
            "status": "pending_preparation",
            "severity": "success",
            "message": "İsim Kesim hazırlık kaydı oluşturuldu.",
        },
        {
            "audit_key": "phase16-label-output",
            "event_type": "label_output_created",
            "source": "label_studio",
            "source_label": "Etiket Studio",
            "source_item_id": "ph16-label-1",
            "title": "Ayşe & Mehmet",
            "status": "OK",
            "severity": "success",
            "message": "Etiket çıktısı oluşturuldu.",
            "output_path": rel(pdf_path),
        },
        {
            "audit_key": "phase16-bulk-namecut",
            "event_type": "bulk_sent_to_namecut_queue",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "source_item_id": "ph16-bulk-1",
            "transfer_batch_id": "PH16-NCQ",
            "batch_id": "PH16-BULK",
            "title": "Toplu Üretim lazer aktarımı",
            "status": "sent",
            "severity": "success",
            "message": "Toplu Üretim kaydı İsim Kesim hazırlık kuyruğuna gönderildi.",
        },
        {
            "audit_key": "phase16-output-missing",
            "event_type": "output_missing",
            "source": "print_queue",
            "source_label": "Yazdırma Sırası",
            "queue_item_id": "missing-print-queue-row",
            "title": "Eksik çıktı",
            "status": "blocked",
            "severity": "blocked",
            "message": "Çıktı dosyası bulunamadı.",
            "output_path": "output/2026-05-21/production_audit_deeplink_phase16/seed/missing.pdf",
        },
        {
            "audit_key": "phase16-audit-export",
            "event_type": "audit_export_created",
            "source": "production_audit",
            "source_label": "Üretim Geçmişi",
            "title": "Audit JSON export",
            "status": "exported",
            "severity": "success",
            "message": "Audit export dosyası oluşturuldu.",
            "file_path": rel(export_json),
            "metadata": {"exported_files": {"manifest": rel(manifest)}},
        },
        {
            "audit_key": "phase16-unknown",
            "event_type": "legacy_event_without_target",
            "source": "legacy",
            "source_label": "Eski kayıt",
            "title": "Bağlantısız eski kayıt",
            "status": "legacy",
            "severity": "warning",
            "message": "Bu eski kayıt hızlı geçişe bağlı değil.",
        },
    ]
    for event in events:
        production_audit_api.append_production_audit_event(PROJECT_ROOT, event)

    return {
        "queue_result": queue_result,
        "queue_item": queue_item,
        "namecut_result": namecut_result,
        "valid_file": rel(export_json),
        "manifest": rel(manifest),
    }


def inspect_ui(window: WebMainWindow) -> tuple[dict[str, object], dict[str, str]]:
    screenshots: dict[str, str] = {}
    run_js(window, """
    (() => {
      showSection("productionAudit");
      updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {});
      return true;
    })()
    """)
    wait(800)
    screenshots["detail_drawer"] = save_screenshot(window, "audit-deeplink-detail-drawer-1920.png")

    target_map = run_js(window, """
    (() => {
      const rows = currentState.productionAudit || [];
      const byType = type => rows.find(row => row.event_type === type) || {};
      return {
        print: resolveAuditEventTarget(byType("print_queue_created")).page,
        namecut: resolveAuditEventTarget(byType("namecut_queue_created")).page,
        label: resolveAuditEventTarget(byType("label_output_created")).page,
        bulkNamecut: resolveAuditEventTarget(byType("bulk_sent_to_namecut_queue")).page,
        missing: resolveAuditEventTarget(byType("output_missing")).page,
        export: resolveAuditEventTarget(byType("audit_export_created")).page,
        legacy: resolveAuditEventTarget(byType("legacy_event_without_target")).page || ""
      };
    })()
    """)

    print_focus = run_js(window, """
    (() => {
      const event = (currentState.productionAudit || []).find(row => row.event_type === "print_queue_created");
      openAuditEventTarget(event.id);
      return {
        active: document.querySelector(".page.active")?.id || "",
        selected: selectedPrintQueueItemId || "",
        text: document.getElementById("printQueue")?.innerText || ""
      };
    })()
    """)
    wait(800)
    screenshots["print_queue_focus"] = save_screenshot(window, "audit-deeplink-print-queue-focus.png")

    namecut_focus = run_js(window, """
    (() => {
      showSection("productionAudit");
      const event = (currentState.productionAudit || []).find(row => row.event_type === "namecut_queue_created");
      openAuditEventTarget(event.id);
      return {
        active: document.querySelector(".page.active")?.id || "",
        selected: selectedNameCutItemId || "",
        text: document.getElementById("nameCutStudio")?.innerText || ""
      };
    })()
    """)
    wait(800)
    screenshots["namecut_focus"] = save_screenshot(window, "audit-deeplink-namecut-focus.png")

    export_detail = run_js(window, """
    (() => {
      showSection("productionAudit");
      const event = (currentState.productionAudit || []).find(row => row.event_type === "audit_export_created");
      selectProductionAuditEvent(event.id);
      return {
        text: document.getElementById("productionAuditDetail")?.innerText || "",
        path: auditEventPath(event, "output"),
        manifest: auditEventPath(event, "manifest")
      };
    })()
    """)
    wait(600)
    screenshots["file_summary"] = save_screenshot(window, "audit-deeplink-file-actions.png")

    legacy_warning = run_js(window, """
    (() => {
      const event = (currentState.productionAudit || []).find(row => row.event_type === "legacy_event_without_target");
      openAuditEventTarget(event.id);
      return document.getElementById("productionAuditStatus")?.innerText || "";
    })()
    """)
    wait(500)
    screenshots["unlinked_warning"] = save_screenshot(window, "audit-deeplink-unlinked-warning.png")

    missing_warning = run_js(window, """
    (() => {
      showSection("productionAudit");
      const event = (currentState.productionAudit || []).find(row => row.event_type === "output_missing");
      selectProductionAuditEvent(event.id);
      runAuditFileAction(event.output_path, "reveal");
      return true;
    })()
    """)
    wait(900)
    missing_status = run_js(window, """(() => document.getElementById("productionAuditStatus")?.innerText || "")()""")
    screenshots["missing_file"] = save_screenshot(window, "audit-deeplink-missing-file-warning.png")

    window.resize(1366, 768)
    wait(800)
    run_js(window, """(() => { showSection("productionAudit"); return true; })()""")
    screenshots["overview_1366"] = save_screenshot(window, "audit-deeplink-1366.png")
    window.resize(1920, 1080)
    wait(800)
    screenshots["overview_1920"] = save_screenshot(window, "audit-deeplink-1920.png")

    return {
        "target_map": target_map,
        "print_focus": print_focus,
        "namecut_focus": namecut_focus,
        "export_detail": export_detail,
        "legacy_warning": legacy_warning,
        "missing_warning_called": bool(missing_warning),
        "missing_status": missing_status,
    }, screenshots


def run_gate() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suppress_message_boxes()
    backup = backup_data()
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        reset_data()
        seed = seed_backend()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        try:
            window.resize(1920, 1080)
            window.show()
            wait(2500)
            ui, screenshots = inspect_ui(window)
            file_checks = {
                "valid_reveal": window.reveal_file_in_folder(seed["valid_file"]),
                "missing_reveal": window.reveal_file_in_folder("output/2026-05-21/production_audit_deeplink_phase16/seed/missing.pdf"),
                "traversal_reveal": window.reveal_file_in_folder("../outside.json"),
            }
        finally:
            window.close()
    finally:
        restore_data(backup)

    assertions = {
        "print_target": ui["target_map"]["print"] == "printQueue",
        "namecut_target": ui["target_map"]["namecut"] == "nameCutStudio",
        "label_target": ui["target_map"]["label"] == "label",
        "bulk_namecut_target": ui["target_map"]["bulkNamecut"] == "nameCutStudio",
        "missing_target": ui["target_map"]["missing"] == "printQueue",
        "unlinked_no_fake_success": ui["target_map"]["legacy"] == "" and "bulunamadı" in ui["legacy_warning"],
        "print_focus": ui["print_focus"]["active"] == "printQueue" and bool(ui["print_focus"]["selected"]),
        "namecut_focus": ui["namecut_focus"]["active"] == "nameCutStudio" and ui["namecut_focus"]["selected"] == "ph16-namecut-1",
        "export_file_buttons": "Klasörde Göster" in ui["export_detail"]["text"] and "Dosya Yolunu Kopyala" in ui["export_detail"]["text"],
        "manifest_detected": ui["export_detail"]["manifest"].endswith("manifest.json"),
        "missing_file_error": "bulunamadı" in ui["missing_status"],
        "valid_reveal_ok": file_checks["valid_reveal"].get("status") == "OK",
        "missing_reveal_error": file_checks["missing_reveal"].get("status") == "ERROR",
        "path_traversal_blocked": file_checks["traversal_reveal"].get("status") == "ERROR",
        "no_auto_start": "otomatik başlamaz" in json.dumps(ui, ensure_ascii=False).lower() or "otomatik" in json.dumps(ui, ensure_ascii=False).lower(),
    }
    return {
        "status": "PASSED" if all(assertions.values()) else "FAILED",
        "checks": {
            "ui": ui,
            "file_checks": file_checks,
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
