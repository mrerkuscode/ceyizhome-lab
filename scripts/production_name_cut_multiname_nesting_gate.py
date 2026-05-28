from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_name_cut_multiname_nesting_fix"
RESULT_PATH = OUTPUT_DIR / "production_name_cut_multiname_nesting_gate_result.json"
REPORT_PATH = OUTPUT_DIR / "PRODUCTION_NAME_CUT_MULTINAME_NESTING_FIX_RAPORU.md"

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


def seed_multiname(window: WebMainWindow, mode: str, text: str, quantity: str = "7") -> dict[str, object]:
    return run_js(
        window,
        f"""
        (() => {{
          window.__nameCutMultiErrors = [];
          window.addEventListener("error", event => window.__nameCutMultiErrors.push(String(event.message || event.error || "")));
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
            offset_mm: 0.3,
            font_family: "Mochary Use Personal",
            mirror_cut: false,
            mirror_vertical: false,
            preview_zoom: 100
          }};
          const base = {{
            id: "multiname-source-1",
            item_id: "multiname-source-1",
            source: "manual_label",
            source_label: "Manuel İsim",
            name_text: {json.dumps(text, ensure_ascii=False)},
            text: {json.dumps(text, ensure_ascii=False)},
            quantity: {json.dumps(quantity)},
            width_mm: 250,
            height_mm: 40,
            offset_mm: 0.3,
            composition: {json.dumps(mode, ensure_ascii=False)},
            composition_mode: {json.dumps(mode, ensure_ascii=False)},
            compositionMode: normalizeNameCutCompositionMode({json.dumps(mode, ensure_ascii=False)}),
            composition_user_selected: {str(mode != "Otomatik Böl ve Diz").lower()},
            warnings: [],
            errors: [],
            status: "READY"
          }};
          const layoutResult = computeNameCutLayout(base, {{ context: "save", userSelectedComposition: base.composition_user_selected === true, forceRecompute: true }});
          nameCutItems = [applyNameCutLayoutResultToItem(base, layoutResult)];
          selectedNameCutItemId = "";
          nameCutCanvasSelectionVisible = false;
          const layout = currentNameCutLayout();
          refreshNameCutStudioViews(layout);
          renderLaserLayoutPreview(layout);
          const metrics = nameCutSourceMetrics(layout);
          const rendered = Array.from(document.querySelectorAll("#nameCutStudio .rdworks-name-outline-svg")).map(el => {{
            const r = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return {{ text: el.textContent.trim(), width: r.width, height: r.height, stroke: style.stroke, cls: el.getAttribute("class") || "" }};
          }});
          return {{
            layoutResult,
            item: nameCutItems[0],
            layout,
            metrics,
            rendered,
            metaText: document.querySelector("#nameCutStudio .laser-layout-meta")?.innerText || "",
            errors: window.__nameCutMultiErrors || []
          }};
        }})()
        """,
        timeout_ms=60000,
    )


def backend_multiname_check(failures: list[str]) -> dict[str, object]:
    text = "Sedef Sefer Vahip Ayşe Mehmet Leyla Mücahit Serap"
    parent = {
        "id": "backend-multiname-1",
        "item_id": "backend-multiname-1",
        "name_text": text,
        "text": text,
        "quantity": "7",
        "composition": "Otomatik Böl ve Diz",
        "composition_mode": "Otomatik Böl ve Diz",
        "compositionMode": "auto_split_and_nest",
        "preview_objects": [
            {"id": f"backend-multiname-1-split-{idx + 1}", "text": name, "formattedText": name, "widthMm": 80, "heightMm": 40, "actualPathWidthMm": 60, "actualPathHeightMm": 32}
            for idx, name in enumerate(text.split())
        ],
        "offset_mm": 0.3,
        "status": "READY",
        "warnings": [],
        "errors": [],
    }
    layout = layout_name_cut_items([parent], LayoutConfig(dense_nesting=True, item_gap_mm=1, target_gap_mm=1))
    assert_true(len(layout["items"]) >= 8, "Backend auto_split preview_objects ayrı placement üretmeli.", failures)
    assert_true(len({item["item_id"] for item in layout["items"]}) >= 8, "Backend split item_id değerleri benzersiz kalmalı.", failures)
    assert_true(layout["summary"]["total_copies"] == 8, "Backend auto_split quantity parent ile karışmamalı; her isim 1 adet olmalı.", failures)
    return layout


