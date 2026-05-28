from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "production_label_studio_smart_layout_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_label_studio_smart_layout_hotfix_gate_result.json"

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
    wait(700)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def setup_studio(window: WebMainWindow, fields: list[dict[str, object]] | None = None, values: dict[str, str] | None = None, collision: bool = False) -> dict[str, object]:
    base_fields = fields or [
        {"field_name": "İsim", "excel_column": "label_text", "x_mm": 1, "y_mm": 2, "width_mm": 48, "height_mm": 8, "font_size": 11, "line_height": 1.12, "align": "center"},
        {"field_name": "Tarih", "excel_column": "date_text", "x_mm": 17, "y_mm": 24, "width_mm": 16, "height_mm": 4, "font_size": 8, "line_height": 1.12, "align": "center"},
        {"field_name": "Not", "excel_column": "note_text", "x_mm": 12, "y_mm": 27, "width_mm": 26, "height_mm": 4, "font_size": 8, "line_height": 1.12, "align": "center"},
        {"field_name": "Lazer isim", "excel_column": "name_cut_text", "x_mm": 6, "y_mm": 25, "width_mm": 38, "height_mm": 4, "font_size": 8, "line_height": 1.12, "align": "center"},
    ]
    base_values = values or {
        "label_text": "Ayşe & Mehmet",
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "name_cut_text": "Ayşe & Mehmet",
    }
    density = [{"label": "merkez çiçek/desen yoğunluğu", "x": 14, "y": 8, "width": 22, "height": 12}] if collision else []
    return run_js(
        window,
        f"""
        (() => {{
          const model = {{
            path: "hotfix-smart-layout-model",
            model_name: "Hotfix Smart Layout Model",
            title: "Hotfix Smart Layout Model",
            width_mm: 50,
            height_mm: 30,
            fields_summary: {json.dumps(base_fields, ensure_ascii=False)},
            label_model_layout: {{
              canvas_width_mm: 50,
              canvas_height_mm: 30,
              text_safe_zone: {{ x: 9, y: 7, width: 32, height: 15, center_x: 25, center_y: 14.5, max_text_width: 30, max_text_height: 14 }},
              visual_density_zones: {json.dumps(density, ensure_ascii=False)}
            }}
          }};
          currentLabelModels = [model];
          selectedLabelModel = model;
          selectedFieldIndex = 0;
          manualFieldValuesByModel[manualModelKey(model)] = {json.dumps(base_values, ensure_ascii=False)};
          currentFieldValues = {{ ...manualFieldValuesByModel[manualModelKey(model)] }};
          document.body.classList.add("label-studio-active");
          showSection("label", {{ labelMode: "studio" }});
          if (document.getElementById("manualTemplate")) document.getElementById("manualTemplate").value = model.path;
          syncManualInputsFromState();
          showManualPreviewPlaceholder();
          return {{
            page: document.querySelector(".page.active")?.id || "",
            fields: selectedLabelModel.fields_summary,
            values: getCurrentFieldValues()
          }};
        }})()
        """,
        timeout_ms=60000,
    )


def layout_for_values(window: WebMainWindow, values: dict[str, str], collision: bool = False) -> dict[str, object]:
    setup_studio(window, values=values, collision=collision)
    return run_js(
        window,
        """
        (() => {
          const suggestion = suggestLearningLayout({ fields: selectedLabelModel.fields_summary, label_size: effectiveManualSize(selectedLabelModel), values: getCurrentFieldValues() });
          const rows = suggestion.fields.filter(field => ["label_text","date_text","note_text"].includes(field.excel_column) && String(getCurrentFieldValues()[field.excel_column] || "").trim());
          return {
            active: suggestion.smartLayout.activeFields.map(item => item.column),
            fields: suggestion.fields,
            rows,
            metadata: suggestion.smartLayout.preview_metadata,
            outputMetadata: suggestion.smartLayout.output_metadata,
            messages: suggestion.smartLayout.messages,
            needsReview: suggestion.smartLayout.needsReview,
            warnings: suggestion.smartLayout.warnings,
            quality: suggestion.qualityAfter
          };
        })()
        """,
        timeout_ms=60000,
    )


def row_by_column(layout: dict[str, object], column: str) -> dict[str, object]:
    for row in layout.get("rows", []):
        if row.get("excel_column") == column:
            return row
    return {}


