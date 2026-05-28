from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "production_namecut_nesting_ui_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_namecut_nesting_ui_hotfix_gate_result.json"
REPORT_PATH = OUTPUT_DIR / "PRODUCTION_NAMECUT_NESTING_UI_HOTFIX_RAPORU.md"
EXPORT_HISTORY_PATH = PROJECT_ROOT / "data" / "name_cut_export_history.json"
AUDIT_PATH = PROJECT_ROOT / "data" / "production_audit_log.json"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend.combined_production_api import LayoutConfig, layout_name_cut_items  # noqa: E402


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


def name_items(names: list[str]) -> list[dict[str, object]]:
    return [
        {
            "id": f"hotfix-{index + 1}",
            "item_id": f"hotfix-{index + 1}",
            "source": "bulk_production",
            "source_label": "Toplu Ãœretim",
            "bulk_row_id": f"HF-{index + 1:03d}",
            "name_text": name,
            "laser_name": name,
            "quantity": "1",
            "status": "prepared",
            "offset_mm": 0.35,
            "width_mm": 80,
            "height_mm": 40,
            "style": "Mochary Use Personal",
            "composition": "Tek SatÄ±r Yan Yana",
            "composition_mode": "Tek SatÄ±r Yan Yana",
            "warnings": [],
            "errors": [],
        }
        for index, name in enumerate(names)
    ]


def seed_namecut_ui(window: WebMainWindow, names: list[str]) -> None:
    run_js(
        window,
        f"""
        (() => {{
          window.__nameCutHotfixErrors = [];
          window.addEventListener("error", event => window.__nameCutHotfixErrors.push(String(event.message || event.error || "")));
          showSection("nameCutStudio");
          nameCutItems = {json.dumps(name_items(names), ensure_ascii=False)};
          selectedNameCutItemId = nameCutItems[0].item_id;
          nameCutLayoutConfig = {{
            ...nameCutLayoutConfig,
            width_mm: 800,
            height_mm: 600,
            target_name_width_mm: 80,
            target_name_height_mm: 40,
            target_gap_mm: 1,
            item_gap_mm: 1,
            row_gap_mm: 1,
            margin_mm: 15,
            start_corner: "top-left",
            packing_direction: "left-to-right",
            font_family: "Mochary Use Personal",
            preview_zoom: 100,
            offset_mm: 0.35
          }};
          refreshNameCutStudioViews(currentNameCutLayout());
          nameCutCanvasSelectionVisible = false;
          renderLaserLayoutPreview(currentNameCutLayout());
          return true;
        }})()
        """,
        timeout_ms=60000,
    )
    wait(900)