def write_report(result: dict[str, object]) -> None:
    failures = result.get("failures", [])
    shots = result.get("screenshots", [])
    report = f"""# PRODUCTION NAME CUT MULTINAME NESTING FIX RAPORU

## Sorun Neydi?
Çoklu isim metni layout seviyesinde algılansa bile nesting ve render katmanına tek parent obje gibi sızabiliyordu. Bu durumda üst metriklerde `1 / 1 yerleşen isim` görünürken quantity toplamı ayrı sayılıyor ve canvas tek sıkışmış obje gibi görünüyordu.

## Kök Neden
- Split child item içinde parent `text/layout_result` alanları kalabiliyordu.
- Logical id hesabı `source_item_id` öncelikli olduğu için split objeler tek kaynak gibi sayılıyordu.
- `Yerleşen isim` metriği gerçek name object sayısı yerine parent queue item sayısına yakın hesaplanıyordu.

## Düzeltme
- `parseNameCutInput()` eklendi; auto split, single line ve preserve lines ayrımı netleşti.
- Split child item’lar kendi `text/name_text/layout_result` değerlerini taşıyor.
- Auto split child quantity değeri güvenli varsayılan olarak `1`.
- `nameCutLogicalItemId()` item id öncelikli hale geldi.
- `nameCutSourceMetrics()` parent item sayısı yerine gerçek split name object sayısını kullanıyor.
- Backend `_expand_joined_name_items()` auto split `preview_objects` listesini gerçek ayrı placement olarak kabul ediyor.

## Test Sonuçları
- Durum: **{result.get("status")}**
- Hata sayısı: {len(failures)}
{chr(10).join(f"- {failure}" for failure in failures) if failures else "- Kritik hata yok."}

## Screenshot Yolları
{chr(10).join(f"- `{path}`" for path in shots)}

## Kalan Riskler
- Bu düzeltme tam polygon nesting değildir; çoklu isim parse + placement ayrımını güvenceye alır.
- Harf weld/path doğrulaması export/preflight tarafında yeniden doğrulanır.
- Lazer, RDWorks ve yazıcı otomatik başlatılmaz.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    screenshots: list[str] = []
    backend = backend_multiname_check(failures)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    window.resize(1366, 768)
    window.show()
    wait(1600)
    try:
        text = "Sedef Sefer Vahip Ayşe Mehmet Leyla Mücahit Serap"
        auto = seed_multiname(window, "Otomatik Böl ve Diz", text, quantity="7")
        screenshots.append(save_screenshot(window, "name-cut-multiname-auto-split.png"))
        assert_true(auto["layoutResult"]["multiNameCandidate"] is True, "Çoklu isim adayı algılanmalı.", failures)
        assert_true(len(auto["layoutResult"]["previewObjects"]) >= 8, "Auto split previewObjects en az 8 olmalı.", failures)
        assert_true(len(auto["layout"]["items"]) >= 8, "Ana canvas en az 8 ayrı placement üretmeli.", failures)
        assert_true(len({item["item_id"] for item in auto["layout"]["items"]}) >= 8, "Placement item_id değerleri tek parent id'ye düşmemeli.", failures)
        assert_true(auto["metrics"]["source_total"] >= 8 and auto["metrics"]["source_placed"] >= 8, f"Yerleşen isim metriği 1/1 kalmamalı: {auto['metrics']}", failures)
        assert_true(auto["metrics"]["copies_total"] >= 8 and auto["metrics"]["copies_placed"] >= 8, f"Yerleşen adet quantity toplamından ayrı doğru hesaplanmalı: {auto['metrics']}", failures)
        assert_true(len(auto["rendered"]) >= 8, "Canvas en az 8 ayrı text/path render etmeli.", failures)
        assert_true(all(float(item["width_mm"]) >= 20 and float(item["height_mm"]) >= 10 for item in auto["layout"]["items"]), "Hiçbir placement 5 mm gibi sıkışmış olmamalı.", failures)
        assert_true(auto["layout"]["summary"]["collision_free"] is True, "Auto split isimler temas etmemeli.", failures)
        assert_true(not any("risk-dots" in item["cls"] or "collision-risk" in item["cls"] or "needs-weld" in item["cls"] for item in auto["rendered"]), "Hazır split isimler kırmızı hata/debug blob gibi görünmemeli.", failures)

        single = seed_multiname(window, "Tek Satır Yan Yana", text, quantity="7")
        screenshots.append(save_screenshot(window, "name-cut-multiname-single-line.png"))
        assert_true(single["layoutResult"]["compositionMode"] == "single_line_text", "Single line mode açıkça seçilince korunmalı.", failures)
        assert_true(len(single["layoutResult"]["previewObjects"]) == 1, "Single line mode previewObjects tek obje olmalı.", failures)
        assert_true(len(single["layout"]["items"]) == 7, "Single line mode quantity kadar fiziksel kopya üretmeli.", failures)

        couple = seed_multiname(window, "Otomatik Böl ve Diz", "Ayşe & Mehmet", quantity="1")
        screenshots.append(save_screenshot(window, "name-cut-couple-not-forced-split.png"))
        assert_true(couple["layoutResult"]["multiNameCandidate"] is False, "Ayşe & Mehmet liste adayı sayılmamalı.", failures)
        assert_true(len(couple["layoutResult"]["previewObjects"]) == 1, "Ayşe & Mehmet çiftli isim varsayılan tek obje kalmalı.", failures)
        assert_true(len(couple["layout"]["items"]) == 1, "Ayşe & Mehmet ana canvas'ta tek çiftli obje olmalı.", failures)

        assert_true(not auto.get("errors") and not single.get("errors") and not couple.get("errors"), "Console error olmamalı.", failures)
    finally:
        window.close()
        app.quit()

    status = "PASSED" if not failures else "FAILED"
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
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result)
    print(json.dumps({"status": status, "failures": failures, "report": str(REPORT_PATH), "result": str(RESULT_PATH)}, ensure_ascii=False, indent=2))
    return 0 if status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