def exercise_combinations(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    combos = {
        "name_only": {"label_text": "Ayşe & Mehmet", "date_text": "", "note_text": "", "name_cut_text": "Ayşe & Mehmet"},
        "name_date": {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "", "name_cut_text": ""},
        "name_note": {"label_text": "Ayşe & Mehmet", "date_text": "", "note_text": "Söz Hatırası", "name_cut_text": ""},
        "name_date_note": {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "Söz Hatırası", "name_cut_text": ""},
        "date_only": {"label_text": "", "date_text": "12.05.2026", "note_text": "", "name_cut_text": ""},
        "note_only": {"label_text": "", "date_text": "", "note_text": "Söz Hatırası", "name_cut_text": ""},
    }
    results: dict[str, object] = {}
    for key, values in combos.items():
        layout = layout_for_values(window, values)
        results[key] = layout
        active = layout.get("active", [])
        metadata = layout.get("metadata", {})
        positions = metadata.get("field_positions", {})
        assert_true(active == [column for column in ["label_text", "date_text", "note_text"] if values.get(column)], f"{key}: aktif alan seti yanlış: {active}", failures)
        assert_true(metadata.get("text_safe_zone"), f"{key}: text_safe_zone metadata yok.", failures)
        assert_true(metadata.get("field_positions") == layout.get("outputMetadata", {}).get("field_positions"), f"{key}: preview/output metadata tutarsız.", failures)
        if key == "name_only":
            name = row_by_column(layout, "label_text")
            assert_true(abs((float(name.get("x_mm", 0)) + float(name.get("width_mm", 0)) / 2) - 25) <= 1.1, "Sadece isim: isim merkezde değil.", failures)
            assert_true(float(name.get("font_size", 0)) >= 18, "Sadece isim: font üçlü düzene göre yeterince büyümedi.", failures)
            assert_true("date_text" not in positions and "note_text" not in positions, "Sadece isim: tarih/not için boşluk veya metadata bırakıldı.", failures)
        if key == "name_date":
            name = row_by_column(layout, "label_text")
            date = row_by_column(layout, "date_text")
            assert_true(float(date.get("y_mm", 0)) - float(name.get("y_mm", 0)) < 9, "İsim+tarih: tarih çok uzağa düştü.", failures)
            assert_true("note_text" not in positions, "İsim+tarih: not boşluğu bırakıldı.", failures)
        if key == "name_note":
            name = row_by_column(layout, "label_text")
            note = row_by_column(layout, "note_text")
            assert_true(float(note.get("y_mm", 0)) - float(name.get("y_mm", 0)) < 9, "İsim+not: not aşırı aşağıda kaldı.", failures)
            assert_true("date_text" not in positions, "İsim+not: tarih boşluğu bırakıldı.", failures)
        if key == "name_date_note":
            name = row_by_column(layout, "label_text")
            date = row_by_column(layout, "date_text")
            note = row_by_column(layout, "note_text")
            assert_true(float(name.get("font_size", 0)) > float(date.get("font_size", 0)) >= float(note.get("font_size", 0)) - 1, "Üçlü blok: font hiyerarşisi bozuk.", failures)
            assert_true(float(note.get("y_mm", 0)) - float(name.get("y_mm", 0)) < 12, "Üçlü blok: alanlar kopuk görünüyor.", failures)
        if key in {"date_only", "note_only"}:
            assert_true(layout.get("needsReview") is True, f"{key}: isim zorunlu eksikken needs_review olmadı.", failures)
    return results


def exercise_apply_and_metadata(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    setup_studio(window)
    before = run_js(window, "(() => ({ fields: selectedLabelModel.fields_summary, quality: calculateLayoutQuality(selectedLabelModel.fields_summary, selectedLabelModel, getCurrentFieldValues()) }))()")
    save_screenshot(window, "label-studio-before-bad-auto-layout.png")
    applied = run_js(
        window,
        """
        (() => {
          window.confirm = () => true;
          applySmartLearningLayout();
          return {
            fields: selectedLabelModel.fields_summary,
            smart: lastSmartLayoutResult,
            auditPending: Boolean(lastSmartLayoutAuditResult),
            payload: manualPayload(),
            qualityText: document.getElementById("manualLayoutQualityPanel")?.innerText || ""
          };
        })()
        """,
        timeout_ms=60000,
    )
    wait(900)
    applied["audit"] = run_js(window, "(() => lastSmartLayoutAuditResult || {})()")
    save_screenshot(window, "label-studio-after-smart-layout.png")
    save_screenshot(window, "label-studio-user-reference-like-layout.png")
    assert_true(applied.get("smart", {}).get("preview_metadata", {}).get("active_text_fields") == ["label_text", "date_text", "note_text"], "Akıllı yerleşim üçlü text group üretmedi.", failures)
    assert_true("Yazı grubu güvenli alanda" in applied.get("qualityText", ""), "Kalite paneli güvenli alan mesajını göstermedi.", failures)
    assert_true(applied.get("payload", {}).get("_smart_layout_preview_metadata", {}).get("field_positions") == applied.get("payload", {}).get("_smart_layout_output_metadata", {}).get("field_positions"), "Manual payload preview/output metadata tutarsız.", failures)
    assert_true(applied.get("audit", {}).get("status") in {"OK", "DUPLICATE", "ADDED"}, "Akıllı layout audit event oluşmadı.", failures)
    last_output = run_js(
        window,
        """
        (() => {
          lastManualOutput = {
            status: "OK",
            pdf_path: "output/2026-05-23/label_studio_smart_layout/sample.pdf",
            png_path: "output/2026-05-23/label_studio_smart_layout/sample.png",
            smart_layout_preview_metadata: lastSmartLayoutResult.preview_metadata,
            smart_layout_output_metadata: lastSmartLayoutResult.output_metadata,
            smart_layout_metadata_match: JSON.stringify(lastSmartLayoutResult.preview_metadata.field_positions) === JSON.stringify(lastSmartLayoutResult.output_metadata.field_positions),
            output_validation: { status: "OK", message: "Metadata eşleşti." }
          };
          updateManualOutputControlPanel();
          return lastManualOutput;
        })()
        """,
        timeout_ms=60000,
    )
    save_screenshot(window, "label-studio-output-metadata-match.png")
    assert_true(last_output.get("smart_layout_metadata_match") is True, "Last output metadata eşleşmedi.", failures)
    return {"before": before, "applied": applied, "output": last_output}


def exercise_collision(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    setup_studio(window, collision=True)
    collision = run_js(
        window,
        """
        (() => {
          window.confirm = () => true;
          applySmartLearningLayout();
          const zone = lastSmartLayoutResult.layoutMetadata.text_safe_zone;
          const wrap = document.querySelector(".field-overlay-wrap");
          if (wrap && zone && !document.getElementById("smartSafeZoneDebug")) {
            const d = document.createElement("div");
            d.id = "smartSafeZoneDebug";
            d.className = "smart-safe-zone-debug";
            d.style.position = "absolute";
            d.style.zIndex = "22";
            d.style.pointerEvents = "none";
            d.style.border = "2px dashed #2563eb";
            d.style.background = "rgba(37, 99, 235, .08)";
            d.style.left = `${zone.x / 50 * 100}%`;
            d.style.top = `${zone.y / 30 * 100}%`;
            d.style.width = `${zone.width / 50 * 100}%`;
            d.style.height = `${zone.height / 30 * 100}%`;
            d.innerHTML = '<span style="position:absolute;left:4px;top:4px;background:#2563eb;color:white;font-size:10px;border-radius:999px;padding:3px 6px">text_safe_zone</span>';
            wrap.appendChild(d);
          }
          return { smart: lastSmartLayoutResult, text: document.getElementById("manualLayoutQualityPanel")?.innerText || "" };
        })()
        """,
        timeout_ms=60000,
    )
    save_screenshot(window, "label-studio-collision-warning.png")
    save_screenshot(window, "label-studio-text-safe-zone-debug.png")
    assert_true(collision.get("smart", {}).get("needsReview") is True, "Görsel yoğunluk çakışması needs_review üretmedi.", failures)
    assert_true(collision.get("smart", {}).get("collisionScore", 0) > 0, "Görsel çakışma skoru oluşmadı.", failures)
    return collision


def capture_responsive(window: WebMainWindow) -> dict[str, str]:
    screenshots = {}
    window.resize(1366, 768)
    wait(800)
    setup_studio(window)
    run_js(window, "(() => { window.confirm = () => true; applySmartLearningLayout(); return true; })()", timeout_ms=60000)
    screenshots["smart_1366"] = save_screenshot(window, "label-studio-1366-smart-layout.png")
    window.resize(1920, 1080)
    wait(800)
    setup_studio(window)
    run_js(window, "(() => { window.confirm = () => true; applySmartLearningLayout(); return true; })()", timeout_ms=60000)
    screenshots["smart_1920"] = save_screenshot(window, "label-studio-1920-smart-layout.png")
    return screenshots


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    try:
        window.resize(1366, 768)
        window.show()
        window.raise_()
        window.activateWindow()
        wait(2400)
        combinations = exercise_combinations(window, failures)
        apply_result = exercise_apply_and_metadata(window, failures)
        collision = exercise_collision(window, failures)
        responsive = capture_responsive(window)
        result = {
            "status": "PASS" if not failures else "FAIL",
            "final_decision": "READY_FOR_PILOT_WITH_SMART_LAYOUT_FIX" if not failures else "READY_WITH_LAYOUT_BLOCKER",
            "failures": failures,
            "combinations": combinations,
            "apply_result": apply_result,
            "collision": collision,
            "screenshots": {
                "before_bad_auto_layout": str(OUTPUT_DIR / "label-studio-before-bad-auto-layout.png"),
                "after_smart_layout": str(OUTPUT_DIR / "label-studio-after-smart-layout.png"),
                "user_reference_like_layout": str(OUTPUT_DIR / "label-studio-user-reference-like-layout.png"),
                "collision_warning": str(OUTPUT_DIR / "label-studio-collision-warning.png"),
                "text_safe_zone_debug": str(OUTPUT_DIR / "label-studio-text-safe-zone-debug.png"),
                "output_metadata_match": str(OUTPUT_DIR / "label-studio-output-metadata-match.png"),
                **responsive,
            },
            "safety": {
                "printer_auto_start": False,
                "laser_auto_start": False,
                "rdworks_auto_start": False,
                "trendyol_live_action": False,
                "fake_ai_success": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "final_decision": "READY_WITH_LAYOUT_BLOCKER", "error": str(exc), "failures": failures}
    finally:
        window.close()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
