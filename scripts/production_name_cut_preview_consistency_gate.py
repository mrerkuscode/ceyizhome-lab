from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_name_cut_preview_consistency"
RESULT_PATH = OUTPUT_DIR / "production_name_cut_preview_consistency_gate_result.json"
REPORT_PATH = OUTPUT_DIR / "PRODUCTION_NAME_CUT_PREVIEW_CONSISTENCY_RAPORU.md"

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


def seed(window: WebMainWindow) -> None:
    run_js(
        window,
        """
        (() => {
          window.__nameCutConsistencyErrors = [];
          window.addEventListener("error", event => window.__nameCutConsistencyErrors.push(String(event.message || event.error || "")));
          showSection("nameCutStudio");
          nameCutItems = [];
          selectedNameCutItemId = "";
          nameCutLayoutConfig = {
            ...nameCutLayoutConfig,
            width_mm: 800,
            height_mm: 600,
            target_name_width_mm: 80,
            target_name_height_mm: 40,
            margin_mm: 15,
            item_gap_mm: 1,
            target_gap_mm: 1,
            row_gap_mm: 1,
            joined_name_gap_mm: 1,
            dense_nesting: true,
            offset_mm: 0.3,
            font_family: "Mochary Use Personal",
            preview_zoom: 100
          };
          refreshNameCutStudioViews(currentNameCutLayout());
          return true;
        })()
        """,
        timeout_ms=60000,
    )
    wait(900)


def run_case(window: WebMainWindow, *, text: str, mode: str | None, width: int = 250, height: int = 40, offset: float = 0.3, screenshot: str) -> dict[str, object]:
    mode_json = json.dumps(mode, ensure_ascii=False)
    result = run_js(
        window,
        f"""
        (() => {{
          nameCutItems = [];
          openManualNameCutModal();
          updateNameCutDraftField("width_mm", "{width}");
          updateNameCutDraftField("height_mm", "{height}");
          updateNameCutDraftField("offset_mm", "{offset}");
          updateNameCutDraftField("name_text", {json.dumps(text, ensure_ascii=False)});
          const explicitMode = {mode_json};
          if (explicitMode) updateNameCutDraftField("composition_mode", explicitMode);
          const modalLayout = computeNameCutLayout(nameCutDraft, {{ context: "modal", userSelectedComposition: nameCutDraft.composition_user_selected === true, forceRecompute: true }});
          const modalPreview = byId("nameCutEditPreview");
          if (modalPreview) modalPreview.innerHTML = renderNameCutComputedPreview(modalLayout, true);
          saveNameCutDraft();
          const saved = nameCutItems[0];
          const savedLayout = saved.layout_result || computeNameCutLayout(saved, {{ context: "saved", userSelectedComposition: saved.composition_user_selected === true }});
          const layout = currentNameCutLayout();
          renderLaserLayoutPreview(layout);
          const mainItems = layout.items || [];
          const visibleTexts = Array.from(document.querySelectorAll("#nameCutStudio .rdworks-name-outline-svg")).map(el => el.textContent.trim());
          return {{
            modalLayout,
            savedLayout,
            saved: {{
              compositionMode: saved.compositionMode,
              composition_mode: saved.composition_mode,
              lineBreakMode: saved.lineBreakMode,
              layoutSignature: saved.layoutSignature || saved.layout_signature,
              previewLines: saved.previewLines || saved.preview_lines,
              previewObjects: saved.previewObjects || saved.preview_objects,
              width_mm: saved.width_mm,
              height_mm: saved.height_mm,
              actual_path_width_mm: saved.actual_path_width_mm,
              actual_path_height_mm: saved.actual_path_height_mm,
              fitStatus: saved.fitStatus || saved.fit_status,
              warnings: saved.warnings || []
            }},
            main: {{
              count: mainItems.length,
              texts: visibleTexts,
              itemSignatures: mainItems.map(item => item.layout_signature || item.layoutSignature || item.layout_result?.layoutSignature || ""),
              items: mainItems.map(item => ({{
                name_text: item.name_text,
                width_mm: item.width_mm,
                height_mm: item.height_mm,
                actual_path_width_mm: item.actual_path_width_mm,
                actual_path_height_mm: item.actual_path_height_mm,
                compositionMode: item.compositionMode,
                lineBreakMode: item.lineBreakMode,
                layoutSignature: item.layout_signature || item.layoutSignature || item.layout_result?.layoutSignature || ""
              }}))
            }},
            errors: window.__nameCutConsistencyErrors || []
          }};
        }})()
        """,
        timeout_ms=60000,
    )
    result["screenshot"] = save_screenshot(window, screenshot)
    return result


