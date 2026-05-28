from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_name_cut_scale_zoom_hotfix"
RESULT_PATH = OUTPUT_DIR / "production_name_cut_scale_zoom_hotfix_gate_result.json"
REPORT_PATH = OUTPUT_DIR / "PRODUCTION_NAME_CUT_SCALE_ZOOM_HOTFIX_RAPORU.md"

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
    wait(600)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def seed_scale_case(window: WebMainWindow) -> dict[str, object]:
    text = "Sedef Sefer Hasan Huseyin Leyla Ayse Veli"
    return run_js(
        window,
        f"""
        (() => {{
          window.__nameCutScaleErrors = [];
          window.addEventListener("error", event => window.__nameCutScaleErrors.push(String(event.message || event.error || "")));
          showSection("nameCutStudio");
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
            allow_rotation: true,
            offset_mm: 0.3,
            font_family: "Ceyizhome Lab Script (Mochary)",
            mirror_cut: false,
            mirror_vertical: false,
            preview_zoom: 100
          }};
          const base = {{
            id: "scale-source-1",
            item_id: "scale-source-1",
            source: "manual_label",
            source_label: "Manuel isim",
            name_text: {json.dumps(text, ensure_ascii=False)},
            text: {json.dumps(text, ensure_ascii=False)},
            quantity: "7",
            width_mm: 250,
            height_mm: 40,
            offset_mm: 0.3,
            style: "Ceyizhome Lab Script (Mochary)",
            composition: "Otomatik Bol ve Diz",
            composition_mode: "Otomatik Bol ve Diz",
            compositionMode: "auto_split_and_nest",
            composition_user_selected: false,
            warnings: [],
            errors: [],
            status: "READY"
          }};
          const layoutResult = computeNameCutLayout(base, {{ context: "save", forceRecompute: true }});
          nameCutItems = [applyNameCutLayoutResultToItem(base, layoutResult)];
          selectedNameCutItemId = "";
          nameCutCanvasSelectionVisible = false;
          const layout = currentNameCutLayout();
          refreshNameCutStudioViews(layout);
          renderLaserLayoutPreview(layout);
          const layoutAfterPath = currentNameCutLayout();
          const rendered = Array.from(document.querySelectorAll("#nameCutStudio .rdworks-name-outline-svg")).map(el => {{
            const b = el.getBBox ? el.getBBox() : {{ width: 0, height: 0 }};
            const r = el.getBoundingClientRect();
            return {{ tag: el.tagName, text: el.textContent.trim(), bboxWidth: b.width, bboxHeight: b.height, pxWidth: r.width, pxHeight: r.height }};
          }});
          const board = document.querySelector("#nameCutStudio .laser-layout-stage[data-namecut-board='true']");
          const beforeZoom = Number(nameCutLayoutConfig.preview_zoom || 100);
          board.dispatchEvent(new WheelEvent("wheel", {{ deltaY: -120, bubbles: true, cancelable: true }}));
          const afterZoomIn = Number(nameCutLayoutConfig.preview_zoom || 100);
          board.dispatchEvent(new WheelEvent("wheel", {{ deltaY: 120, bubbles: true, cancelable: true }}));
          const afterZoomOut = Number(nameCutLayoutConfig.preview_zoom || 100);
          return {{
            layoutResult,
            layout: layoutAfterPath,
            metrics: nameCutSourceMetrics(layoutAfterPath),
            rendered,
            beforeZoom,
            afterZoomIn,
            afterZoomOut,
            metaText: document.querySelector("#nameCutStudio .laser-layout-meta")?.innerText || "",
            errors: window.__nameCutScaleErrors || []
          }};
        }})()
        """,
        timeout_ms=60000,
    )


def backend_rdworks_scale_check(failures: list[str]) -> dict[str, object]:
    text = "Sedef Sefer Hasan Huseyin Leyla Ayse Veli"
    parent = {
        "id": "backend-scale-1",
        "item_id": "backend-scale-1",
        "name_text": text,
        "text": text,
        "quantity": "7",
        "style": "Ceyizhome Lab Script (Mochary)",
        "composition": "Otomatik Bol ve Diz",
        "composition_mode": "Otomatik Bol ve Diz",
        "compositionMode": "auto_split_and_nest",
        "preview_objects": [
            {
                "id": f"backend-scale-1-split-{idx + 1}",
                "text": name,
                "formattedText": name,
                "widthMm": 48,
                "heightMm": 40,
                "actualPathWidthMm": 48,
                "actualPathHeightMm": 35,
            }
            for idx, name in enumerate(text.split())
        ],
        "offset_mm": 0.3,
        "status": "READY",
        "warnings": [],
        "errors": [],
    }
    layout = layout_name_cut_items([parent], LayoutConfig(dense_nesting=True, item_gap_mm=1, target_gap_mm=1, allow_rotation=True))
    assert_true(len(layout["items"]) == 7, "Backend 7 ayri isim placement uretmeli.", failures)
    assert_true(
        all(30 <= float(item["width_mm"]) <= 90 and float(item["height_mm"]) >= 38 for item in layout["items"]),
        "Backend split isimleri RDWorks path bbox + okunur yukseklikle yerlestirmeli.",
        failures,
    )
    assert_true(
        float(layout["summary"]["used_area_percent"]) >= 2.0,
        f"Backend kullanim orani RDWorks dense footprint'e gore anlamli olmali: {layout['summary']['used_area_percent']}",
        failures,
    )
    return layout


