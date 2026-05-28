from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from label_models_real_click_gate import PROJECT_ROOT, WebMainWindow, assert_true, run_gate, run_js, state, wait


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "label_models_premium_flow"
RESULT_PATH = OUTPUT_DIR / "LABEL_MODELS_PREMIUM_FLOW_RESULT.json"


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def run_premium_checks(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = run_gate(window)
    checks = list(base.get("checks", []))
    screenshots = dict(base.get("screenshots", {}))

    run_js(window, """
    (() => {
      showSection('labelModels');
      if (document.getElementById('labelTechnicalMode')?.checked) document.getElementById('labelTechnicalMode').click();
      clearModelFilters();
      renderLabelModels();
      return { ok: true };
    })()
    """)
    wait(800)

    premium = run_js(window, """
    (() => {
      const kpis = [...document.querySelectorAll('#labelModelHealthSummary .health-kpi')];
      const firstCard = document.querySelector('#labelModelGallery .model-card');
      const missingPlaceholders = [...document.querySelectorAll('#labelModelGallery .missing-preview-placeholder')]
        .filter(node => node.offsetParent !== null).length;
      firstCard?.click();
      return {
        kpiCount: kpis.length,
        kpiHasIcons: kpis.every(item => Boolean(item.querySelector('.kpi-icon'))),
        hasFilterClear: Boolean([...document.querySelectorAll('#labelModels .filterbar .btn')].find(btn => /Filtreleri Temizle/.test(btn.textContent || ''))),
        hasSelectedRibbon: Boolean(document.querySelector('#labelModelGallery .model-card.selected .selected-ribbon')),
        healthPills: document.querySelectorAll('#labelModelGallery .model-card.selected .model-health-pill').length,
        hasPreviewFallback: Boolean(document.querySelector('#labelModelGallery .missing-preview-placeholder')),
        visibleMissingPlaceholders: missingPlaceholders,
        rightPreviewHtml: document.getElementById('selectedModelPreview')?.innerHTML || '',
        rightHealthChecks: document.querySelectorAll('#selectedModelHealthPanel .health-check-list span').length,
        technicalHidden: getComputedStyle(document.getElementById('selectedModelTechnicalWrap')).display === 'none',
      };
    })()
    """)
    assert_true(premium["kpiCount"] == 5, "KPI kart sayısı eksik", premium)
    assert_true(premium["kpiHasIcons"], "KPI kart ikonları eksik", premium)
    assert_true(premium["hasFilterClear"], "Filtreleri Temizle butonu eksik", premium)
    assert_true(premium["hasSelectedRibbon"], "Seçili model badge'i görünmüyor", premium)
    assert_true(premium["healthPills"] >= 4, "Kart health pill göstergeleri eksik", premium)
    assert_true(premium["rightHealthChecks"] >= 5, "Sağ panel health checklist eksik", premium)
    assert_true(premium["technicalHidden"], "Teknik detaylar normal modda gizli değil", premium)
    run_js(window, "(() => { const panel = document.querySelector('#labelModels .detail-panel'); if (panel) panel.scrollTop = 0; return { ok: true }; })()")
    wait(250)
    screenshots["premium_general"] = save_screenshot(window, "label_models_premium_general.png")
    checks.append({"name": "premium_layout_tokens", "status": "PASSED", "state": premium})

    kpi_filter = run_js(window, """
    (() => {
      setModelHealthFilter('Hazır');
      const readyCards = [...document.querySelectorAll('#labelModelGallery .model-card')].map(card => card.innerText || '');
      setModelHealthFilter('Görsel eksik');
      const missingCards = [...document.querySelectorAll('#labelModelGallery .model-card')].map(card => card.innerText || '');
      clearModelFilters();
      return {
        readyCount: readyCards.length,
        missingCount: missingCards.length,
        readyLabelsOk: readyCards.every(text => text.includes('Hazır')),
        missingLabelsOk: missingCards.every(text => text.includes('Görsel eksik') || text.includes('Görsel bulunamadı') || text.includes('Önizleme henüz hazır değil')),
      };
    })()
    """)
    assert_true(kpi_filter["readyLabelsOk"], "Hazır KPI yanlış filtre uyguladı", kpi_filter)
    assert_true(kpi_filter["missingLabelsOk"], "Görsel eksik KPI yanlış filtre uyguladı", kpi_filter)
    screenshots["filtered_missing"] = save_screenshot(window, "label_models_filtered_missing.png")
    checks.append({"name": "kpi_filters_apply_real_filters", "status": "PASSED", "state": kpi_filter})

    preview_fallback = run_js(window, """
    (() => {
      const model = currentLabelModels.find(item => !item.preview_image) || currentLabelModels[0];
      if (model) selectLabelModel(model.path);
      const card = document.querySelector('#labelModelGallery .model-card.selected');
      const panel = document.getElementById('selectedModelPreview');
      return {
        selected: selectedLabelModel?.path || '',
        cardHasImageOrPlaceholder: Boolean(card?.querySelector('img, .missing-preview-placeholder')),
        panelHasImageOrPlaceholder: Boolean(panel?.querySelector('img, .missing-preview-placeholder')),
        noBrokenWhiteBox: Boolean(card?.querySelector('.model-preview')?.textContent?.trim() || card?.querySelector('.model-preview img')),
      };
    })()
    """)
    assert_true(preview_fallback["cardHasImageOrPlaceholder"], "Kart preview resolver boş kaldı", preview_fallback)
    assert_true(preview_fallback["panelHasImageOrPlaceholder"], "Sağ panel preview resolver boş kaldı", preview_fallback)
    assert_true(preview_fallback["noBrokenWhiteBox"], "Preview alanı boş beyaz kutu gibi kaldı", preview_fallback)
    screenshots["preview_resolver"] = save_screenshot(window, "label_models_preview_resolver.png")
    checks.append({"name": "preview_resolver_never_leaves_blank_box", "status": "PASSED", "state": preview_fallback})

    run_js(window, "(() => { runSelectedModelHealthCheck(); return { ok: true }; })()")
    wait(500)
    health_state = state(window)
    assert_true(health_state["healthResultVisible"], "Modeli Kontrol Et sonucu açılmadı", health_state)
    screenshots["health_result"] = save_screenshot(window, "label_models_premium_health_result.png")
    checks.append({"name": "model_check_result_visible", "status": "PASSED", "state": health_state})

    final_state = state(window)
    assert_true(not final_state["consoleErrors"], "Console error oluştu", final_state)
    return {
        "status": "PASSED",
        "checks": checks,
        "screenshots": screenshots,
        "final_state": final_state,
    }


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()
    result_box: dict[str, object] = {}

    def execute() -> None:
        try:
            result_box.update(run_premium_checks(window))
        except Exception as exc:  # noqa: BLE001
            result_box.update({"status": "FAILED", "error": str(exc)})
        RESULT_PATH.write_text(json.dumps(result_box, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()
        app.quit()

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(1800, execute))
    exit_code = app.exec()
    if result_box.get("status") != "PASSED":
        sys.stdout.buffer.write(json.dumps(result_box, ensure_ascii=False, indent=2).encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        return 1
    print(f"LABEL_MODELS_PREMIUM_FLOW: PASSED -> {RESULT_PATH}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
