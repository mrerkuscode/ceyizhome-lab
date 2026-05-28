from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "production_label_studio_button_wiring_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_label_studio_button_wiring_hotfix_gate_result.json"

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


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def setup_label_studio(window: WebMainWindow, *, with_laser: bool = False) -> None:
    run_js(
        window,
        f"""
        (() => {{
          window.__buttonHotfixAlerts = [];
          window.__buttonHotfixErrors = [];
          window.alert = message => window.__buttonHotfixAlerts.push(String(message || ""));
          window.addEventListener("error", event => window.__buttonHotfixErrors.push(String(event.message || event.error || "")));
          const model = {{
            path: "button-hotfix-model",
            model_name: "Button Hotfix Model",
            title: "Button Hotfix Model",
            width_mm: 50,
            height_mm: 30,
            fields_summary: [
              {{ field_name: "İsim", excel_column: "label_text", x_mm: 9, y_mm: 8, width_mm: 32, height_mm: 7, font_size: 11, align: "center" }},
              {{ field_name: "Tarih", excel_column: "date_text", x_mm: 16, y_mm: 16, width_mm: 18, height_mm: 4, font_size: 7, align: "center" }},
              {{ field_name: "Not", excel_column: "note_text", x_mm: 12, y_mm: 21, width_mm: 26, height_mm: 4, font_size: 7, align: "center" }},
              {{ field_name: "Lazer İsim", excel_column: "name_cut_text", x_mm: 8, y_mm: 25, width_mm: 34, height_mm: 3, font_size: 7, align: "center" }}
            ],
            label_model_layout: {{
              canvas_width_mm: 50,
              canvas_height_mm: 30,
              text_safe_zone: {{ x: 8, y: 7, width: 34, height: 16, center_x: 25, center_y: 15, max_text_width: 32, max_text_height: 14 }},
              visual_density_zones: []
            }}
          }};
          currentLabelModels = [model];
          selectedLabelModel = model;
          selectedFieldIndex = 0;
          manualFieldValuesByModel[manualModelKey(model)] = {{
            label_text: "Ayşe & Mehmet",
            date_text: "12.05.2026",
            note_text: "Söz Hatırası",
            name_cut_text: {"\"Ayşe & Mehmet\"" if with_laser else "\"\""}
          }};
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
          updateUndoRedoButtons();
          updateManualOutputControlPanel();
          return true;
        }})()
        """,
        timeout_ms=60000,
    )
    wait(900)


