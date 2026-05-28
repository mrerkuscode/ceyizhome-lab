from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_namecut_safe_export_phase11"
RESULT_PATH = OUTPUT_DIR / "production_namecut_safe_export_phase11_gate_result.json"
QUEUE_PATH = PROJECT_ROOT / "data" / "name_cut_queue.json"
EXPORT_HISTORY_PATH = PROJECT_ROOT / "data" / "name_cut_export_history.json"

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


def backup_files() -> dict[Path, str | None]:
    return {
        QUEUE_PATH: QUEUE_PATH.read_text(encoding="utf-8") if QUEUE_PATH.exists() else None,
        EXPORT_HISTORY_PATH: EXPORT_HISTORY_PATH.read_text(encoding="utf-8") if EXPORT_HISTORY_PATH.exists() else None,
    }


def restore_files(snapshot: dict[Path, str | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def seed_queue_files() -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "id": "phase11-export-ready-1",
            "item_id": "phase11-export-ready-1",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": "phase11-row-1",
            "order_no": "SIP-P11-001",
            "customer_name": "Ayşe & Mehmet",
            "laser_name": "Ayşe Mehmet",
            "name_text": "Ayşe Mehmet",
            "quantity": "2",
            "label_model": "01 A Gold Rulo Etiket",
            "laser_model": "01 A Gold Lazer Kesim",
            "note": "Söz Hatırası",
            "status": "prepared",
            "warnings": [],
            "errors": [],
            "offset_mm": 0.3,
            "height_mm": "20",
            "style": "Ceyizhome Lab Script (Mochary)",
            "composition": "Tek Satır Yan Yana",
            "composition_mode": "Tek Satır Yan Yana",
            "created_at": "2026-05-21T22:10:00",
            "updated_at": "2026-05-21T22:10:00",
            "transfer_batch_id": "NCQ-P11",
            "duplicate_key": "bulk_production:phase11-row-1",
        },
        {
            "id": "phase11-export-ready-2",
            "item_id": "phase11-export-ready-2",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": "phase11-row-2",
            "order_no": "SIP-P11-002",
            "customer_name": "Yağmur & Efe",
            "laser_name": "Yağmur Efe",
            "name_text": "Yağmur Efe",
            "quantity": "1",
            "label_model": "01 A Gold Rulo Etiket",
            "laser_model": "01 A Gold Lazer Kesim",
            "note": "Nişan Hatırası",
            "status": "pending_preparation",
            "warnings": [],
            "errors": [],
            "offset_mm": 0.3,
            "height_mm": "20",
            "style": "Ceyizhome Lab Script (Mochary)",
            "composition": "Tek Satır Yan Yana",
            "composition_mode": "Tek Satır Yan Yana",
            "created_at": "2026-05-21T22:10:00",
            "updated_at": "2026-05-21T22:10:00",
            "transfer_batch_id": "NCQ-P11",
            "duplicate_key": "bulk_production:phase11-row-2",
        },
    ]
    QUEUE_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    EXPORT_HISTORY_PATH.write_text("[]", encoding="utf-8")