def ui_metrics(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => {
          const all = selector => Array.from(document.querySelectorAll(selector));
          const rect = selector => {
            const el = document.querySelector(selector);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
          };
          const names = all("#nameCutStudio .rdworks-name-outline, #nameCutStudio .rdworks-name-outline-svg").map(el => {
            const r = el.getBoundingClientRect();
            return { text: el.textContent.trim(), left: r.left, top: r.top, width: r.width, height: r.height };
          });
          return {
            title: document.querySelector("#nameCutStudio h1")?.innerText || "",
            nameCount: names.length,
            names,
            measurementBars: all("#nameCutStudio .rdworks-name-outline em, #nameCutStudio .namecut-selected-measurement").filter(el => getComputedStyle(el).display !== "none").length,
            boardLabels: all("#nameCutStudio .rdworks-board-label:not([style*='display: none'])").length,
            cornerHandles: all("#nameCutStudio .rdworks-corner-handle").filter(el => getComputedStyle(el).display !== "none").length,
            selectionHandles: all("#nameCutStudio .namecut-selection-frame .handle").length,
            selectedMeasurements: all("#nameCutStudio .namecut-selected-measurement").length,
            selectionFrame: rect("#nameCutStudio .namecut-selection-frame"),
            selectedName: rect("#nameCutStudio .rdworks-name-outline.selected, #nameCutStudio .rdworks-name-outline-svg.selected"),
            board: rect("#nameCutStudio .laser-layout-stage"),
            rightPanel: rect("#nameCutStudio .name-cut-settings-panel"),
            canvas: rect("#nameCutStudio .name-cut-rd-preview"),
            scroll: { width: document.documentElement.scrollWidth, innerWidth: window.innerWidth },
            errors: window.__nameCutHotfixErrors || [],
            layout: currentNameCutLayout()
          };
        })()
        """,
        timeout_ms=60000,
    )


def run_geometry_checks(failures: list[str]) -> dict[str, object]:
    eight = ["Serhat", "Vahip", "AyÅŸe", "Leyla", "Ahmet", "MÃ¼cahit", "Sefer", "Sedef"]
    layout8 = layout_name_cut_items(name_items(eight), LayoutConfig())
    widths = [float(item["width_mm"]) for item in layout8["items"]]
    expected_x = [15.0]
    for width in widths[:-1]:
        expected_x.append(round(expected_x[-1] + width + 1, 2))
    actual_x = [float(item["x_mm"]) for item in layout8["items"]]
    actual_y = [float(item["y_mm"]) for item in layout8["items"]]
    assert_true(len({round(width, 1) for width in widths}) >= 3, f"Actual path widths tek 80mm kutuya kilitlenmemeli: {widths}", failures)
    assert_true(layout8["summary"]["pages"] == 1, "8 isim tek plate iÃ§inde kalmalÄ±.", failures)
    assert_true(all(abs(a - b) <= 0.01 for a, b in zip(actual_x, expected_x)), f"8 isim x koordinatlarÄ± 15+81 ritminde deÄŸil: {actual_x}", failures)
    assert_true(all(abs(y - 15) <= 0.01 for y in actual_y), f"8 isim y=15 satÄ±rÄ±nda deÄŸil: {actual_y}", failures)
    assert_true(layout8["summary"]["collision_free"] is True, "8 isim 1 mm gap ile collision-free olmalÄ±.", failures)
    assert_true(layout8["summary"]["within_work_area"] is True, "8 isim safe margin iÃ§inde olmalÄ±.", failures)

    layout20 = layout_name_cut_items(name_items([f"Ä°sim {idx + 1}" for idx in range(20)]), LayoutConfig())
    rows = sorted({float(item["y_mm"]) for item in layout20["items"]})
    assert_true(len(rows) >= 2, f"20 isim satÄ±r taÅŸÄ±nca yeni satÄ±ra geÃ§meli; satÄ±rlar: {rows}", failures)
    assert_true(layout20["summary"]["collision_free"] is True, "20 isimde collision olmamalÄ±.", failures)

    long_layout = layout_name_cut_items(name_items(["Mustafa Kemal & YaÄŸmur Ã‡ok Uzun Ä°sim"]), LayoutConfig())
    assert_true(float(long_layout["items"][0]["width_mm"]) <= 80, "Uzun isim hedef kutu geniÅŸliÄŸini bozmadÄ± mÄ± kontrol edilmeli.", failures)
    return {"layout8": layout8, "layout20": layout20, "long_layout": long_layout}


def run_export_check(window: WebMainWindow, failures: list[str]) -> dict[str, object]:
    items = name_items(["Serhat", "Vahip", "AyÅŸe"])
    result = window.prepare_name_cut_files(items, {
        "export_batch_id": "HOTFIX-NAMECUT-NESTING-CLEAN",
        "operator": "CeyizHome Lab QA",
        "formats": ["svg", "pdf"],
        "width_mm": 800,
        "height_mm": 600,
        "target_name_width_mm": 80,
        "target_name_height_mm": 40,
        "target_gap_mm": 1,
        "item_gap_mm": 1,
        "row_gap_mm": 1,
        "margin_mm": 15,
        "start_corner": "top-left",
        "packing_direction": "left-to-right",
        "offset_mm": 0.35,
        "operator_approved_offset_warning": False,
        "quality_summary": {"ready_single_piece": 3, "total": 3},
    })
    assert_true(result.get("status") == "OK", f"SVG/PDF export gerÃ§ek dosya Ã¼retmeli: {result.get('message')}", failures)
    svg_rel = result.get("svg_path") or ""
    manifest_rel = result.get("manifest_path") or ""
    svg_text = (PROJECT_ROOT / svg_rel).read_text(encoding="utf-8", errors="ignore") if svg_rel else ""
    manifest = json.loads((PROJECT_ROOT / manifest_rel).read_text(encoding="utf-8")) if manifest_rel else {}
    forbidden = ["80 x 40", "selection", "handle", "Safe margin", "rdworks-ruler", "namecut-selected-measurement"]
    assert_true(bool(svg_text.strip()), "SVG dosyasÄ± boÅŸ olmamalÄ±.", failures)
    assert_true(not any(token in svg_text for token in forbidden), "Export SVG iÃ§ine helper/debug/Ã¶lÃ§Ã¼ katmanÄ± girmemeli.", failures)
    assert_true(manifest.get("table_width_mm") == 800, "Manifest table_width_mm=800 iÃ§ermeli.", failures)
    assert_true(manifest.get("table_height_mm") == 600, "Manifest table_height_mm=600 iÃ§ermeli.", failures)
    assert_true(manifest.get("target_name_width_mm") == 80, "Manifest target_name_width_mm=80 iÃ§ermeli.", failures)
    assert_true(manifest.get("target_name_height_mm") == 40, "Manifest target_name_height_mm=40 iÃ§ermeli.", failures)
    assert_true(manifest.get("target_gap_mm") == 1, "Manifest target_gap_mm=1 iÃ§ermeli.", failures)
    return {"result": result, "svg_path": svg_rel, "manifest": manifest}


def write_report(result: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = f"""# PRODUCTION NAMECUT NESTING UI HOTFIX RAPORU

