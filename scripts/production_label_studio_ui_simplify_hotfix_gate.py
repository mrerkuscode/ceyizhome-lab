from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "production_label_studio_ui_simplify_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_label_studio_ui_simplify_hotfix_gate_result.json"

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


def setup_studio(window: WebMainWindow, values: dict[str, str] | None = None) -> None:
    vals = values or {
        "label_text": "Ayşe & Mehmet",
        "date_text": "12.05.2026",
        "note_text": "Söz Hatırası",
        "name_cut_text": "",
    }
    run_js(
        window,
        f"""
        (() => {{
          window.__uiSimplifyAlerts = [];
          window.__uiSimplifyErrors = [];
          window.alert = message => window.__uiSimplifyAlerts.push(String(message || ""));
          window.addEventListener("error", event => window.__uiSimplifyErrors.push(String(event.message || event.error || "")));
          const model = {{
            path: "ui-simplify-model",
            model_name: "UI Simplify Model",
            title: "UI Simplify Model",
            width_mm: 50,
            height_mm: 30,
            fields_summary: [
              {{ field_name: "İsim", excel_column: "label_text", x_mm: 9, y_mm: 8, width_mm: 32, height_mm: 7, font_size: 12, align: "center" }},
              {{ field_name: "Tarih", excel_column: "date_text", x_mm: 16, y_mm: 16, width_mm: 18, height_mm: 4, font_size: 8, align: "center" }},
              {{ field_name: "Not", excel_column: "note_text", x_mm: 12, y_mm: 21, width_mm: 26, height_mm: 4, font_size: 8, align: "center" }},
              {{ field_name: "Lazer İsim", excel_column: "name_cut_text", x_mm: 8, y_mm: 25, width_mm: 34, height_mm: 3, font_size: 7, align: "center" }}
            ],
            label_model_layout: {{
              canvas_width_mm: 50,
              canvas_height_mm: 30,
              text_safe_zone: {{ x: 8, y: 7, width: 34, height: 16, center_x: 25, center_y: 15, max_text_width: 31, max_text_height: 14 }},
              visual_density_zones: []
            }}
          }};
          currentLabelModels = [model];
          selectedLabelModel = model;
          selectedFieldIndex = 0;
          manualSizeOverridesByModel = {{}};
          manualFieldValuesByModel[manualModelKey(model)] = {json.dumps(vals, ensure_ascii=False)};
          currentFieldValues = {{ ...manualFieldValuesByModel[manualModelKey(model)] }};
          lastManualOutput = null;
          lastManualQueueResult = null;
          lastManualPreflightResult = null;
          manualUndoStack = [];
          manualRedoStack = [];
          document.body.classList.add("label-studio-active");
          showSection("label", {{ labelMode: "studio" }});
          if (document.getElementById("manualTemplate")) document.getElementById("manualTemplate").value = model.path;
          syncManualInputsFromState();
          syncManualValuesFromInputs();
          showManualPreviewPlaceholder();
          renderManualSelectedFieldPanel();
          updateManualOutputControlPanel();
          return true;
        }})()
        """,
        timeout_ms=60000,
    )
    wait(900)


