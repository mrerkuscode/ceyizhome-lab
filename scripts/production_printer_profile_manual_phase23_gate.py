from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_printer_profile_manual_phase23"
RESULT_PATH = OUTPUT_DIR / "production_printer_profile_manual_phase23_gate_result.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import print_queue_api, printer_profile_api, production_audit_api  # noqa: E402


DATA_FILES = [
    PROJECT_ROOT / "data" / "print_queue.json",
    PROJECT_ROOT / "data" / "printer_profiles.json",
    PROJECT_ROOT / "data" / "production_audit_log.json",
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
        raise RuntimeError(f"JavaScript timed out: {script[:160]}")
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
    wait(600)
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


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def create_minimal_pdf(relative: str) -> str:
    path = PROJECT_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 180] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 18 Tf 40 100 Td (Phase 23 Test) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000242 00000 n
0000000337 00000 n
trailer << /Root 1 0 R /Size 6 >>
startxref
407
%%EOF
"""
    path.write_bytes(pdf)
    return relative


def seed_queue() -> dict[str, str]:
    ready_pdf = create_minimal_pdf("output/2026-05-22/phase23/phase23_ready.pdf")
    ready = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
        "job_name": "Phase 23 Hazır Etiket",
        "job_type": "Toplu",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "quantity": "2",
        "file_type": "PDF",
        "relative_path": ready_pdf,
        "output_path": ready_pdf,
        "model_name": "01 A Gold Rulo Etiket",
        "label_model": "01 A Gold Rulo Etiket",
        "label_text": "Ayşe & Mehmet",
        "status": "Yazdırmaya Hazır",
        "status_key": "ready_to_print",
        "duplicate_key": "phase23-ready",
    })
    missing = print_queue_api.add_to_print_queue(PROJECT_ROOT, {
        "job_name": "Phase 23 Eksik Çıktı",
        "job_type": "Toplu",
        "source": "bulk_production",
        "source_label": "Toplu Üretim",
        "quantity": "1",
        "file_type": "PDF",
        "relative_path": "output/2026-05-22/phase23/missing.pdf",
        "output_path": "output/2026-05-22/phase23/missing.pdf",
        "model_name": "01 A Gold Rulo Etiket",
        "label_text": "Eksik Dosya",
        "status": "Yazdırmaya Hazır",
        "status_key": "ready_to_print",
        "duplicate_key": "phase23-missing",
    })
    return {"ready_id": ready["id"], "missing_id": missing["id"], "ready_pdf": ready_pdf}


def run_backend_checks(window: WebMainWindow) -> dict[str, object]:
    ids = seed_queue()
    no_profile = window.prepare_manual_print(ids["ready_id"], "")
    profile_result = window.save_printer_profile({
        "profile_name": "Phase 23 Manuel Profil",
        "printer_name": "Manuel PDF kontrolü",
        "paper_size": "A4",
        "label_size": "50 x 30 mm",
        "orientation": "portrait",
        "margin": "0 mm",
        "copies_default": 2,
        "output_format_allowed": ["PDF"],
        "is_default": True,
    })
    profile = profile_result["profile"]
    missing_output = window.prepare_manual_print(ids["missing_id"], profile["printer_profile_id"])
    prepared = window.prepare_manual_print(ids["ready_id"], profile["printer_profile_id"])
    test_result = window.test_printer_profile(profile["printer_profile_id"])
    rows = print_queue_api.list_print_queue(PROJECT_ROOT)
    ready_row = next(row for row in rows if row.get("id") == ids["ready_id"])
    marked = window.mark_queue_item_printed(ids["ready_id"])
    audit_rows = production_audit_api.list_production_audit_events(PROJECT_ROOT, {})
    return {
        "ids": ids,
        "no_profile": no_profile,
        "profile_result": profile_result,
        "missing_output": missing_output,
        "prepared": prepared,
        "marked": marked,
        "test_result": test_result,
        "ready_history": [entry.get("event") for entry in ready_row.get("queue_history", [])],
        "audit_event_types": [row.get("event_type") for row in audit_rows],
        "audit_blob": json.dumps(audit_rows, ensure_ascii=False),
    }


def run_ui_checks(window: WebMainWindow, ready_id: str, missing_id: str) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1920, 1080)
    wait(800)
    result["settings"] = run_js(window, """
    (() => {
      refreshState();
      showSection('settings');
      updateSettings(currentState);
      const text = document.getElementById('settings')?.innerText || '';
      return {
        activePage: document.querySelector('.page.active')?.id || '',
        hasProfiles: /Yazıcı Profilleri/.test(text),
        hasProfileName: /Phase 23 Manuel Profil/.test(text),
        hasNoDeviceTrigger: /gerçek cihazı tetiklemez|Yazıcı otomatik çalışmaz/.test(text)
      };
    })()
    """, timeout_ms=60000)
    result["settings_screenshot"] = save_screenshot(window, "printer-profile-settings-1920.png")
    result["missing_output"] = run_js(window, f"""
    (() => {{
      showSection('printQueue');
      updatePrintQueue(currentState.printQueue || []);
      selectPrintQueueItem('{missing_id}');
      const text = document.getElementById('printQueue')?.innerText || '';
      return {{
        hasMissingOutput: /Çıktı dosyası bulunamadı|Dosya yok|Üretime Engel/.test(text),
        hasNoAutoLanguage: /Yazıcı otomatik çalışmaz/.test(text)
      }};
    }})()
    """, timeout_ms=60000)
    result["missing_output_screenshot"] = save_screenshot(window, "printer-profile-output-missing.png")
    run_js(window, f"""
    (() => {{
      showSection('printQueue');
      updatePrintQueue(currentState.printQueue || []);
      safePrint('{ready_id}');
      return {{ started: true }};
    }})()
    """, timeout_ms=60000)
    wait(1800)
    result["modal"] = run_js(window, """
    (() => {
      const text = document.getElementById('safePrintModal')?.innerText || '';
      return {
        modalOpen: !document.getElementById('safePrintModal')?.hidden,
        hasProfileSelect: Boolean(document.getElementById('safePrintProfileSelect')),
        hasApproval: Boolean(document.getElementById('safePrintOperatorApproval')),
        hasManualLanguage: /Manuel Print Hazırla|Yazıcı otomatik çalışmaz/.test(text),
        openDisabled: Boolean(document.getElementById('safePrintOpenBtn')?.disabled)
      };
    })()
    """, timeout_ms=60000)
    result["modal_screenshot"] = save_screenshot(window, "printer-profile-print-modal.png")
    result["approved_modal"] = run_js(window, """
    (() => {
      const approval = document.getElementById('safePrintOperatorApproval');
      if (approval) approval.checked = true;
      handleSafePrintApprovalChange();
      return {
        openDisabled: Boolean(document.getElementById('safePrintOpenBtn')?.disabled),
        profileValue: document.getElementById('safePrintProfileSelect')?.value || ''
      };
    })()
    """, timeout_ms=60000)
    result["approved_screenshot"] = save_screenshot(window, "printer-profile-manual-ready.png")
    result["audit"] = run_js(window, """
    (() => {
      showSection('productionAudit');
      updateProductionAudit(currentState.productionAudit || [], currentState.productionAuditSummary || {});
      const text = document.getElementById('productionAudit')?.innerText || '';
      return { hasManual: /manual_print_prepared|Manuel print/.test(text), hasPrinted: /printed_marked|Yazdırıldı/.test(text) };
    })()
    """, timeout_ms=60000)
    result["audit_screenshot"] = save_screenshot(window, "printer-profile-audit-log.png")
    window.resize(1366, 768)
    wait(600)
    result["view_1366"] = run_js(window, """
    (() => {
      showSection('printQueue');
      updatePrintQueue(currentState.printQueue || []);
      return { activePage: document.querySelector('.page.active')?.id || '', width: window.innerWidth, hasQueue: /Yazdırma Sırası/.test(document.body.innerText || '') };
    })()
    """, timeout_ms=60000)
    result["view_1366_screenshot"] = save_screenshot(window, "printer-profile-1366.png")
    return result


def main() -> int:
    suppress_message_boxes()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_data()
    failures: list[str] = []
    screenshots: dict[str, str] = {}
    try:
        app = QApplication.instance() or QApplication([])
        _ = app
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        wait(900)
        backend = run_backend_checks(window)
        ui = run_ui_checks(window, backend["ids"]["ready_id"], backend["ids"]["missing_id"])
        screenshots = {key: value for key, value in ui.items() if key.endswith("_screenshot") and isinstance(value, str)}

        assert_true(backend["no_profile"].get("status") == "PROFILE_REQUIRED", "Profil seçmeden print hazırlığı tamamlandı.", failures)
        assert_true(backend["profile_result"].get("status") == "OK", "Yazıcı profili oluşturulamadı.", failures)
        assert_true(backend["test_result"].get("status") == "UNSUPPORTED", "Test bağlantısı gerçek cihaz tetikliyor gibi görünüyor.", failures)
        assert_true(backend["missing_output"].get("status") in {"OUTPUT_MISSING", "BLOCKED", "NOT_READY"}, "Output yokken print hazırlığı engellenmedi.", failures)
        assert_true(backend["prepared"].get("status") == "OK", "Hazır kayıt manuel print hazırlığına alınamadı.", failures)
        assert_true(backend["prepared"].get("auto_print_started") is False, "Yazıcı otomatik başlamış görünüyor.", failures)
        assert_true(backend["marked"].get("status") == "OK", "Yazdırıldı işaretleme başarısız.", failures)
        assert_true("manual_print_prepared" in backend["ready_history"], "Queue history manual_print_prepared içermiyor.", failures)
        assert_true("manual_print_prepared" in backend["audit_event_types"], "Audit manual_print_prepared event içermiyor.", failures)
        assert_true("printed_marked" in backend["audit_event_types"], "Audit printed_marked event içermiyor.", failures)
        assert_true('"auto_print_started": true' not in backend["audit_blob"].lower(), "Audit otomatik print başlatılmış gibi görünüyor.", failures)
        assert_true(ui["settings"].get("hasProfiles"), "Ayarlar ekranında Yazıcı Profilleri görünmüyor.", failures)
        assert_true(ui["settings"].get("hasProfileName"), "Oluşturulan profil UI'da görünmüyor.", failures)
        assert_true(ui["missing_output"].get("hasMissingOutput"), "Output eksik uyarısı UI'da görünmüyor.", failures)
        assert_true(ui["missing_output"].get("hasNoAutoLanguage"), "Output eksik durumunda güvenlik dili kayboldu.", failures)
        assert_true(ui["modal"].get("modalOpen"), "Safe print modal açılmadı.", failures)
        assert_true(ui["modal"].get("hasProfileSelect"), "Print modal profil seçimi göstermiyor.", failures)
        assert_true(ui["modal"].get("hasApproval"), "Print modal operatör onayı göstermiyor.", failures)
        assert_true(ui["modal"].get("openDisabled"), "Operatör onayı yokken print hazırlık butonu aktif.", failures)
        assert_true(not ui["approved_modal"].get("openDisabled"), "Profil ve onay sonrası manuel hazırlık butonu aktif olmadı.", failures)
        assert_true(ui["audit"].get("hasManual") and ui["audit"].get("hasPrinted"), "Audit/log görünümü manuel print ve yazdırıldı eventlerini göstermiyor.", failures)
        assert_true(ui["view_1366"].get("hasQueue"), "1366 görünümde Yazdırma Sırası bozuldu.", failures)

        status = "PASSED" if not failures else "FAILED"
        result = {"status": status, "checks": {"backend": backend, "ui": ui}, "failures": failures, "screenshots": screenshots}
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if status == "PASSED" else 1
    finally:
        restore_data(backup)


if __name__ == "__main__":
    raise SystemExit(main())
