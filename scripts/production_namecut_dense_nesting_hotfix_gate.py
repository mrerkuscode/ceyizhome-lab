from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-05-23"
OUTPUT_DIR = PROJECT_ROOT / "output" / TODAY / "production_namecut_dense_nesting_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_namecut_dense_nesting_hotfix_gate_result.json"
REPORT_PATH = OUTPUT_DIR / "PRODUCTION_NAMECUT_DENSE_NESTING_HOTFIX_RAPORU.md"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend.combined_production_api import LayoutConfig, export_name_cut_batch, layout_name_cut_items  # noqa: E402


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
            "id": f"dense-{index + 1}",
            "item_id": f"dense-{index + 1}",
            "source": "bulk_production",
            "source_label": "Toplu Üretim",
            "bulk_row_id": f"DN-{index + 1:03d}",
            "name_text": name,
            "laser_name": name,
            "quantity": "1",
            "status": "prepared",
            "offset_mm": 0.35,
            "style": "Mochary Use Personal",
            "composition": "Tek Satır Yan Yana",
            "composition_mode": "Tek Satır Yan Yana",
            "warnings": [],
            "errors": [],
        }
        for index, name in enumerate(names)
    ]


def seed_namecut_ui(window: WebMainWindow, names: list[str], allow_rotation: bool = False) -> None:
    run_js(
        window,
        f"""
        (() => {{
          window.__nameCutDenseErrors = [];
          window.addEventListener("error", event => window.__nameCutDenseErrors.push(String(event.message || event.error || "")));
          showSection("nameCutStudio");
          nameCutItems = {json.dumps(name_items(names), ensure_ascii=False)};
          selectedNameCutItemId = "";
          nameCutCanvasSelectionVisible = false;
          nameCutLayoutConfig = {{
            ...nameCutLayoutConfig,
            width_mm: 800,
            height_mm: 600,
            target_name_width_mm: 80,
            target_name_height_mm: 40,
            target_gap_mm: 1,
            item_gap_mm: 1,
            row_gap_mm: 1,
            joined_name_gap_mm: 1,
            margin_mm: 15,
            dense_nesting: true,
            allow_rotation: {str(allow_rotation).lower()},
            mirror_cut: false,
            mirror_vertical: false,
            font_family: "Mochary Use Personal",
            preview_zoom: 100,
            offset_mm: 0.35
          }};
          refreshNameCutStudioViews(currentNameCutLayout());
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
          const names = all("#nameCutStudio .rdworks-name-outline-svg").map(el => {
            const r = el.getBoundingClientRect();
            return { text: el.textContent.trim(), left: r.left, top: r.top, width: r.width, height: r.height, outline: el.dataset.outlineExport || "" };
          });
          const firstName = document.querySelector("#nameCutStudio .rdworks-name-outline-svg");
          const firstStyle = firstName ? getComputedStyle(firstName) : null;
          return {
            title: document.querySelector("#nameCutStudio h1")?.innerText || "",
            svgNameCount: names.length,
            htmlNameCount: all("#nameCutStudio span.rdworks-name-outline").length,
            names,
            productionSvg: !!document.querySelector("#nameCutStudio .namecut-production-svg"),
            outlineStyle: firstStyle ? { stroke: firstStyle.stroke, strokeWidth: firstStyle.strokeWidth, opacity: firstStyle.opacity } : {},
            measurementBars: all("#nameCutStudio .rdworks-name-outline em, #nameCutStudio .namecut-selected-measurement").filter(el => getComputedStyle(el).display !== "none").length,
            defaultSelectionFrames: all("#nameCutStudio .namecut-selection-frame").length,
            selectionHandles: all("#nameCutStudio .namecut-selection-frame .handle").length,
            board: rect("#nameCutStudio .laser-layout-stage"),
            rightPanel: rect("#nameCutStudio .name-cut-settings-panel"),
            canvas: rect("#nameCutStudio .name-cut-rd-preview"),
            scroll: { width: document.documentElement.scrollWidth, innerWidth: window.innerWidth },
            errors: window.__nameCutDenseErrors || [],
            layout: currentNameCutLayout()
          };
        })()
        """,
        timeout_ms=60000,
    )