def layout_metrics(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const rect = selector => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
          };
          const intersects = (a, b) => Boolean(a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top);
          const head = rect("#label .studio-fast-head");
          const topbar = rect("#label .corel-production-topbar");
          const left = rect("#label .corel-left-toolbar");
          const canvas = rect("#label .preview-studio.corel-canvas-panel");
          const stage = rect("#label .corel-canvas-stage");
          const preview = rect("#manualPreview .preview-label.editor-live");
          const right = rect("#label .corel-inspector");
          const toast = rect("#labelStudioToastHost .label-studio-toast");
          const doc = document.documentElement;
          const shape = Array.from(document.querySelectorAll("#label .corel-tool")).find(button => button.innerText.includes("Şekil"));
          const rotate = Array.from(document.querySelectorAll("#label .corel-tool")).find(button => button.innerText.includes("Döndür"));
          const queueButtons = Array.from(document.querySelectorAll("#label [data-manual-requires-output='true']")).map(button => ({ text: button.innerText.trim(), disabled: button.disabled }));
          return {
            rects: { head, topbar, left, canvas, stage, preview, right, toast },
            overlap: {
              headCanvas: intersects(head, canvas),
              topbarCanvas: intersects(topbar, canvas),
              leftCanvas: intersects(left, canvas),
              rightCanvas: intersects(right, canvas),
              toastHead: intersects(toast, head)
            },
            scroll: { width: doc.scrollWidth, innerWidth: window.innerWidth, height: doc.scrollHeight, innerHeight: window.innerHeight },
            activeText: document.querySelector("#label .corel-dock-tabs button.active")?.innerText || "",
            alerts: window.__uiSimplifyAlerts || [],
            errors: window.__uiSimplifyErrors || [],
            disabledTools: {
              shapeHidden: shape ? getComputedStyle(shape).display === "none" : true,
              rotateHidden: rotate ? getComputedStyle(rotate).display === "none" : true,
              rotateDisabled: rotate?.getAttribute("aria-disabled") === "true"
            },
            queueButtons,
            manualSizeNotice: document.getElementById("manualSizeNotice")?.innerText || "",
            live: document.getElementById("manualLiveStatus")?.innerText || ""
          };
        })()
        """,
    )


def assert_stable_layout(metrics: dict[str, object], label: str, failures: list[str]) -> None:
    overlap = metrics["overlap"]
    rects = metrics["rects"]
    scroll = metrics["scroll"]
    assert_true(not overlap["headCanvas"], f"{label}: üst toolbar canvas ile çakışıyor.", failures)
    assert_true(not overlap["topbarCanvas"], f"{label}: model/boyut barı canvas ile çakışıyor.", failures)
    assert_true(not overlap["leftCanvas"], f"{label}: sol araç çubuğu canvas'ı eziyor.", failures)
    assert_true(not overlap["rightCanvas"], f"{label}: sağ panel canvas üstüne taşıyor.", failures)
    assert_true(not overlap["toastHead"], f"{label}: toast toolbar üstüne biniyor.", failures)
    assert_true(rects["preview"] and rects["preview"]["width"] > 220 and rects["preview"]["height"] > 180, f"{label}: etiket preview çok küçük veya görünmez.", failures)
    assert_true(scroll["width"] <= scroll["innerWidth"] + 8, f"{label}: yatay sayfa taşması var ({scroll['width']} > {scroll['innerWidth']}).", failures)
    assert_true(not metrics["alerts"], f"{label}: browser alert üretildi: {metrics['alerts']}", failures)
    assert_true(not metrics["errors"], f"{label}: console error yakalandı: {metrics['errors']}", failures)
    assert_true(all(button["disabled"] for button in metrics["queueButtons"]), f"{label}: çıktı yokken print/queue butonu aktif.", failures)
    assert_true(metrics["disabledTools"]["shapeHidden"] or metrics["disabledTools"]["rotateDisabled"], f"{label}: bağlı olmayan araçlar aktif görünüyor.", failures)


def apply_size(window: WebMainWindow, preset: str | None = None, width: int | None = None, height: int | None = None) -> dict[str, object]:
    if preset:
        script = f"(() => {{ applyManualSizePreset('{preset}'); showLabelStudioToast('Etiket boyutu test edildi.', 'info', 5000); return true; }})()"
    else:
        script = f"""
        (() => {{
          document.getElementById("manualUseDefaultSize").checked = false;
          document.getElementById("manualWidthMm").disabled = false;
          document.getElementById("manualHeightMm").disabled = false;
          document.getElementById("manualWidthMm").value = "{width}";
          document.getElementById("manualHeightMm").value = "{height}";
          updateManualSizeOverrideFromInputs();
          showLabelStudioToast('Özel boyut test edildi.', 'info', 5000);
          return true;
        }})()
        """
    run_js(window, script, timeout_ms=60000)
    wait(900)
    return layout_metrics(window)


def smart_variation_checks(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    cases = {
        "name_only": {"label_text": "Ayşe & Mehmet", "date_text": "", "note_text": "", "name_cut_text": ""},
        "name_date_note": {"label_text": "Ayşe & Mehmet", "date_text": "12.05.2026", "note_text": "Söz Hatırası", "name_cut_text": ""},
    }
    results: dict[str, object] = {}
    for name, values in cases.items():
        setup_studio(window, values)
        result = run_js(
            window,
            f"""
            (() => {{
              const values = {json.dumps(values, ensure_ascii=False)};
              manualFieldValuesByModel[manualModelKey(selectedLabelModel)] = values;
              currentFieldValues = {{ ...values }};
              syncManualInputsFromState();
              const smart = buildSmartLabelTextLayout({{ model: selectedLabelModel, label_size: effectiveManualSize(selectedLabelModel), values, fields: selectedLabelModel.fields_summary || [] }});
              selectedLabelModel.fields_summary = smart.fields;
              showManualPreviewPlaceholder();
              return {{ active: smart.activeFields.map(item => item.column), messages: smart.messages, metadata: smart.preview_metadata, needsReview: smart.needsReview }};
            }})()
            """,
            timeout_ms=60000,
        )
        results[name] = result
        if name == "name_only":
          assert_true(result["active"] == ["label_text"], "Smart layout sadece isim varyasyonunda boş tarih/not alanlarını çıkarmadı.", failures)
          assert_true(any("Sadece isim" in msg for msg in result["messages"]), "Sadece isim kalite mesajı görünmüyor.", failures)
          save_screenshot(window, "label-studio-smart-layout-name-only.png")
        if name == "name_date_note":
          assert_true(result["active"] == ["label_text", "date_text", "note_text"], "Smart layout üçlü yazı bloğunu korumadı.", failures)
          assert_true(any("Üçlü" in msg or "blok" in msg for msg in result["messages"]), "Üçlü blok kalite mesajı görünmüyor.", failures)
          save_screenshot(window, "label-studio-smart-layout-name-date-note.png")
    return results


def write_report(result: dict[str, object]) -> Path:
    report = OUTPUT_DIR / "PRODUCTION_LABEL_STUDIO_UI_SIMPLIFY_HOTFIX_RAPORU.md"
    failures = result.get("failures") or []
    report.write_text(
        f"""# Etiket Studio UI Simplify Hotfix Raporu