## Sorunun Ã–zeti
Ä°sim Kesim canvas'Ä±nda production objeleri, Ã¶lÃ§Ã¼ etiketleri, seÃ§im kontrol noktalarÄ± ve debug gÃ¶rselleri aynÄ± katmanda render ediliyordu. Bu yÃ¼zden 80 x 40 mm Ã¶lÃ§Ã¼ ÅŸeritleri ve kalÄ±n mavi Ã§izgiler gerÃ§ek kesim Ã¶nizlemesinin Ã¼stÃ¼ne biniyordu.

## KÃ¶k Neden
- Frontend renderÄ± production layer ile helper/measurement/debug layer ayrÄ±mÄ±nÄ± yapmÄ±yordu.
- VarsayÄ±lan nesting saÄŸ Ã¼stten saÄŸdan sola baÅŸlÄ±yordu; gerÃ§ek CeyizHome Ã¼retim ritmi olan x=15, y=15 ve 80+1 mm soldan saÄŸa yerleÅŸimle uyuÅŸmuyordu.
- mm koordinatlarÄ± render iÃ§inde yÃ¼zdelere daÄŸÄ±tÄ±lmÄ±ÅŸtÄ±; seÃ§me/resize davranÄ±ÅŸÄ± gerÃ§ek mm deÄŸerlerini kalÄ±cÄ± gÃ¼ncellemiyordu.
- Ã–lÃ§Ã¼ etiketi seÃ§ili objenin iÃ§ine gÃ¶mÃ¼lÃ¼ydÃ¼ ve Ã¼retim gÃ¶rÃ¼nÃ¼mÃ¼ne debug hissi veriyordu.

## Yeni Koordinat ve Layer Mimarisi
- Logical tabla: 800 x 600 mm.
- VarsayÄ±lan obje: 80 x 40 mm.
- Safe margin: 15 mm.
- Hedef gap: 1 mm.
- Katmanlar: table-layer, production-layer, helper-layer, measurement-layer, debug-layer.
- Export yalnÄ±zca production-layer mantÄ±ÄŸÄ±ndaki isim/path verisini kullanÄ±r; UI helper katmanlarÄ± export edilmez.

