from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-22" / "production_namecut_rdworks_export_phase21"
RESULT_PATH = OUTPUT_DIR / "production_namecut_rdworks_export_phase21_gate_result.json"
QUEUE_PATH = PROJECT_ROOT / "data" / "name_cut_queue.json"
EXPORT_HISTORY_PATH = PROJECT_ROOT / "data" / "name_cut_export_history.json"
AUDIT_PATH = PROJECT_ROOT / "data" / "production_audit_log.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    wait(600)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def backup_files() -> dict[Path, str | None]:
    return {
        QUEUE_PATH: QUEUE_PATH.read_text(encoding="utf-8") if QUEUE_PATH.exists() else None,
        EXPORT_HISTORY_PATH: EXPORT_HISTORY_PATH.read_text(encoding="utf-8") if EXPORT_HISTORY_PATH.exists() else None,
        AUDIT_PATH: AUDIT_PATH.read_text(encoding="utf-8") if AUDIT_PATH.exists() else None,
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
    rows = [
        {
            "id": "phase21-ready-1",
            "item_id": "phase21-ready-1",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": "phase21-row-1",
            "order_no": "P21-001",
            "customer_name": "Ayşe Mehmet",
            "laser_name": "Ayşe Mehmet",
            "name_text": "Ayşe Mehmet",
            "quantity": "2",
            "label_model": "01 A Gold Rulo Etiket",
            "laser_model": "01 A Gold Lazer Kesim",
            "status": "prepared",
            "offset_mm": 0.35,
            "height_mm": "20",
            "style": "Ceyizhome Lab Script (Mochary)",
            "composition": "Tek Satır Yan Yana",
            "composition_mode": "Tek Satır Yan Yana",
            "warnings": [],
            "errors": [],
            "duplicate_key": "bulk_production:phase21-row-1",
        },
        {
            "id": "phase21-ready-2",
            "item_id": "phase21-ready-2",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": "phase21-row-2",
            "order_no": "P21-002",
            "customer_name": "Yağmur Efe",
            "laser_name": "Yağmur Efe",
            "name_text": "Yağmur Efe",
            "quantity": "1",
            "label_model": "01 A Gold Rulo Etiket",
            "laser_model": "01 A Gold Lazer Kesim",
            "status": "prepared",
            "offset_mm": 0.35,
            "height_mm": "20",
            "style": "Ceyizhome Lab Script (Mochary)",
            "composition": "Tek Satır Yan Yana",
            "composition_mode": "Tek Satır Yan Yana",
            "warnings": [],
            "errors": [],
            "duplicate_key": "bulk_production:phase21-row-2",
        },
    ]
    QUEUE_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    EXPORT_HISTORY_PATH.write_text("[]", encoding="utf-8")
    AUDIT_PATH.write_text("[]", encoding="utf-8")


def export_items() -> list[dict[str, object]]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def export_config(**overrides: object) -> dict[str, object]:
    base = {
        "export_batch_id": overrides.pop("export_batch_id", "P21-EXPORT-READY"),
        "operator": "CeyizHome Lab QA",
        "formats": ["svg", "dxf", "pdf", "plt"],
        "mirror_cut": True,
        "mirror_vertical": False,
        "cut_direction": "Ayna Yatay",
        "width_mm": 800,
        "height_mm": 600,
        "target_name_width_mm": 80,
        "target_name_height_mm": 40,
        "target_gap_mm": 1,
        "margin_mm": 15,
        "item_gap_mm": 1,
        "row_gap_mm": 1,
        "joined_name_gap_mm": 1,
        "offset_mm": 0.35,
        "font_family": "Ceyizhome Lab Script (Mochary)",
        "quality_summary": {"ready_single_piece": 2, "total": 2},
        "operator_approved_offset_warning": False,
    }
    base.update(overrides)
    return base


def read_manifest(relative_path: str) -> dict[str, object]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return {"exists": False}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(relative_path: str) -> str:
    path = PROJECT_ROOT / relative_path
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def run_backend_checks(window: WebMainWindow) -> dict[str, object]:
    items = export_items()
    checks: dict[str, object] = {}
    checks["needs_weld_block"] = window.prepare_name_cut_files(items, export_config(
        export_batch_id="P21-NEEDS-WELD",
        quality_summary={"needs_weld": 1, "ready_single_piece": 1, "total": 2},
    ))
    checks["detached_marks_block"] = window.prepare_name_cut_files(items, export_config(
        export_batch_id="P21-DETACHED",
        quality_summary={"detached_marks": 1, "ready_single_piece": 1, "total": 2},
    ))
    checks["collision_block"] = window.prepare_name_cut_files(items, export_config(
        export_batch_id="P21-COLLISION",
        quality_summary={"collision_risk": 1, "ready_single_piece": 1, "total": 2},
    ))
    checks["needs_offset_without_approval"] = window.prepare_name_cut_files(items, export_config(
        export_batch_id="P21-OFFSET-BLOCK",
        quality_summary={"needs_offset": 1, "ready_single_piece": 1, "total": 2},
        offset_mm=0,
        operator_approved_offset_warning=False,
    ))
    checks["needs_offset_with_approval"] = window.prepare_name_cut_files(items, export_config(
        export_batch_id="P21-OFFSET-APPROVED",
        quality_summary={"needs_offset": 1, "ready_single_piece": 1, "total": 2},
        offset_mm=0,
        operator_approved_offset_warning=True,
    ))
    ready = window.prepare_name_cut_files(items, export_config())
    manifest = read_manifest(str(ready.get("manifest_path") or ""))
    svg_text = read_text(str(ready.get("svg_path") or ""))
    dxf_text = read_text(str(ready.get("dxf_path") or ""))
    checks["ready_export"] = ready
    checks["manifest"] = {
        "exists": bool(manifest),
        "export_batch_id": manifest.get("export_batch_id"),
        "unit": manifest.get("unit"),
        "plate_size_mm": manifest.get("plate_size_mm"),
        "table_width_mm": manifest.get("table_width_mm"),
        "table_height_mm": manifest.get("table_height_mm"),
        "target_name_width_mm": manifest.get("target_name_width_mm"),
        "target_name_height_mm": manifest.get("target_name_height_mm"),
        "target_gap_mm": manifest.get("target_gap_mm"),
        "cut_direction": manifest.get("cut_direction"),
        "mirror_horizontal": manifest.get("mirror_horizontal"),
        "mirror_vertical": manifest.get("mirror_vertical"),
        "offset_mm": manifest.get("offset_mm"),
        "min_gap_mm": manifest.get("min_gap_mm"),
        "safe_margin_mm": manifest.get("safe_margin_mm"),
        "single_piece_quality": manifest.get("single_piece_quality"),
        "weld_status": manifest.get("weld_status"),
        "detached_marks_status": manifest.get("detached_marks_status"),
        "collision_check": manifest.get("collision_check"),
        "file_list": manifest.get("file_list"),
        "source_items": manifest.get("source_records"),
        "rdworks_qa": manifest.get("rdworks_compatibility_qa"),
        "machine_automation": manifest.get("machine_automation"),
    }
    checks["file_checks"] = {
        "svg_exists": bool(ready.get("svg_path")) and (PROJECT_ROOT / str(ready.get("svg_path"))).exists(),
        "dxf_exists": bool(ready.get("dxf_path")) and (PROJECT_ROOT / str(ready.get("dxf_path"))).exists(),
        "pdf_exists": bool(ready.get("pdf_preview")) and (PROJECT_ROOT / str(ready.get("pdf_preview"))).exists(),
        "plt_empty": not bool((manifest.get("file_list") or {}).get("plt")),
        "svg_has_path": "<path" in svg_text,
        "dxf_has_polyline": "POLYLINE" in dxf_text,
        "no_svg_guides": not any(token in svg_text for token in ("GUIDE_PREVIEW", "CALIBRATION", "selection-box", "data-ui-helper", "namecut-selection-frame", "rdworks-board-label", "safe margin")),
        "no_dxf_guides": not any(token in dxf_text for token in ("GUIDE_PREVIEW", "CALIBRATION", "selection-box", "data-ui-helper", "namecut-selection-frame", "rdworks-board-label", "safe margin")),
    }
    audit_rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8")) if AUDIT_PATH.exists() else []
    checks["audit_event_types"] = sorted({row.get("event_type") for row in audit_rows})
    checks["queue_statuses"] = [row.get("status") for row in json.loads(QUEUE_PATH.read_text(encoding="utf-8"))]
    return checks


def run_ui_checks(window: WebMainWindow) -> dict[str, object]:
    result: dict[str, object] = {}
    window.resize(1920, 1080)
    wait(600)
    result["open_1920"] = run_js(window, """
    (() => {
      refreshState();
      showSection("nameCutStudio");
      selectedNameCutItemId = "phase21-ready-1";
      nameCutLayoutConfig = {
        ...nameCutLayoutConfig,
        mirror_cut: true,
        mirror_vertical: false,
        offset_mm: 0.35,
        item_gap_mm: 1,
        row_gap_mm: 1,
        joined_name_gap_mm: 1,
        target_gap_mm: 1,
        target_name_width_mm: 80,
        target_name_height_mm: 40,
        width_mm: 800,
        height_mm: 600,
        weld_inside_name: true,
        punctuation_fix: true,
        turkish_mark_bridge: true,
        dot_bridge_enabled: true
      };
      refreshNameCutStudioViews(currentNameCutLayout());
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        text: document.getElementById("nameCutStudio")?.innerText || "",
        direction: nameCutDirectionLabel(nameCutLayoutConfig),
        hasTargetSize: /80\\s*x\\s*40\\s*mm/.test(document.getElementById("nameCutStudio")?.innerText || ""),
        hasOneMmGap: /Min/.test(document.getElementById("nameCutStudio")?.innerText || "") && /1\\s*mm/.test(document.getElementById("nameCutStudio")?.innerText || ""),
        hasSafety: /RDWorks.*otomatik başlamaz|lazer otomatik/.test(document.body.innerText || "")
      };
    })()
    """, timeout_ms=60000)
    result["screenshot_1920"] = save_screenshot(window, "namecut-rdworks-export-1920.png")
    result["quality_lock"] = run_js(window, """
    (() => {
      nameCutItems = nameCutItems.map((item, index) => index === 0 ? { ...item, force_needs_weld: true } : item);
      refreshNameCutStudioViews(currentNameCutLayout());
      prepareNameCutFiles();
      const modal = document.getElementById("nameCutExportConfirmModal");
      const text = modal?.innerText || "";
      const disabled = !!document.getElementById("nameCutExportConfirmButton")?.disabled;
      nameCutItems = nameCutItems.map(item => ({ ...item, force_needs_weld: false, force_collision_risk: false, force_detached_marks: false, force_needs_offset: false, offset_mm: 0.35 }));
      return { open: modal ? !modal.hidden : false, disabled, text };
    })()
    """, timeout_ms=60000)
    result["screenshot_quality_lock"] = save_screenshot(window, "namecut-quality-lock.png")
    result["modal_ready"] = run_js(window, """
    (() => {
      closeNameCutExportConfirmModal();
      refreshNameCutStudioViews(currentNameCutLayout());
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
    result["screenshot_modal"] = save_screenshot(window, "namecut-export-confirm-modal.png")
    result["success_panel"] = run_js(window, """
    (() => {
      closeNameCutExportConfirmModal();
      lastNameCutExport = {
        status: "OK",
        manifest_path: "output/2026-05-22/namecut_exports/P21-EXPORT-READY/manifest.json",
        svg_path: "output/2026-05-22/namecut_exports/P21-EXPORT-READY/plate_1.svg",
        dxf_path: "output/2026-05-22/namecut_exports/P21-EXPORT-READY/plate_1.dxf",
        pdf_preview: "output/2026-05-22/namecut_exports/P21-EXPORT-READY/plate_1.pdf",
        png_preview: "output/2026-05-22/namecut_exports/P21-EXPORT-READY/preview.png",
        rdworks_compatibility_qa: {
          status: "PASSED",
          checks: { scale_preserved: true, no_ui_helper_geometry: true, cut_paths_only: true }
        }
      };
      renderNameCutExportPanel(combinedProductionState);
      const text = document.getElementById("nameCutStudioExportPanel")?.innerText || document.getElementById("nameCutExportPanel")?.innerText || "";
      return {
        hasQa: /RDWorks QA/.test(text),
        hasSvg: /SVG/.test(text),
        hasPdf: /PDF/.test(text),
        hasPltPassive: /PLT/.test(text) && /Henüz production backend/.test(text),
        hasSafety: /RDWorks.*otomatik açılmaz|lazer otomatik/.test(text)
      };
    })()
    """, timeout_ms=60000)
    result["screenshot_success"] = save_screenshot(window, "namecut-export-svg-pdf-success.png")
    result["screenshot_manifest"] = save_screenshot(window, "namecut-export-manifest-detail.png")
    window.resize(1366, 768)
    wait(600)
    result["ui_1366"] = run_js(window, """
    (() => {
      showSection("nameCutStudio");
      refreshNameCutStudioViews(currentNameCutLayout());
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        text: document.getElementById("nameCutStudio")?.innerText || "",
        bodyHasAutoStart: /yazıcı otomatik başladı|lazer otomatik başladı|RDWorks açıldı/i.test(document.body.innerText || "")
      };
    })()
    """, timeout_ms=60000)
    result["screenshot_1366"] = save_screenshot(window, "namecut-rdworks-export-1366.png")
    return result


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = backup_files()
    outcome = {
        "status": "FAILED",
        "checks": {},
        "screenshots": {},
        "failures": [],
    }
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window: WebMainWindow | None = None
    try:
        seed_queue_files()
        window = WebMainWindow(PROJECT_ROOT, sys.executable)
        window.show()
        wait(1200)
        backend = run_backend_checks(window)
        ui = run_ui_checks(window)
        outcome["checks"] = {"backend": backend, "ui": ui}
        outcome["screenshots"] = {
            key: value for key, value in ui.items() if key.startswith("screenshot_")
        }

        failures: list[str] = []
        assert_true(str(backend["needs_weld_block"].get("status")) == "ERROR", "Tek parça/weld geçmeyen kayıt export oldu.", failures)
        assert_true(str(backend["detached_marks_block"].get("status")) == "ERROR", "Kopuk nokta/işaret kayıt export oldu.", failures)
        assert_true(str(backend["collision_block"].get("status")) == "ERROR", "Temas riski olan nesting export oldu.", failures)
        assert_true(str(backend["needs_offset_without_approval"].get("status")) == "ERROR", "Offset onayı olmadan needs_offset export oldu.", failures)
        assert_true(str(backend["needs_offset_with_approval"].get("status")) == "OK", "Offset operatör onaylı export oluşmadı.", failures)
        assert_true(str(backend["ready_export"].get("status")) == "OK", "Hazır tek parça kayıt export olmadı.", failures)
        files = backend["file_checks"]
        assert_true(files["svg_exists"] and files["pdf_exists"], "SVG/PDF gerçek dosya oluşmadı.", failures)
        assert_true(files["dxf_exists"], "DXF gerçek destekli dosya oluşmadı.", failures)
        assert_true(files["plt_empty"], "PLT sahte dosya yolu üretildi.", failures)
        assert_true(files["svg_has_path"] and files["dxf_has_polyline"], "SVG/DXF kesim path/polyline içermiyor.", failures)
        assert_true(files["no_svg_guides"] and files["no_dxf_guides"], "Export dosyasında UI yardımcı çizgisi/selection box var.", failures)
        manifest = backend["manifest"]
        assert_true(manifest["plate_size_mm"] == {"width": 800, "height": 600}, "Manifest plate 800x600 mm degil.", failures)
        assert_true(manifest["table_width_mm"] == 800 and manifest["table_height_mm"] == 600, "Manifest table_width/table_height 800x600 degil.", failures)
        assert_true(manifest["target_name_width_mm"] == 80 and manifest["target_name_height_mm"] == 40, "Manifest hedef isim olcusu 80x40 degil.", failures)
        assert_true(manifest["target_gap_mm"] == 1 and manifest["min_gap_mm"] == 1, "Manifest hedef/min bosluk 1 mm degil.", failures)
        assert_true(manifest["unit"] == "mm", "Manifest unit mm değil.", failures)
        assert_true(manifest["cut_direction"] == "Ayna Yatay", "Ayna/düz yön manifestte tutarsız.", failures)
        assert_true(manifest["mirror_horizontal"] is True and manifest["mirror_vertical"] is False, "Mirror bilgisi manifestte hatalı.", failures)
        assert_true(manifest["single_piece_quality"] == "PASSED", "Manifest tek parça kalitesi PASSED değil.", failures)
        assert_true(manifest["weld_status"] == "PASSED", "Manifest weld status PASSED değil.", failures)
        assert_true(manifest["detached_marks_status"] == "PASSED", "Manifest detached marks status PASSED değil.", failures)
        assert_true(manifest["collision_check"] == "PASSED", "Manifest collision check PASSED değil.", failures)
        assert_true((manifest["rdworks_qa"] or {}).get("status") == "PASSED", "RDWorks QA PASSED değil.", failures)
        automation = manifest["machine_automation"] or {}
        assert_true(automation.get("rdworks_auto_open") is False and automation.get("laser_auto_start") is False and automation.get("direct_print") is False, "Manifest otomatik makine güvenliğini bozuyor.", failures)
        events = set(backend["audit_event_types"])
        for event_type in {
            "namecut_export_preflight_passed",
            "namecut_export_preflight_failed",
            "namecut_export_created",
            "namecut_export_format_skipped",
            "namecut_export_manifest_created",
        }:
            assert_true(event_type in events, f"Audit event eksik: {event_type}", failures)
        assert_true(ui["modal_ready"]["hasSvg"] and ui["modal_ready"]["hasDxf"] and ui["modal_ready"]["hasPdf"], "Export modalında SVG/DXF/PDF görünmüyor.", failures)
        assert_true(ui["modal_ready"]["hasPltPassive"], "PLT pasif/uyarılı görünmüyor.", failures)
        assert_true(ui["success_panel"]["hasQa"], "RDWorks QA sonucu UI'da görünmüyor.", failures)
        assert_true(not ui["ui_1366"]["bodyHasAutoStart"], "UI'da otomatik yazıcı/lazer/RDWorks başlatma dili göründü.", failures)

        outcome["failures"] = failures
        outcome["status"] = "PASSED" if not failures else "FAILED"
    except Exception as exc:  # noqa: BLE001
        outcome["status"] = "FAILED"
        outcome["failures"].append(str(exc))
    finally:
        RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        if window is not None:
            window.close()
        restore_files(snapshot)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0 if outcome["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