def show_namecut_ready(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    return run_js(window, """
    (() => {
      refreshState();
      showSection("nameCutStudio");
      nameCutLayoutConfig = {
        ...nameCutLayoutConfig,
        mirror_cut: true,
        mirror_vertical: false,
        offset_mm: 0.3,
        min_stroke_mm: 0.28,
        item_gap_mm: 1.5,
        margin_mm: 15,
        width_mm: 800,
        height_mm: 600,
        weld_inside_name: true,
        punctuation_fix: true,
        turkish_mark_bridge: true,
        dot_bridge_enabled: true
      };
      nameCutItems = nameCutItems.map(item => ({ ...item, force_needs_weld: false, force_collision_risk: false, force_detached_marks: false, force_needs_offset: false, offset_mm: 0.3, errors: [] }));
      selectedNameCutItemId = "phase11-export-ready-1";
      refreshNameCutStudioViews(currentNameCutLayout());
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        items: nameCutItems.length,
        qualities: nameCutItems.map(item => nameCutSinglePieceQuality(item, currentNameCutLayout()).status),
        direction: nameCutDirectionLabel(nameCutLayoutConfig),
        hasSafety: /RDWorks\\/lazer otomatik başlamaz|RDWorks ve lazer otomatik/.test(document.body.innerText || "")
      };
    })()
    """, timeout_ms=60000)


def open_export_modal(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      prepareNameCutFiles();
      const modal = document.getElementById("nameCutExportConfirmModal");
      const text = modal?.innerText || "";
      return {
        open: modal ? !modal.hidden : false,
        text,
        hasSvg: /SVG/.test(text),
        hasDxf: /DXF/.test(text),
        hasPdf: /PDF/.test(text),
        hasPltPassive: /PLT/.test(text) && /Henüz production backend/.test(text),
        canConfirm: !document.getElementById("nameCutExportConfirmButton")?.disabled
      };
    })()
    """, timeout_ms=60000)


def confirm_export(window: WebMainWindow) -> dict[str, object]:
    run_js(window, "(() => { confirmNameCutSafeExport(); return true; })()", timeout_ms=60000)
    wait(2000)
    return run_js(window, """
    (() => {
      const result = lastNameCutExport || {};
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      return {
        status: result.status || "",
        manifest: result.manifest_path || "",
        svg: result.svg_path || "",
        dxf: result.dxf_path || "",
        pdf: result.pdf_preview || "",
        batch: result.export_batch_id || "",
        historyRows: nameCutExportHistoryRows.length,
        queueStatuses: nameCutItems.map(item => item.status),
        exportStatus: document.getElementById("nameCutStudioExportStatus")?.innerText || "",
        hasAutoStartText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
      };
    })()
    """, timeout_ms=60000)


def read_manifest(relative_path: str) -> dict[str, object]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return {"exists": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "exists": True,
        "export_batch_id": data.get("export_batch_id"),
        "cut_direction": data.get("cut_direction"),
        "mirror_horizontal": data.get("mirror_horizontal"),
        "mirror_vertical": data.get("mirror_vertical"),
        "safe_margin_mm": data.get("safe_margin_mm"),
        "min_gap_mm": data.get("min_gap_mm"),
        "offset_mm": data.get("offset_mm"),
        "exported_files": data.get("exported_files") or {},
        "machine_automation": data.get("machine_automation") or {},
        "quality_summary": data.get("quality_summary") or {},
    }


def blocked_export_check(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      closeNameCutExportConfirmModal();
      nameCutItems = [{
        item_id: "phase11-blocked-collision",
        name_text: "Temas Riski",
        preview_text: "Temas Riski",
        quantity: "1",
        height_mm: "20",
        offset_mm: 0.3,
        force_collision_risk: true,
        status: "READY",
        errors: [],
        warnings: []
      }];
      selectedNameCutItemId = "phase11-blocked-collision";
      refreshNameCutStudioViews(currentNameCutLayout());
      prepareNameCutFiles();
      const modal = document.getElementById("nameCutExportConfirmModal");
      const text = modal?.innerText || "";
      return {
        open: modal ? !modal.hidden : false,
        disabled: !!document.getElementById("nameCutExportConfirmButton")?.disabled,
        hasCollisionWarning: /Temas/.test(text) || /collision/.test(text),
        historyRows: nameCutExportHistoryRows.length
      };
    })()
    """, timeout_ms=60000)