def write_report(result: dict[str, object]) -> None:
    failures = result.get("failures", [])
    shots = result.get("screenshots", [])
    report = f"""# PRODUCTION NAME CUT SCALE ZOOM HOTFIX RAPORU

## Sorun
Coklu isimler ayrilsa bile uretim gorunumu web preview gibi eziliyor, isimler operator tarafindan zor goruluyor ve zoom tasarim programi hissi vermiyordu.

## Duzeltme
- Frontend ve backend split isimleri RDWorks path bbox + 1 mm gap mantigiyla yerlestirir.
- Actual path olcusu hem yerlestim hem kalite bilgisi olarak kullanilir; 80x40 hedef standardi referans olarak kalir.
- Canvas wheel zoom dogrudan calisir; zoom sadece render olcegini degistirir.
- Selection/helper katmani production/export katmanindan ayri kalir.

## Gate Sonucu
- Durum: **{result.get("status")}**
- Hata sayisi: {len(failures)}
{chr(10).join(f"- {failure}" for failure in failures) if failures else "- Kritik hata yok."}

## Screenshot Yollari
{chr(10).join(f"- `{path}`" for path in shots)}

## Guvenlik
Lazer, RDWorks ve yazici otomatik baslatilmadi.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    screenshots: list[str] = []
    backend = backend_rdworks_scale_check(failures)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    window.resize(1366, 768)
    window.show()
    wait(1600)
    try:
        scale_case = seed_scale_case(window)
        screenshots.append(save_screenshot(window, "name-cut-scale-rdworks-7-names-1366.png"))
        assert_true(scale_case["layoutResult"]["multiNameCandidate"] is True, "7 isimlik liste coklu isim adayi olmali.", failures)
        assert_true(len(scale_case["layout"]["items"]) == 7, "Ana layout 7 ayri placement uretmeli.", failures)
        assert_true(
            all(30 <= float(item["width_mm"]) <= 90 and float(item["height_mm"]) >= 38 for item in scale_case["layout"]["items"]),
            "Frontend split isimleri RDWorks path bbox + okunur yukseklikle yerlestirmeli.",
            failures,
        )
        assert_true(
            float(scale_case["layout"]["summary"]["used_area_percent"]) >= 2.0,
            f"Frontend kullanim orani RDWorks dense footprint'e gore anlamli olmali: {scale_case['layout']['summary']['used_area_percent']}",
            failures,
        )
        assert_true(len(scale_case["rendered"]) == 7, "Canvas 7 ayri uretim path/text render etmeli.", failures)
        assert_true(
            all(float(item["bboxHeight"]) >= 18 for item in scale_case["rendered"]),
            f"Isimler operatorun goremeyecegi kadar kucuk kalmamali: {scale_case['rendered']}",
            failures,
        )
        assert_true(scale_case["afterZoomIn"] > scale_case["beforeZoom"], "Mouse wheel zoom in preview_zoom degerini artirmali.", failures)
        assert_true(scale_case["afterZoomOut"] <= scale_case["afterZoomIn"], "Mouse wheel zoom out preview_zoom degerini dusurmeli.", failures)
        assert_true(not scale_case.get("errors"), f"Console error olmamali: {scale_case.get('errors')}", failures)
    finally:
        window.close()
        app.processEvents()

    status = "FAILED" if failures else "PASSED"
    result = {
        "status": status,
        "failures": failures,
        "backend_summary": backend["summary"],
        "screenshots": screenshots,
        "security": {
            "printer_auto_start": False,
            "laser_auto_start": False,
            "rdworks_auto_start": False,
        },
        "report_path": str(REPORT_PATH),
        "result_path": str(RESULT_PATH),
    }
    write_report(result)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