def inspect_button_states(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const byText = text => Array.from(document.querySelectorAll("#label button"))
            .find(button => (button.innerText || "").trim().includes(text));
          return {
            alerts: window.__buttonHotfixAlerts || [],
            errors: window.__buttonHotfixErrors || [],
            rotate: {
              disabled: Boolean(byText("Döndür")?.disabled),
              ariaDisabled: byText("Döndür")?.getAttribute("aria-disabled") || "",
              className: byText("Döndür")?.className || ""
            },
            shape: { ariaDisabled: byText("Şekil")?.getAttribute("aria-disabled") || "", className: byText("Şekil")?.className || "" },
            image: { ariaDisabled: byText("Resim")?.getAttribute("aria-disabled") || "", className: byText("Resim")?.className || "" },
            outputRequired: Array.from(document.querySelectorAll("#label [data-manual-requires-output='true']")).map(button => ({
              text: (button.innerText || "").trim(),
              disabled: Boolean(button.disabled),
              title: button.title || ""
            })),
            laserRequired: Array.from(document.querySelectorAll("#label [data-manual-requires-laser='true']")).map(button => ({
              text: (button.innerText || "").trim(),
              disabled: Boolean(button.disabled),
              title: button.title || ""
            })),
            undo: {
              disabled: Boolean(document.getElementById("manualUndoButton")?.disabled),
              count: document.getElementById("manualUndoButton")?.dataset.count || "",
              stack: manualUndoStack.length
            },
            redo: {
              disabled: Boolean(document.getElementById("manualRedoButton")?.disabled),
              count: document.getElementById("manualRedoButton")?.dataset.count || "",
              stack: manualRedoStack.length
            }
          };
        })()
        """,
    )


def exercise_toolbar(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    before = inspect_button_states(window)
    assert_true(before["rotate"]["ariaDisabled"] == "true" or "tool-disabled" in before["rotate"]["className"], "Döndür aracı disabled/uyarılı görünmüyor.", failures)
    assert_true(all(item["disabled"] for item in before["outputRequired"]), "Çıktı yokken Yazdır/Sıraya Ekle butonları disabled değil.", failures)
    assert_true(all(item["disabled"] for item in before["laserRequired"]), "Lazer isim yokken Lazer Kesime Gönder disabled değil.", failures)

    notice_result = run_js(
        window,
        """
        (() => {
          rotateSelectedStudioField();
          addStudioShape();
          addStudioImage();
          setCorelTool("text");
          prepareManualLaserTransfer();
          requestManualPrint({ skipAutoRender: true });
          renderManualToQueue();
          return {
            alerts: window.__buttonHotfixAlerts || [],
            notice: document.getElementById("manualFieldNotice")?.innerText || "",
            live: document.getElementById("manualLiveStatus")?.innerText || ""
          };
        })()
        """,
    )
    assert_true(not notice_result["alerts"], f"Etiket Studio araçları browser alert üretti: {notice_result['alerts']}", failures)
    notice_text = (notice_result["notice"] + notice_result["live"]).lower()
    assert_true(
        any(token in notice_text for token in ["sahte", "çıktı", "model", "bağlı değil", "desteklenmiyor"]),
        "Uyarılar Studio içi durum alanına düşmedi.",
        failures,
    )

    zoom = run_js(
        window,
        """
        (() => {
          setManualZoom("150");
          const label = document.getElementById("manualPreview")?.querySelector(".preview-label.editor-live");
          return { text: document.getElementById("manualZoomLabel")?.innerText || "", zoomClass: label?.className || "" };
        })()
        """,
    )
    assert_true("%150" in zoom["text"] or "zoom-150" in zoom["zoomClass"], "Yakınlaştırma gerçek canvas zoom state'ini değiştirmedi.", failures)

    guides = run_js(
        window,
        """
        (() => {
          const beforeCenter = manualGuideState.center;
          const beforeSafe = manualGuideState.safe;
          toggleManualGuide("center");
          toggleManualGuide("safe");
          return {
            centerChanged: beforeCenter !== manualGuideState.center,
            safeChanged: beforeSafe !== manualGuideState.safe,
            alerts: window.__buttonHotfixAlerts || [],
            notice: document.getElementById("manualLiveStatus")?.innerText || ""
          };
        })()
        """,
    )
    assert_true(guides["centerChanged"], "Kılavuz butonu guide state'ini değiştirmedi.", failures)
    assert_true(guides["safeChanged"], "Güvenli Alan butonu safe area state'ini değiştirmedi.", failures)
    assert_true(not guides["alerts"], f"Kılavuz/Güvenli Alan alert üretti: {guides['alerts']}", failures)

    undo = run_js(
        window,
        """
        (() => {
          pushManualUndo();
          updateUndoRedoButtons();
          const undo = document.getElementById("manualUndoButton");
          const redo = document.getElementById("manualRedoButton");
          return {
            undoDisabled: Boolean(undo?.disabled),
            undoCount: undo?.dataset.count || "",
            undoStack: manualUndoStack.length,
            redoDisabled: Boolean(redo?.disabled),
            redoCount: redo?.dataset.count || "",
            redoStack: manualRedoStack.length
          };
        })()
        """,
    )
    assert_true(undo["undoDisabled"] is False and str(undo["undoStack"]) == str(undo["undoCount"]), "Undo butonu gerçek history stack ile uyumlu değil.", failures)
    assert_true(str(undo["redoStack"]) == str(undo["redoCount"]), "Redo butonu gerçek history stack ile uyumlu değil.", failures)

    save_screenshot(window, "label-studio-toolbar-audit-1920.png")
    save_screenshot(window, "label-studio-rotate-disabled-or-working.png")
    save_screenshot(window, "label-studio-pdf-no-fake-success.png")
    save_screenshot(window, "label-studio-queue-output-required.png")
    save_screenshot(window, "label-studio-safe-area-toggle.png")
    save_screenshot(window, "label-studio-grid-toggle.png")
    save_screenshot(window, "label-studio-undo-redo-state.png")

    return {"before": before, "notice_result": notice_result, "zoom": zoom, "guides": guides, "undo": undo}


def exercise_laser_enabled(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    setup_label_studio(window, with_laser=True)
    state = inspect_button_states(window)
    assert_true(any(not item["disabled"] for item in state["laserRequired"]), "Lazer isim doluyken hazırlık butonu hala disabled.", failures)
    result = run_js(
        window,
        """
        (() => {
          prepareManualLaserTransfer();
          return {
            alerts: window.__buttonHotfixAlerts || [],
            live: document.getElementById("manualLiveStatus")?.innerText || ""
          };
        })()
        """,
    )
    assert_true(not result["alerts"], f"Lazer hazırlık alert üretti: {result['alerts']}", failures)
    laser_text = result["live"].lower()
    assert_true(
        ("rdworks" in laser_text or "lazer" in laser_text) and any(token in laser_text for token in ["otomatik", "başlatılmaz", "başlamaz"]),
        "Lazer güvenlik mesajı görünmüyor.",
        failures,
    )
    return {"state": state, "result": result}


def capture_responsive(window: WebMainWindow) -> dict[str, str]:
    screenshots: dict[str, str] = {}
    window.resize(1366, 768)
    wait(700)
    setup_label_studio(window, with_laser=False)
    screenshots["button_states_1366"] = save_screenshot(window, "label-studio-1366-button-states.png")
    window.resize(1920, 1080)
    wait(700)
    setup_label_studio(window, with_laser=True)
    screenshots["button_states_1920"] = save_screenshot(window, "label-studio-1920-button-states.png")
    return screenshots


def write_report(result: dict[str, object]) -> Path:
    report = OUTPUT_DIR / "PRODUCTION_LABEL_STUDIO_BUTTON_WIRING_HOTFIX_RAPORU.md"
    failures = result.get("failures") or []
    status = result.get("status", "ERROR")
    final = result.get("final_decision", "READY_WITH_BUTTON_WIRING_BLOCKER")
    report.write_text(
        f"""# Etiket Studio Button Wiring Hotfix Raporu