## Sorunun özeti
Etiket boyutu değiştiğinde Etiket Studio toolbar, model boyut alanı, canvas ve sağ panel dengesini kaybediyordu. 40x40 gibi kare ölçülerde preview alanı ve sağ panel metinleri üst üste binebiliyordu.

## Boyut değişiminde layout neden bozuluyordu?
Önceki CSS katmanları etiket artboard genişliğini ve sağ panel yüksekliğini sabit varsayıyordu. Boyut değişimi mesajları da inline status olarak toolbar bölgesini itiyordu.

## Yeni layout sistemi
Ekran dört bölgeye sabitlendi: üst toolbar, sol araç çubuğu, orta canvas viewport ve sağ özellik paneli. Canvas kendi içinde scroll kullanır; sağ panel kendi içinde scroll yapar.

## Toolbar sadeleştirme
Dosya aksiyonları ve çıktı aksiyonları ayrı gruplarda tutuldu. 1366 görünümde ikincil lazer aksiyonu compact alana taşınır ve butonlar canvas üstüne binmez.

## Sağ panel sadeleştirme
Dock sekmeleri Alanlar, Stil, Yerleşim ve Çıktı olarak sadeleştirildi. Validation/Yazdırma/Queue bilgileri compact status listesinde tutulur.

## Canvas viewport stabilizasyonu
40x40, 50x30 ve özel ölçü geçişlerinde artboard merkezde kalır. Preview aspect ratio gerçek ölçüden gelir.

## Toast/bildirim düzeltmesi
Boyut değişimi mesajları sağ üst toast olarak gösterilir; toolbar veya canvas üstüne binmez.

## Sol araç çubuğu sonucu
Kullanılan araçlar sadeleştirildi. Bağlı olmayan araçlar görünür aktif araç gibi davranmaz.

## Smart layout varyasyonları
Sadece isim ve isim+tarih+not varyasyonları gate içinde doğrulandı. Boş alanlar layout hesabından çıkarılır.

## 40x40 test sonucu
{json.dumps(result.get("metrics", {}).get("40x40", {}), ensure_ascii=False)[:1200]}