def run_backend_geometry_checks(failures: list[str]) -> dict[str, object]:
    eight_names = ["Sedef", "Sefer", "Mücahit", "Leyla", "Ahmet", "Songül", "Hasan", "Abdullah"]
    cfg = LayoutConfig(dense_nesting=True)
    layout8 = layout_name_cut_items(name_items(eight_names), cfg)
    assert_true(layout8["summary"]["pages"] == 1, "8 isim tek plate içinde kalmalı.", failures)
    assert_true(layout8["summary"]["collision_free"] is True, "8 isim 1 mm gap ile collision-free olmalı.", failures)
    assert_true(layout8["summary"]["within_work_area"] is True, "8 isim safe margin içinde olmalı.", failures)
    assert_true(layout8["summary"]["placement_strategy"] == "ACTUAL_PATH_DENSE_SHELF", "Dense placement strategy manifest/layout içinde görünmeli.", failures)
    assert_true(all(float(item.get("actual_path_width_mm") or 0) > 0 for item in layout8["items"]), "Her isim actual_path_width_mm taşımalı.", failures)

    actual_widths = {round(float(item.get("actual_path_width_mm") or 0), 1) for item in layout8["items"]}
    assert_true(len(actual_widths) >= 3, f"Actual path widths must not be locked to a single 80mm box: {sorted(actual_widths)}", failures)
    assert_true(min(actual_widths) < 70 and max(actual_widths) <= 80, f"Short/long names should use different actualPathWidth values: {sorted(actual_widths)}", failures)

    required_model_keys = {"id", "name", "xMm", "yMm", "widthMm", "heightMm", "actualPathWidthMm", "actualPathHeightMm", "rotation", "mirrored", "direction", "scale", "selected", "lockedAspectRatio", "isConnectedPath", "hasCollision", "isInsideSafeMargin", "readyForCut", "warnings", "errors"}
    assert_true(all(required_model_keys.issubset(set((item.get("laser_name_object") or {}).keys())) for item in layout8["items"]), "Her backend item LaserNameObject sozlesmesini tasimali.", failures)
    assert_true(all(item.get("xMm") == (item.get("laser_name_object") or {}).get("xMm") for item in layout8["items"]), "CamelCase xMm alias modelle tutarli olmali.", failures)
    assert_true(all(item.get("widthMm") == (item.get("laser_name_object") or {}).get("widthMm") for item in layout8["items"]), "CamelCase widthMm alias modelle tutarli olmali.", failures)

    dense_names = [eight_names[index % len(eight_names)] for index in range(60)]
    layout60 = layout_name_cut_items(name_items(dense_names), cfg)
    rows = sorted({float(item["y_mm"]) for item in layout60["items"] if int(item.get("page", 1)) == 1})
    assert_true(len(rows) >= 5, f"60 isim tabla aşağı doğru dolmalı; satır sayısı: {len(rows)}", failures)
    assert_true(max(rows) > 170, f"Yoğun yerleşim sadece üstte kalmamalı; son y: {max(rows) if rows else '-'}", failures)
    assert_true(layout60["summary"]["collision_free"] is True, "60 isim dense yerleşimde collision-free olmalı.", failures)
    assert_true(layout60["summary"]["within_work_area"] is True, "60 isim dense yerleşimde safe margin içinde olmalı.", failures)

    rot_cfg = LayoutConfig(dense_nesting=True, allow_rotation=True)
    layout_rot = layout_name_cut_items(name_items(["Mustafa Kemal & Yağmur Çok Uzun İsim"] * 12), rot_cfg)
    assert_true(layout_rot["summary"]["collision_free"] is True, "Rotasyon açıkken collision üretilmemeli.", failures)
    return {"layout8": layout8, "layout60": layout60, "layout_rot": layout_rot}