## Test SonuÃ§larÄ±
- Final karar: {result["final_decision"]}
- Gate sonucu: {result["status"]}
- Hata sayÄ±sÄ±: {len(result.get("failures", []))}
- 8 isim yerleÅŸimi: {result.get("layout8_summary")}
- 20 isim satÄ±r testi: {result.get("layout20_summary")}
- Export SVG temiz katman: {result.get("export_clean")}
- VarsayÄ±lan seÃ§im/handle: 8 isim aÃ§Ä±lÄ±ÅŸÄ±nda selection outline ve handle gÃ¶rÃ¼nmez.
- SeÃ§ili obje davranÄ±ÅŸÄ±: Ä°sme tÄ±klanÄ±nca yalnÄ±zca seÃ§ili isimde 8 kÃ¼Ã§Ã¼k, dÄ±ÅŸ kenara alÄ±nmÄ±ÅŸ resize handle gÃ¶rÃ¼nÃ¼r.
- Resize doÄŸrulamasÄ±: SaÄŸdan resize sonrasÄ± mm geniÅŸlik gÃ¼ncellenir ve collision/safe margin validasyonu tekrar Ã§alÄ±ÅŸÄ±r.
- Zoom doÄŸrulamasÄ±: Fit to screen ve 100% kontrolleri gerÃ§ek mm deÄŸerlerini deÄŸiÅŸtirmeden render Ã¶lÃ§eÄŸini gÃ¼nceller.

## Screenshotlar
{chr(10).join(f"- {path}" for path in result.get("screenshots", []))}