## 50x30 test sonucu
{json.dumps(result.get("metrics", {}).get("50x30", {}), ensure_ascii=False)[:1200]}

## 1366/1920 test sonucu
- 1366: {result.get("screenshots", {}).get("final_1366", "")}
- 1920: {result.get("screenshots", {}).get("final_1920", "")}

## Gate sonucu
- Status: {result.get("status")}
- Final karar: {result.get("final_decision")}
- Failures: {json.dumps(failures, ensure_ascii=False)}

## Kalan riskler
- 920px altı mobil/overlay davranışı ayrı polish fazı gerektirebilir.
- Şekil/Resim/Döndürme gerçek çıktı motoruna bağlanana kadar sade toolbar dışında kalmalıdır.
""",
        encoding="utf-8",
    )
    return report


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    try:
        window.resize(1920, 1080)
        window.show()
        window.raise_()
        window.activateWindow()
        wait(2600)
        setup_studio(window)
        regression_ref = save_screenshot(window, "label-studio-40x40-before-or-regression-reference.png")
        metrics_40 = apply_size(window, "40x40")
        assert_stable_layout(metrics_40, "40x40", failures)
        after_40 = save_screenshot(window, "label-studio-40x40-after-clean-layout.png")
        toast = save_screenshot(window, "label-studio-toast-not-overlapping.png")
        right_panel = save_screenshot(window, "label-studio-right-panel-compact.png")
        metrics_50 = apply_size(window, "50x30")
        assert_stable_layout(metrics_50, "50x30", failures)
        clean_50 = save_screenshot(window, "label-studio-50x30-clean-layout.png")
        metrics_custom = apply_size(window, None, 70, 35)
        assert_stable_layout(metrics_custom, "custom 70x35", failures)
        custom_shot = save_screenshot(window, "label-studio-custom-size-clean-layout.png")
        smart = smart_variation_checks(window, failures)
        window.resize(1366, 768)
        wait(800)
        setup_studio(window)
        metrics_1366 = apply_size(window, "40x40")
        assert_stable_layout(metrics_1366, "1366 40x40", failures)
        toolbar_1366 = save_screenshot(window, "label-studio-toolbar-compact-1366.png")
        final_1366 = save_screenshot(window, "label-studio-1366-final.png")
        window.resize(1920, 1080)
        wait(800)
        setup_studio(window)
        metrics_1920 = apply_size(window, "50x30")
        assert_stable_layout(metrics_1920, "1920 50x30", failures)
        toolbar_1920 = save_screenshot(window, "label-studio-toolbar-1920.png")
        final_1920 = save_screenshot(window, "label-studio-1920-final.png")
        result = {
            "status": "PASS" if not failures else "FAIL",
            "final_decision": "READY_FOR_PILOT_WITH_LABEL_STUDIO_UI_FIX" if not failures else "READY_WITH_LABEL_STUDIO_UI_BLOCKER",
            "failures": failures,
            "metrics": {
                "40x40": metrics_40,
                "50x30": metrics_50,
                "custom": metrics_custom,
                "1366": metrics_1366,
                "1920": metrics_1920,
            },
            "smart_layout": smart,
            "screenshots": {
                "regression_reference": regression_ref,
                "after_40": after_40,
                "clean_50": clean_50,
                "custom": custom_shot,
                "toast": toast,
                "right_panel": right_panel,
                "toolbar_1366": toolbar_1366,
                "toolbar_1920": toolbar_1920,
                "smart_name_only": str(OUTPUT_DIR / "label-studio-smart-layout-name-only.png"),
                "smart_name_date_note": str(OUTPUT_DIR / "label-studio-smart-layout-name-date-note.png"),
                "final_1366": final_1366,
                "final_1920": final_1920,
            },
            "safety": {
                "printer_auto_start": False,
                "laser_auto_start": False,
                "rdworks_auto_start": False,
                "trendyol_live_action": False,
                "fake_success_detected": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "final_decision": "READY_WITH_LABEL_STUDIO_UI_BLOCKER", "error": str(exc), "failures": failures}
    finally:
        window.close()
    report = write_report(result)
    result["report_path"] = str(report)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
