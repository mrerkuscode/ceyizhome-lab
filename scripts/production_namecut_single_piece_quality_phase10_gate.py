from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "2026-05-21" / "production_namecut_single_piece_quality_phase10"
RESULT_PATH = OUTPUT_DIR / "production_namecut_single_piece_quality_phase10_gate_result.json"

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
    wait(600)
    if not window.view.grab().save(str(path)):
        raise RuntimeError(f"Screenshot kaydedilemedi: {path}")
    return str(path)


def seed_namecut_quality(window: WebMainWindow, width: int, height: int) -> dict[str, object]:
    window.resize(width, height)
    wait(700)
    return run_js(window, """
    (() => {
      showSection("nameCutStudio");
      nameCutLayoutConfig = {
        ...nameCutLayoutConfig,
        width_mm: 800,
        height_mm: 600,
        margin_mm: 15,
        item_gap_mm: 1.5,
        row_gap_mm: 1.5,
        joined_name_gap_mm: 1.5,
        dense_nesting: true,
        mirror_cut: false,
        mirror_vertical: false,
        weld_inside_name: true,
        export_as_path: true,
        punctuation_fix: true,
        turkish_mark_bridge: true,
        dot_bridge_enabled: true,
        offset_mm: 0.3,
        min_stroke_mm: 0.28,
        preview_zoom: 100
      };
      nameCutItems = [
        {
          item_id: "phase10-ready-single",
          row_number: 1,
          name_text: "Ayşe Mehmet",
          preview_text: "Ayşe Mehmet",
          quantity: "2",
          width_mm: "",
          height_mm: "20",
          style: "Ceyizhome Lab Script (Mochary)",
          composition: "Tek Satır Yan Yana",
          composition_mode: "Tek Satır Yan Yana",
          offset_mm: 0.3,
          status: "READY",
          source: "bulk_production",
          source_label: "Toplu Üretim",
          errors: [],
          warnings: []
        },
        {
          item_id: "phase10-needs-weld",
          row_number: 2,
          name_text: "Mustafa Kemal",
          preview_text: "Mustafa Kemal",
          quantity: "1",
          height_mm: "20",
          offset_mm: 0.3,
          force_needs_weld: true,
          status: "READY",
          source: "manual_label",
          source_label: "Manuel Etiket",
          errors: [],
          warnings: []
        },
        {
          item_id: "phase10-detached-marks",
          row_number: 3,
          name_text: "İrem Özge",
          preview_text: "İrem Özge",
          quantity: "1",
          height_mm: "20",
          offset_mm: 0.3,
          force_detached_marks: true,
          status: "READY",
          source: "bulk_production",
          source_label: "Toplu Üretim",
          errors: [],
          warnings: []
        },
        {
          item_id: "phase10-needs-offset",
          row_number: 4,
          name_text: "Can",
          preview_text: "Can",
          quantity: "1",
          height_mm: "20",
          offset_mm: 0,
          force_needs_offset: true,
          status: "READY",
          source: "manual_label",
          source_label: "Manuel Etiket",
          errors: [],
          warnings: []
        },
        {
          item_id: "phase10-collision-risk",
          row_number: 5,
          name_text: "Abdurrahman Yağmur",
          preview_text: "Abdurrahman Yağmur",
          quantity: "1",
          height_mm: "20",
          offset_mm: 0.3,
          force_collision_risk: true,
          status: "READY",
          source: "bulk_production",
          source_label: "Toplu Üretim",
          errors: [],
          warnings: []
        },
        {
          item_id: "phase10-blocked",
          row_number: 6,
          name_text: "Model Eksik",
          preview_text: "Model Eksik",
          quantity: "1",
          height_mm: "20",
          offset_mm: 0.3,
          status: "ERROR",
          source: "bulk_production",
          source_label: "Toplu Üretim",
          errors: ["Font/model kontrolü eksik."],
          warnings: []
        }
      ];
      selectedNameCutItemId = "phase10-ready-single";
      nameCutPreviewPage = 1;
      lastNameCutExport = null;
      refreshNameCutStudioViews(currentNameCutLayout());
      const layout = currentNameCutLayout();
      const qualities = Object.fromEntries(nameCutItems.map(item => [item.item_id, nameCutSinglePieceQuality(item, layout).status]));
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      return {
        activePage: document.querySelector(".page.active")?.id || "",
        itemCount: nameCutItems.length,
        renderedCards: document.querySelectorAll("#nameCutStudio .name-cut-card").length,
        renderedOutlines: document.querySelectorAll("#nameCutStudio .rdworks-name-outline, #nameCutStudio .rdworks-name-outline-svg").length,
        qualities,
        direction: nameCutDirectionLabel(nameCutLayoutConfig),
        hasNewLanguage: /Harfler birleşik/.test(text) && /İsimler ayrı/.test(text) && /Tek parça kontrolü/.test(text) && /Min boşluk/.test(text),
        hasOldLanguage: /İsimler ayrı obje/.test(text),
        hasMetrics: /Yerleşen isim: \\d+ \\/ \\d+ · Yerleşen adet: \\d+ \\/ \\d+/.test(text),
        hasSafetyText: /RDWorks\\/lazer otomatik başlamaz/.test(text) || /RDWorks ve lazer otomatik/.test(text),
        hasAutoStartText: /yazıcı otomatik başladı|direct print başlatıldı|rdworks açıldı|lazer başladı/i.test(text)
      };
    })()
    """, timeout_ms=60000)