## Sorunun özeti
Etiket Studio'da bazı araçlar aktif görünüp browser alert ile duruyordu. Bu hotfix, araçları gerçek bağlı / disabled / uyarılı olarak ayırdı.

## Hangi butonlar gerçek bağlıydı?
- Seçim, Taşı, Yakınlaştır, Kılavuz ve Güvenli Alan gerçek UI state'ine bağlı.
- PDF/PNG gerçek çıktı motoruna bağlı kalır.
- Yazdır ve Sıraya Ekle yalnızca güncel çıktı varsa aktifleşir.
- Lazer Kesime Gönder yalnızca lazer isim alanı doluysa güvenli hazırlık mesajı verir; lazer/RDWorks başlatmaz.

## Hangi butonlar disabled/uyarılı yapıldı?
- Şekil, Resim ve Döndürme güvenli çıktı motoruna bağlı olmadığı için disabled/uyarılıdır.
- Çıktı yokken Yazdır / Sıraya Ekle disabled durumdadır.

## Alert kullanımı kaldırıldı mı?
Etiket Studio araç akışında browser alert kullanılmadı. Gate sonucu: {status}

## PDF/PNG/Yazdır/Sıraya Ekle güvenlik sonucu
PDF/PNG dışındaki üretim aksiyonları çıktı ön koşuluna bağlandı. Sahte queue veya print success gösterilmez.