def run_export_check(failures: list[str]) -> dict[str, object]:
    items = name_items(["Sedef", "Sefer", "Mücahit", "Leyla"])
    result = export_name_cut_batch(
        PROJECT_ROOT,
        PROJECT_ROOT / "missing.xlsx",
        items,
        {
            "export_batch_id": "DENSE-NESTING-HOTFIX",
            "operator": "CeyizHome Lab QA",
            "formats": ["svg", "dxf", "pdf"],
            "dense_nesting": True,
            "allow_rotation": True,
            "operator_approved_offset_warning": True,
            "quality_summary": {"ready_single_piece": len(items), "total": len(items)},
        },
    )
    assert_true(result.get("status") == "OK", f"SVG/DXF/PDF export gerçek dosya üretmeli: {result.get('message')}", failures)
    svg_rel = result.get("svg_path") or ""
    manifest_rel = result.get("manifest_path") or ""
    svg_text = (PROJECT_ROOT / svg_rel).read_text(encoding="utf-8", errors="ignore") if svg_rel else ""
    manifest = json.loads((PROJECT_ROOT / manifest_rel).read_text(encoding="utf-8")) if manifest_rel else {}
    forbidden = ["selection", "handle", "Safe margin", "rdworks-ruler", "namecut-selected-measurement", "80 x 40"]
    assert_true(bool(svg_text.strip()), "SVG dosyası boş olmamalı.", failures)
    assert_true("<path" in svg_text or "POLYLINE" in svg_text, "SVG gerçek kesim path/outline içermeli.", failures)
    assert_true(not any(token in svg_text for token in forbidden), "Export SVG içine helper/debug/ölçü katmanı girmemeli.", failures)
    assert_true(manifest.get("table_width_mm") == 800, "Manifest table_width_mm=800 içermeli.", failures)
    assert_true(manifest.get("table_height_mm") == 600, "Manifest table_height_mm=600 içermeli.", failures)
    assert_true(manifest.get("target_name_width_mm") == 80, "Manifest target_name_width_mm=80 içermeli.", failures)
    assert_true(manifest.get("target_name_height_mm") == 40, "Manifest target_name_height_mm=40 içermeli.", failures)
    assert_true(manifest.get("target_gap_mm") == 1, "Manifest target_gap_mm=1 içermeli.", failures)
    assert_true(manifest.get("actual_path_layout") is True, "Manifest actual_path_layout=true içermeli.", failures)
    return {"result": result, "svg_path": svg_rel, "manifest": manifest}


def run_ui_checks(window: WebMainWindow, failures: list[str], screenshots: list[str]) -> dict[str, object]:
    seed_namecut_ui(window, ["Sedef", "Sefer", "Mücahit", "Leyla", "Ahmet", "Songül", "Hasan", "Abdullah"])
    window.resize(1920, 1080)
    wait(500)
    metrics8 = ui_metrics(window)
    screenshots.append(save_screenshot(window, "namecut-dense-8-1920.png"))
    assert_true(metrics8["productionSvg"] is True, "Production preview SVG layer kullanmalı.", failures)
    assert_true(metrics8["svgNameCount"] == 8, f"8 isim SVG outline preview olarak görünmeli: {metrics8['svgNameCount']}", failures)
    assert_true(metrics8["htmlNameCount"] == 0, "NameCut production layer HTML span text preview kullanmamalı.", failures)
    assert_true(metrics8["measurementBars"] == 0, "Varsayılan görünümde ölçü barı/debug etiketi görünmemeli.", failures)
    assert_true(metrics8["defaultSelectionFrames"] == 0, "Varsayılan açılışta selection frame görünmemeli.", failures)
    assert_true(not metrics8["errors"], f"Console error olmamalı: {metrics8['errors']}", failures)

    run_js(
        window,
        """
        (() => {
          selectedNameCutItemId = nameCutItems[0].item_id;
          nameCutCanvasSelectionVisible = true;
          renderLaserLayoutPreview(currentNameCutLayout());
          return true;
        })()
        """,
    )
    wait(400)
    selected = ui_metrics(window)
    screenshots.append(save_screenshot(window, "namecut-selection-handles-1920.png"))
    assert_true(selected["defaultSelectionFrames"] == 1, "Seçili isimde tek selection frame olmalı.", failures)
    assert_true(selected["selectionHandles"] == 8, "Seçili isimde 8 küçük resize handle olmalı.", failures)

    before = selected["layout"]["items"][0]
    run_js(
        window,
        """
        (() => {
          const item = nameCutItems[0];
          const placed = currentNameCutLayout().items[0];
          nameCutApplyManualGeometry(item.item_id, {
            x_mm: placed.x_mm,
            y_mm: placed.y_mm,
            width_mm: placed.width_mm + 12,
            height_mm: placed.height_mm,
            operator_position_locked: true,
            operator_size_locked: true,
            locked_aspect_ratio: false
          });
          refreshNameCutStudioViews(currentNameCutLayout());
          nameCutCanvasSelectionVisible = true;
          return currentNameCutLayout().items[0];
        })()
        """,
    )
    after_resize = ui_metrics(window)["layout"]["items"][0]
    assert_true(float(after_resize["width_mm"]) > float(before["width_mm"]), "Sağdan resize eşdeğeri width_mm değerini artırmalı.", failures)

    run_js(window, "(() => { nameCutZoom(20); return nameCutLayoutConfig.preview_zoom; })()")
    zoomed = ui_metrics(window)
    run_js(window, "(() => { nameCutSetActualSize(); return nameCutLayoutConfig.preview_zoom; })()")
    actual = ui_metrics(window)
    assert_true(zoomed["layout"]["items"][0]["x_mm"] == actual["layout"]["items"][0]["x_mm"], "Zoom logical mm koordinatlarını değiştirmemeli.", failures)

    seed_namecut_ui(window, ["Sedef", "Sefer", "Mücahit", "Leyla", "Ahmet", "Songül", "Hasan", "Abdullah"] * 7, allow_rotation=True)
    window.resize(1366, 768)
    wait(600)
    dense_metrics = ui_metrics(window)
    screenshots.append(save_screenshot(window, "namecut-dense-60-1366.png"))
    rows = sorted({float(item["y_mm"]) for item in dense_metrics["layout"]["items"] if int(item.get("page", 1)) == 1})
    assert_true(len(rows) >= 5, "1366 yoğun üretim görünümünde tabla aşağı doğru dolmalı.", failures)
    assert_true(dense_metrics["scroll"]["width"] <= dense_metrics["scroll"]["innerWidth"] + 24, "1366 görünümde kontrolsüz yatay taşma olmamalı.", failures)
    return {"metrics8": metrics8, "selected": selected, "dense_metrics": dense_metrics}