def write_report(result: dict[str, object]) -> None:
    failures = result.get("failures", [])
    shots = result.get("screenshots", [])
    cases = result.get("cases", {})
    report = f"""# PRODUCTION NAME CUT PREVIEW CONSISTENCY RAPORU

## Hata Neydi?
İsim Kesim düzenleme modalı, ana 800 x 600 mm lazer tablasından farklı line-break, scale ve preview metni üretebiliyordu. Özellikle uzun çoklu isim metinleri modalda iki satır gibi görünürken kaydet sonrası ana tablaya tek uzun satır olarak düşüyordu.

## Yeni Source of Truth
Frontend tarafında `computeNameCutLayout(item, options)` ortak layout motoru eklendi. Modal preview, kaydet akışı, ana canvas render’ı, inspector metrikleri ve export payload aynı layout sonucunu kullanır.

## Bağlanan Fonksiyonlar
- `nameCutPreviewText`
- `nameCutPreview`
- `normalizedNameCutItemForLayout`
- `expandJoinedNameItems`
- `renderNameCutEditor`
- `updateNameCutDraftField`
- `refreshNameCutEditorFeedback`
- `saveNameCutDraft`
- `renderLaserLayoutPreview`
- `confirmNameCutSafeExport`

## Çoklu İsim ve Kompozisyon
Çoklu isim adayları 5+ kelime, liste ayırıcıları veya çok uzun tek satır ile algılanır. Kullanıcı açıkça `single_line_text` seçmedikçe varsayılan güvenli davranış `auto_split_and_nest` olur. `preserve_lines` seçildiğinde modal ve ana canvas aynı satırları korur.

## Offset ve Actual Path Ölçüsü
`offsetMm` actual path bbox hesabına konservatif olarak dahil edilir. Backend export hattı mevcut FontTools yolunu korur; frontend layout imzası ve actual ölçüleri varsa uyumsuzlukta `layout_mismatch` uyarısı üretir.

## Test Sonuçları
- Durum: **{result.get("status")}**
- Hata sayısı: {len(failures)}
{chr(10).join(f"- {failure}" for failure in failures) if failures else "- Kritik hata yok."}

## Senaryo Özeti
{chr(10).join(f"- `{name}`: modal={case.get('modalLayout', {}).get('layoutSignature')} saved={case.get('saved', {}).get('layoutSignature')} main_count={case.get('main', {}).get('count')}" for name, case in cases.items())}

## Screenshot Yolları
{chr(10).join(f"- `{path}`" for path in shots)}

## Kalan Riskler
- Bu faz tam polygon nesting veya gerçek boolean weld motoru değildir.
- Path birleşikliği frontend’de heuristic preview olarak görünür; export/preflight aşamasında yeniden doğrulanmalıdır.
- Lazer, RDWorks ve yazıcı otomatik başlatılmaz.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, Path(sys.executable))
    window.resize(1366, 768)
    window.show()
    wait(1800)
    failures: list[str] = []
    screenshots: list[str] = []
    cases: dict[str, dict[str, object]] = {}

    try:
        seed(window)
        cases["single"] = run_case(window, text="Ayşe", mode=None, screenshot="name-cut-single-250x40.png")
        cases["couple"] = run_case(window, text="Ayşe & Mehmet", mode=None, screenshot="name-cut-couple-250x40.png")
        long_text = "Sedef Sefer Vahip Ayşe Mehmet Leyla Mücahit Serap Sedef"
        cases["multiname"] = run_case(window, text=long_text, mode=None, screenshot="name-cut-multiname-detected.png")
        cases["single_line"] = run_case(window, text=long_text, mode="Tek Satır Yan Yana", screenshot="name-cut-single-line-mode.png")
        cases["preserve_lines"] = run_case(window, text="Sedef Sefer Vahip Ayşe\nMehmet Leyla Mücahit Serap Sedef", mode="Satırları Koru", screenshot="name-cut-preserve-lines-mode.png")
        cases["offset"] = run_case(window, text="Ayşe", mode=None, offset=0.3, screenshot="name-cut-offset-030.png")
        screenshots.extend(str(case["screenshot"]) for case in cases.values())

        single = cases["single"]
        assert_true(single["modalLayout"]["layoutSignature"] == single["saved"]["layoutSignature"], "Ayşe modal ve kaydedilen layout imzası aynı olmalı.", failures)
        assert_true(single["modalLayout"]["actualPathWidthMm"] == single["saved"]["actual_path_width_mm"], "Ayşe actual width modal/kayıt arasında değişmemeli.", failures)

        couple = cases["couple"]
        assert_true(couple["modalLayout"]["layoutSignature"] == couple["saved"]["layoutSignature"], "Ayşe & Mehmet modal ve kayıt layout imzası aynı olmalı.", failures)
        assert_true(couple["saved"]["fitStatus"] in {"fits", "font_scaled"}, "Ayşe & Mehmet 250x40 içinde kontrollü sığmalı.", failures)

        multiname = cases["multiname"]
        assert_true(multiname["modalLayout"]["multiNameCandidate"] is True, "Uzun liste çoklu isim adayı algılanmalı.", failures)
        assert_true(multiname["modalLayout"]["compositionMode"] == "auto_split_and_nest", "Uzun liste varsayılan olarak tek uzun satır yapılmamalı.", failures)
        assert_true(multiname["main"]["count"] >= 5, "Uzun liste ana tablaya ayrı objeler olarak düşmeli.", failures)
        assert_true(any("çoklu isim" in warning.lower() for warning in multiname["saved"]["warnings"]), "Çoklu isim uyarısı kaydedilmeli.", failures)

        single_line = cases["single_line"]
        assert_true(single_line["modalLayout"]["compositionMode"] == "single_line_text", "Açık single_line_text seçimi korunmalı.", failures)
        assert_true(single_line["main"]["count"] == 1, "Single line modu tek obje olarak kalmalı.", failures)
        assert_true(single_line["modalLayout"]["layoutSignature"] == single_line["saved"]["layoutSignature"], "Single line modal/kayıt imzası aynı olmalı.", failures)

        preserve = cases["preserve_lines"]
        assert_true(preserve["modalLayout"]["compositionMode"] == "preserve_lines", "Satırları koru modu uygulanmalı.", failures)
        assert_true(len(preserve["modalLayout"]["previewLines"]) == 2, "Preserve lines iki satırı korumalı.", failures)
        assert_true(preserve["saved"]["previewLines"] == preserve["modalLayout"]["previewLines"], "Preserve lines kayıt satırları modal ile aynı olmalı.", failures)

        offset_case = cases["offset"]
        no_offset = run_js(window, """
        (() => {
          const base = computeNameCutLayout({ name_text: "Ayşe", width_mm: 250, height_mm: 40, offset_mm: 0, composition_user_selected: true, composition_mode: "Tek Satır Yan Yana" }, { context: "test", userSelectedComposition: true, forceRecompute: true });
          const off = computeNameCutLayout({ name_text: "Ayşe", width_mm: 250, height_mm: 40, offset_mm: 0.3, composition_user_selected: true, composition_mode: "Tek Satır Yan Yana" }, { context: "test", userSelectedComposition: true, forceRecompute: true });
          return { base, off };
        })()
        """)
        assert_true(no_offset["off"]["actualPathWidthMm"] > no_offset["base"]["actualPathWidthMm"], "Offset 0.30 actual path genişliğini büyütmeli.", failures)
        assert_true(no_offset["off"]["actualPathHeightMm"] > no_offset["base"]["actualPathHeightMm"], "Offset 0.30 actual path yüksekliğini büyütmeli.", failures)
        assert_true(offset_case["modalLayout"]["layoutSignature"] == offset_case["saved"]["layoutSignature"], "Offset case modal/kayıt imzası aynı olmalı.", failures)

        all_errors = [error for case in cases.values() for error in case.get("errors", [])]
        assert_true(not all_errors, f"Console error olmamalı: {all_errors}", failures)
    finally:
        window.close()
        app.quit()

    status = "PASSED" if not failures else "FAILED"
    result = {
        "status": status,
        "failures": failures,
        "cases": cases,
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