def select_item(window: WebMainWindow, item_id: str) -> dict[str, object]:
    return run_js(window, f"""
    (() => {{
      selectedNameCutItemId = {json.dumps(item_id)};
      refreshNameCutStudioViews(currentNameCutLayout());
      const item = nameCutItems.find(row => row.item_id === {json.dumps(item_id)});
      const quality = nameCutSinglePieceQuality(item, currentNameCutLayout());
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      return {{
        selected: selectedNameCutItemId,
        quality,
        detailHasQuality: new RegExp(quality.label).test(text),
        textHasDetached: /Nokta\\/İşaret Kopuk/.test(text),
        textHasWeld: /Weld Gerekli/.test(text),
        textHasCollision: /Temas Riski/.test(text)
      }};
    }})()
    """, timeout_ms=60000)


def mirror_check(window: WebMainWindow) -> dict[str, object]:
    return run_js(window, """
    (() => {
      nameCutLayoutConfig.mirror_cut = false;
      nameCutLayoutConfig.mirror_vertical = false;
      renderLaserLayoutPreview(currentNameCutLayout());
      const flat = nameCutDirectionLabel(nameCutLayoutConfig);
      toggleNameCutMirror("horizontal");
      const horizontal = nameCutDirectionLabel(nameCutLayoutConfig);
      toggleNameCutMirror("vertical");
      const both = nameCutDirectionLabel(nameCutLayoutConfig);
      const text = document.getElementById("nameCutStudio")?.innerText || "";
      return { flat, horizontal, both, textHasDirection: /Kesim yönü/.test(text) && /Ters\\/Ayna/.test(text) };
    })()
    """, timeout_ms=60000)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    suppress_message_boxes()
    window = WebMainWindow(PROJECT_ROOT, sys.executable)
    window.show()
    wait(1700)

    outcome: dict[str, object] = {"status": "RUNNING", "checks": {}, "screenshots": {}}
    try:
        outcome["checks"]["seed_1920"] = seed_namecut_quality(window, 1920, 1080)
        outcome["screenshots"]["single_piece_1920"] = save_screenshot(window, "namecut-single-piece-1920.png")

        outcome["checks"]["detached_marks"] = select_item(window, "phase10-detached-marks")
        outcome["screenshots"]["detached_marks"] = save_screenshot(window, "namecut-detached-marks-warning.png")

        outcome["checks"]["needs_weld"] = select_item(window, "phase10-needs-weld")
        outcome["screenshots"]["needs_weld"] = save_screenshot(window, "namecut-weld-required-warning.png")

        outcome["checks"]["collision_risk"] = select_item(window, "phase10-collision-risk")
        outcome["screenshots"]["collision_risk"] = save_screenshot(window, "namecut-collision-risk-warning.png")

        outcome["checks"]["dense_valid"] = select_item(window, "phase10-ready-single")
        outcome["screenshots"]["dense_valid"] = save_screenshot(window, "namecut-dense-nesting-valid.png")

        outcome["checks"]["mirror"] = mirror_check(window)
        outcome["screenshots"]["mirror_direction"] = save_screenshot(window, "namecut-mirror-direction.png")

        outcome["checks"]["seed_1366"] = seed_namecut_quality(window, 1366, 768)
        outcome["screenshots"]["single_piece_1366"] = save_screenshot(window, "namecut-single-piece-1366.png")

        failures: list[str] = []
        seed = outcome["checks"]["seed_1920"]
        qualities = seed["qualities"]
        expected = {
            "phase10-ready-single": "ready_single_piece",
            "phase10-needs-weld": "needs_weld",
            "phase10-detached-marks": "detached_marks",
            "phase10-needs-offset": "needs_offset",
            "phase10-collision-risk": "collision_risk",
            "phase10-blocked": "blocked",
        }
        for key, value in expected.items():
            if qualities.get(key) != value:
                failures.append(f"{key} kalite durumu beklenen değil: {qualities.get(key)}")
        if seed["activePage"] != "nameCutStudio" or seed["renderedOutlines"] < 1:
            failures.append("İsim Kesim ekranı veya yerleşim önizlemesi render edilmedi")
        if not seed["hasNewLanguage"] or seed["hasOldLanguage"]:
            failures.append("Üretim dili güncellenmedi veya eski 'İsimler ayrı obje' dili kaldı")
        if not seed["hasMetrics"]:
            failures.append("Yerleşen isim/adet metrikleri mantıklı formatta görünmedi")
        if seed["hasAutoStartText"] or not seed["hasSafetyText"]:
            failures.append("Yazıcı/lazer/RDWorks güvenlik dili bozuldu")
        if not outcome["checks"]["detached_marks"]["textHasDetached"]:
            failures.append("Kopuk nokta/işaret uyarısı görünmedi")
        if not outcome["checks"]["needs_weld"]["textHasWeld"]:
            failures.append("Weld gerekli uyarısı görünmedi")
        if not outcome["checks"]["collision_risk"]["textHasCollision"]:
            failures.append("Temas riski uyarısı görünmedi")
        mirror = outcome["checks"]["mirror"]
        if mirror["flat"] != "Düz" or mirror["horizontal"] != "Ayna Yatay" or mirror["both"] != "Ters/Ayna" or not mirror["textHasDirection"]:
            failures.append(f"Ayna/düz yön state'i beklenen değil: {mirror}")
        if outcome["checks"]["seed_1366"]["renderedOutlines"] < 1:
            failures.append("1366 görünümde yerleşim önizlemesi render edilmedi")

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


if __name__ == "__main__":
    raise SystemExit(main())