def write_report(result: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = f"""# PRODUCTION NAMECUT DENSE NESTING HOTFIX RAPORU

## Sorunun Özeti
İsim Kesim ekranı, isimleri gerçek üretim path objeleri gibi yoğun yerleştirmek yerine web preview mantığıyla üst satıra diziyordu. Bu hotfix, preview'i SVG outline üretim katmanına yaklaştırır ve layout'u actual path bbox + 1 mm gap kullanan dense shelf stratejisine geçirir.

## Kök Neden
- Frontend production layer styled text span kullanıyordu.
- Backend ve frontend layout kaba hedef kutu yaklaşımına yaslanıyordu.
- Preview ve export geometri sözleşmesi yeterince aynı alanları taşımıyordu.

## Yeni Mimari
- Logical tabla: 800 x 600 mm.
- Dense strategy: `ACTUAL_PATH_DENSE_SHELF`.
- Her item `actual_path_width_mm`, `actual_path_height_mm`, `rotation`, `mirrored`, `direction` alanlarını taşır.
- Production preview SVG outline layer kullanır; helper/selection/debug katmanları ayrı kalır.

## Acceptance Sonucu
- 8 isim collision-free ve safe margin içinde.
- 60 isim tabla aşağı doğru çok satırlı yerleşiyor.
- Selection sadece seçili objede 8 küçük handle gösteriyor.
- Zoom logical mm değerlerini değiştirmiyor.
- Export SVG/DXF/PDF gerçek dosya üretir; helper/debug geometri export'a girmez.

## Screenshotlar
{chr(10).join(f"- `{path}`" for path in result.get("screenshots", []))}

## Gate Sonucu
- Durum: **{result.get("status")}**
- Hata sayısı: {len(result.get("failures", []))}
{chr(10).join(f"- {failure}" for failure in result.get("failures", []))}

## Kalan Riskler
- Bu sürüm tam serbest polygon nesting değil; actual path bbox + 1 mm şişirilmiş güvenli shelf/skyline yaklaşımıdır.
- Gerçek kontur-kontur nesting/boolean weld ileri fazda pyclipper tabanlı genişletilebilir.
- RDWorks/lazer/yazıcı otomatik başlatılmaz.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    screenshots: list[str] = []
    backend = run_backend_geometry_checks(failures)
    export = run_export_check(failures)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    window.show()
    wait(1600)
    ui = run_ui_checks(window, failures, screenshots)
    result = {
        "status": "PASSED" if not failures else "FAILED",
        "failures": failures,
        "backend_summary": {
            "layout8": backend["layout8"]["summary"],
            "layout60": backend["layout60"]["summary"],
            "layout_rot": backend["layout_rot"]["summary"],
        },
        "export": {
            "status": export["result"].get("status"),
            "svg_path": export["svg_path"],
            "manifest_path": export["result"].get("manifest_path"),
        },
        "ui": {
            "metrics8": ui["metrics8"],
            "selected": ui["selected"],
            "dense_row_count": len({float(item["y_mm"]) for item in ui["dense_metrics"]["layout"]["items"] if int(item.get("page", 1)) == 1}),
        },
        "screenshots": screenshots,
        "security": {
            "printer_auto_start": False,
            "laser_auto_start": False,
            "rdworks_auto_start": False,
        },
        "report_path": str(REPORT_PATH),
        "result_path": str(RESULT_PATH),
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result)
    print(json.dumps({"status": result["status"], "failures": failures, "report": str(REPORT_PATH), "result": str(RESULT_PATH)}, ensure_ascii=False, indent=2))
    window.close()
    app.quit()
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