def offset_approval_check(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      closeNameCutExportConfirmModal();
      nameCutItems = [{
        item_id: "phase11-offset-warning",
        name_text: "Can",
        preview_text: "Can",
        quantity: "1",
        height_mm: "20",
        offset_mm: 0,
        force_needs_offset: true,
        status: "READY",
        errors: [],
        warnings: []
      }];
      selectedNameCutItemId = "phase11-offset-warning";
      refreshNameCutStudioViews(currentNameCutLayout());
      prepareNameCutFiles();
      const before = !!document.getElementById("nameCutExportConfirmButton")?.disabled;
      updateNameCutExportOffsetApproval(true);
      const after = !!document.getElementById("nameCutExportConfirmButton")?.disabled;
      return { beforeDisabled: before, afterDisabled: after, hasWarning: /Operatör onayı/.test(document.getElementById("nameCutExportConfirmModal")?.innerText || "") };
    })()
    """, timeout_ms=60000)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = backup_files()
    seed_queue_files()
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(1700)

    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    try:
        outcome["checks"]["ready_1920"] = show_namecut_ready(window, 1920, 1080)
        outcome["checks"]["modal"] = open_export_modal(window)
        outcome["screenshots"]["confirm_modal"] = save_screenshot(window, "namecut-export-confirm-modal-1920.png")

        outcome["checks"]["export"] = confirm_export(window)
        outcome["checks"]["manifest"] = read_manifest(str(outcome["checks"]["export"].get("manifest") or ""))
        outcome["screenshots"]["export_success"] = save_screenshot(window, "namecut-export-success-summary.png")
        outcome["screenshots"]["export_history"] = save_screenshot(window, "namecut-export-history.png")
        outcome["screenshots"]["manifest_detail"] = save_screenshot(window, "namecut-export-manifest-detail.png")

        outcome["checks"]["blocked"] = blocked_export_check(window)
        outcome["screenshots"]["blocked_modal"] = save_screenshot(window, "namecut-export-blocked-collision.png")

        outcome["checks"]["offset_approval"] = offset_approval_check(window)
        outcome["screenshots"]["format_options"] = save_screenshot(window, "namecut-export-format-options.png")

        outcome["checks"]["ready_1366"] = show_namecut_ready(window, 1366, 768)
        outcome["screenshots"]["namecut_1366"] = save_screenshot(window, "namecut-export-1366.png")
        outcome["checks"]["ready_1920_final"] = show_namecut_ready(window, 1920, 1080)
        outcome["screenshots"]["namecut_1920"] = save_screenshot(window, "namecut-export-1920.png")

        failures: list[str] = []
        ready = outcome["checks"]["ready_1920"]
        modal = outcome["checks"]["modal"]
        export = outcome["checks"]["export"]
        manifest = outcome["checks"]["manifest"]
        blocked = outcome["checks"]["blocked"]
        offset = outcome["checks"]["offset_approval"]

        if ready["activePage"] != "nameCutStudio" or ready["items"] < 2:
            failures.append("İsim Kesim hazır queue kayıtları yüklenmedi")
        if not modal["open"] or not modal["hasSvg"] or not modal["hasDxf"] or not modal["hasPdf"] or not modal["hasPltPassive"]:
            failures.append("Export onay modalı veya format seçenekleri eksik")
        if not modal["canConfirm"]:
            failures.append("Kalite temiz kayıtta export onayı aktif olmadı")
        if export["status"] != "OK" or not export["manifest"]:
            failures.append("Güvenli export paketi oluşmadı")
        if not manifest["exists"] or manifest["cut_direction"] != "Ayna Yatay" or not manifest["mirror_horizontal"]:
            failures.append(f"Manifest yön/ayna bilgisi hatalı: {manifest}")
        automation = manifest.get("machine_automation") or {}
        if automation.get("rdworks_auto_open") or automation.get("laser_auto_start") or automation.get("direct_print"):
            failures.append("Manifest otomatik RDWorks/lazer/yazıcı güvenliğini bozuyor")
        files = manifest.get("exported_files") or {}
        for key in ("svg", "dxf", "pdf", "manifest"):
            if not files.get(key):
                failures.append(f"Manifest exported_files.{key} eksik")
        if export["historyRows"] < 1:
            failures.append("Export history kalıcı state'e yazılmadı")
        if not all(str(status).lower() == "exported" for status in export["queueStatuses"]):
            failures.append(f"Queue status exported olmadı: {export['queueStatuses']}")
        if export["hasAutoStartText"]:
            failures.append("Otomatik yazıcı/lazer/RDWorks başlatma dili göründü")
        if not blocked["open"] or not blocked["disabled"] or not blocked["hasCollisionWarning"]:
            failures.append("Temas riski olan dizilim export için engellenmedi")
        if not offset["beforeDisabled"] or offset["afterDisabled"] or not offset["hasWarning"]:
            failures.append("Offset eksikliği operatör onayı olmadan/sonra doğru davranmadı")
        if outcome["checks"]["ready_1366"]["activePage"] != "nameCutStudio":
            failures.append("1366 görünümde İsim Kesim açılmadı")

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