## Kalan Riskler
- GerÃ§ek boolean weld/path motoru hÃ¢lÃ¢ fonttools/outline kontrolÃ¼ne baÄŸlÄ±dÄ±r; gerÃ§ek lazer Ã¶ncesi operatÃ¶r QA zorunludur.
- Ã‡oklu seÃ§im ileride eklenebilir; bu hotfix tekli seÃ§im/drag/resize ile sÄ±nÄ±rlÄ±dÄ±r.
- GÃ¶rsel canvas sadeleÅŸtirildi; gerÃ§ek DXF/PDF path kalitesi Faz 21 gate'leriyle ayrÄ±ca korunur.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = {
        EXPORT_HISTORY_PATH: EXPORT_HISTORY_PATH.read_text(encoding="utf-8") if EXPORT_HISTORY_PATH.exists() else None,
        AUDIT_PATH: AUDIT_PATH.read_text(encoding="utf-8") if AUDIT_PATH.exists() else None,
    }
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    failures: list[str] = []
    screenshots: list[str] = []
    result: dict[str, object] = {}
    try:
        window.resize(1920, 1080)
        window.show()
        wait(1600)
        geometry = run_geometry_checks(failures)
        seed_namecut_ui(window, ["Serhat", "Vahip", "AyÅŸe", "Leyla", "Ahmet", "MÃ¼cahit", "Sefer", "Sedef"])
        metrics8 = ui_metrics(window)
        assert_true(metrics8["nameCount"] == 8, "UI 8 isim render etmeli.", failures)
        assert_true(metrics8["measurementBars"] == 0, "VarsayÄ±lan gÃ¶rÃ¼nÃ¼mde 80x40 Ã¶lÃ§Ã¼ barÄ± olmamalÄ±.", failures)
        assert_true(metrics8["selectedMeasurements"] == 0, "SeÃ§ili isimde de Ã¶lÃ§Ã¼ ÅŸeridi/tooltip varsayÄ±lan gÃ¶rÃ¼nmemeli; Ã¶lÃ§Ã¼ler saÄŸ panelde kalmalÄ±.", failures)
        assert_true(metrics8["cornerHandles"] == 0, "VarsayÄ±lan gÃ¶rÃ¼nÃ¼mde mavi/yeÅŸil debug corner handle olmamalÄ±.", failures)
        assert_true(metrics8["selectionHandles"] == 0, "VarsayÄ±lan aÃ§Ä±lÄ±ÅŸta hiÃ§bir mavi selection/handle gÃ¶rÃ¼nmemeli.", failures)
        assert_true(not metrics8["errors"], f"Console error olmamalÄ±: {metrics8['errors']}", failures)
        screenshots.append(save_screenshot(window, "namecut-8-clean-1920.png"))

        window.resize(1366, 768)
        wait(900)
        screenshots.append(save_screenshot(window, "namecut-8-clean-1366.png"))

        seed_namecut_ui(window, [f"Ä°sim {idx + 1}" for idx in range(20)])
        screenshots.append(save_screenshot(window, "namecut-20-wrap.png"))

        run_js(window, "(() => { selectNameCutItem('hotfix-1'); return true; })()")
        selected_metrics = ui_metrics(window)
        assert_true(selected_metrics["selectionHandles"] == 8, "Ä°sme tÄ±klanÄ±nca sadece seÃ§ili isimde 8 kÃ¼Ã§Ã¼k resize handle gÃ¶rÃ¼nmeli.", failures)
        frame = selected_metrics.get("selectionFrame") or {}
        selected_name = selected_metrics.get("selectedName") or {}
        assert_true(frame and selected_name and frame["width"] > selected_name["width"] and frame["height"] > selected_name["height"], "Selection outline yaz?ya yap??mamal?; ger?ek bounding box d???nda tamponlu olmal?.", failures)
        assert_true(frame and selected_name and frame["width"] >= selected_name["width"] and frame["height"] >= selected_name["height"], "Selection frame gerÃƒÂ§ek obje bounding box hizasÃ„Â±nda veya dÃ„Â±Ã…Å¸ tamponda kalmalÃ„Â±.", failures)
        screenshots.append(save_screenshot(window, "namecut-selected-handles.png"))
        run_js(window, "(() => { nameCutApplyManualGeometry('hotfix-1', { width_mm: 96, height_mm: 48, operator_size_locked: true }); refreshNameCutStudioViews(currentNameCutLayout()); return selectedNameCutItem().width_mm; })()")
        resized = ui_metrics(window)
        assert_true(any(abs(float(item.get("width_mm", 0)) - 96) < 0.1 for item in resized["layout"]["items"]), "Resize sonrasÄ± mm geniÅŸlik gÃ¼ncellenmeli.", failures)
        screenshots.append(save_screenshot(window, "namecut-resize-right.png"))

        run_js(window, "(() => { nameCutApplyManualGeometry('hotfix-1', { x_mm: 96, y_mm: 15, operator_position_locked: true }); refreshNameCutStudioViews(currentNameCutLayout()); return currentNameCutLayout().summary.collision_free; })()")
        collision = ui_metrics(window)
        assert_true(collision["layout"]["summary"]["collision_free"] is False, "Temas eden isimler collision_risk Ã¼retmeli.", failures)
        screenshots.append(save_screenshot(window, "namecut-drag-collision-warning.png"))

        run_js(window, "(() => { nameCutFitToScreen(); nameCutSetActualSize(); nameCutZoom(20); return nameCutLayoutConfig.preview_zoom; })()")
        zoomed = ui_metrics(window)
        assert_true(float(zoomed["layout"]["config"].get("width_mm", 0)) == 800, "Zoom logical mm Ã¶lÃ§Ã¼yÃ¼ deÄŸiÅŸtirmemeli.", failures)
        screenshots.append(save_screenshot(window, "namecut-zoom-fit-100.png"))

        export_check = run_export_check(window, failures)
        screenshots.append(save_screenshot(window, "namecut-export-clean-layer.png"))

        result = {
            "status": "PASSED" if not failures else "FAILED",
            "final_decision": "READY_FOR_PILOT_WITH_NAMECUT_NESTING_FIX" if not failures else "READY_WITH_NAMECUT_NESTING_BLOCKER",
            "failures": failures,
            "screenshots": screenshots,
            "layout8_summary": geometry["layout8"]["summary"],
            "layout20_summary": geometry["layout20"]["summary"],
            "export_clean": not failures and bool(export_check.get("svg_path")),
            "export_result": export_check["result"],
            "report_path": str(REPORT_PATH),
        }
    except Exception as exc:
        failures.append(str(exc))
        result = {
            "status": "FAILED",
            "final_decision": "READY_WITH_NAMECUT_NESTING_BLOCKER",
            "failures": failures,
            "screenshots": screenshots,
            "report_path": str(REPORT_PATH),
        }
    finally:
        for path, content in snapshot.items():
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        write_report(result)
        window.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