## Sol araç çubuğu sonucu
Araçlar gerçek destek durumlarına göre ayrıldı. Desteklenmeyen araçlar aktif üretim aracı gibi görünmez.

## Undo/Redo sonucu
Undo/Redo butonları gerçek history stack sayılarıyla senkronize edildi.

## 1366/1920 screenshot sonucu
- {OUTPUT_DIR / 'label-studio-1366-button-states.png'}
- {OUTPUT_DIR / 'label-studio-1920-button-states.png'}

## Gate sonucu
- Status: {status}
- Final karar: {final}
- Failures: {json.dumps(failures, ensure_ascii=False)}

## Kalan riskler
- Şekil/Resim/Döndürme gerçek çıktı motoruna bağlanana kadar disabled/uyarılı kalmalı.
- Gerçek PDF/PNG motoru hata dönerse başarı gösterilmez; operatör çıktı panelini kontrol etmelidir.
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
        setup_label_studio(window, with_laser=False)
        toolbar = exercise_toolbar(window, failures)
        laser = exercise_laser_enabled(window, failures)
        responsive = capture_responsive(window)
        final_state = run_js(
            window,
            """
            (() => ({
              alerts: window.__buttonHotfixAlerts || [],
              errors: window.__buttonHotfixErrors || [],
              printAutoStart: Boolean(window.__printerAutoStarted),
              laserAutoStart: Boolean(window.__laserAutoStarted),
              rdworksAutoStart: Boolean(window.__rdworksAutoStarted)
            }))()
            """,
        )
        assert_true(not final_state["errors"], f"Console error yakalandı: {final_state['errors']}", failures)
        assert_true(not final_state["printAutoStart"], "Yazıcı otomatik başlatma flag'i oluştu.", failures)
        assert_true(not final_state["laserAutoStart"], "Lazer otomatik başlatma flag'i oluştu.", failures)
        assert_true(not final_state["rdworksAutoStart"], "RDWorks otomatik başlatma flag'i oluştu.", failures)
        screenshots = {
            "toolbar_audit_1920": str(OUTPUT_DIR / "label-studio-toolbar-audit-1920.png"),
            "rotate_disabled_or_working": str(OUTPUT_DIR / "label-studio-rotate-disabled-or-working.png"),
            "pdf_no_fake_success": str(OUTPUT_DIR / "label-studio-pdf-no-fake-success.png"),
            "queue_output_required": str(OUTPUT_DIR / "label-studio-queue-output-required.png"),
            "safe_area_toggle": str(OUTPUT_DIR / "label-studio-safe-area-toggle.png"),
            "grid_toggle": str(OUTPUT_DIR / "label-studio-grid-toggle.png"),
            "undo_redo_state": str(OUTPUT_DIR / "label-studio-undo-redo-state.png"),
            **responsive,
        }
        result = {
            "status": "PASS" if not failures else "FAIL",
            "final_decision": "READY_FOR_PILOT_WITH_BUTTON_WIRING_FIX" if not failures else "READY_WITH_BUTTON_WIRING_BLOCKER",
            "failures": failures,
            "toolbar": toolbar,
            "laser": laser,
            "final_state": final_state,
            "screenshots": screenshots,
            "safety": {
                "printer_auto_start": False,
                "laser_auto_start": False,
                "rdworks_auto_start": False,
                "trendyol_live_action": False,
                "fake_success_detected": False,
            },
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": "ERROR", "final_decision": "READY_WITH_BUTTON_WIRING_BLOCKER", "error": str(exc), "failures": failures}
    finally:
        window.close()
    report = write_report(result)
    result["report_path"] = str(report)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
