from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "label_models_click_gate"
RESULT_PATH = OUTPUT_DIR / "LABEL_MODELS_REAL_CLICK_GATE_RESULT.json"


def wait(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run_js(window: WebMainWindow, script: str, timeout_ms: int = 30000):
    loop = QEventLoop()
    result = {"value": None, "done": False}

    def callback(value):
        result["value"] = value
        result["done"] = True
        loop.quit()

    wrapped = f"""
    (() => {{
      try {{
        return JSON.stringify(({script}));
      }} catch (error) {{
        return JSON.stringify({{ "__error": String(error && error.message || error), stack: String(error && error.stack || "") }});
      }}
    }})()
    """
    window.view.page().runJavaScript(wrapped, callback)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    if not result["done"]:
        raise RuntimeError(f"JavaScript timed out: {script[:120]}")
    value = result["value"]
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict) and parsed.get("__error"):
            raise RuntimeError(f"{parsed['__error']}\n{parsed.get('stack', '')}")
        return parsed
    return value


def click(window: WebMainWindow, selector: str, timeout_ms: int = 5000):
    result = run_js(window, f"""
    (() => {{
      const item = document.querySelector({json.dumps(selector)});
      if (!item) return {{ ok: false, error: 'missing selector', selector: {json.dumps(selector)} }};
      item.scrollIntoView({{ block: 'center', inline: 'center' }});
      item.click();
      return {{ ok: true, text: item.innerText || item.textContent || '', selector: {json.dumps(selector)} }};
    }})()
    """, timeout_ms=timeout_ms)
    wait(550)
    if not result or not result.get("ok"):
      raise AssertionError(f"Click failed: {result}")
    return result


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def state(window: WebMainWindow):
    return run_js(window, """
    (() => ({
      activePage: document.querySelector('.page.active')?.id || '',
      selectedPath: selectedLabelModel?.path || '',
      selectedName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
      manualTemplate: document.getElementById('manualTemplate')?.value || '',
      modelCount: currentLabelModels.length,
      visibleCards: [...document.querySelectorAll('#labelModelGallery .model-card')].length,
      selectedCardCount: [...document.querySelectorAll('#labelModelGallery .model-card.selected')].length,
      newModelModalOpen: !document.getElementById('newLabelModelModal')?.hidden,
      newModelWizardStepCount: document.querySelectorAll('#newLabelModelModal .wizard-progress span').length,
      newModelWizardFieldPreview: Boolean(document.querySelector('#newLabelModelModal .wizard-field-preview')),
      cloneModelModalOpen: !document.getElementById('cloneLabelModelModal')?.hidden,
      previewModalOpen: !document.getElementById('modelPreviewModal')?.hidden,
      bindingModalOpen: !document.getElementById('previewBindingModal')?.hidden,
      healthResultVisible: !document.getElementById('modelHealthCheckResult')?.hidden,
      repairResultVisible: !document.getElementById('modelRepairResult')?.hidden,
      technicalMode: document.body.classList.contains('label-technical-mode'),
      technicalVisible: getComputedStyle(document.getElementById('selectedModelTechnicalWrap')).display !== 'none',
      status: document.getElementById('labelModelStatus')?.textContent || '',
      editTemplateCalls: window.__editTemplateCalls || 0,
      sourceModelCalls: window.__sourceModelCalls || 0,
      consoleErrors: window.__clickGateErrors || []
    }))()
    """)


def assert_true(condition: bool, message: str, details=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {details}")


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}

    run_js(window, """
    (() => {
      window.__clickGateErrors = [];
      window.onerror = (message, source, line, column, error) => {
        window.__clickGateErrors.push(String(message || error || 'unknown'));
      };
      window.__editTemplateCalls = 0;
      window.__sourceModelCalls = 0;
      if (bridge && typeof bridge.editTemplate === 'function') {
        const originalEditTemplate = bridge.editTemplate.bind(bridge);
        bridge.editTemplate = (...args) => { window.__editTemplateCalls += 1; return originalEditTemplate(...args); };
      }
      if (bridge && typeof bridge.create_label_model_from_source === 'function') {
        bridge.create_label_model_from_source = () => { window.__sourceModelCalls += 1; };
      }
      showSection('labelModels');
      renderLabelModels();
      return { ok: true, modelCount: currentLabelModels.length };
    })()
    """, timeout_ms=60000)
    wait(1600)
    initial = state(window)
    assert_true(initial["activePage"] == "labelModels", "Etiket Modelleri açılmadı", initial)
    assert_true(initial["modelCount"] > 0, "Model listesi boş", initial)
    screenshots["general"] = save_screenshot(window, "label_models_general.png")
    checks.append({"name": "page_open", "status": "PASSED", "state": initial})

    click(window, "button[onclick='refreshLabelModels()']")
    refreshed = state(window)
    assert_true(refreshed["modelCount"] == initial["modelCount"], "Yenile model listesini bozdu", refreshed)
    assert_true(refreshed["selectedPath"], "Yenile selectedModel değerini kaybetti", refreshed)
    checks.append({"name": "refresh_keeps_model_list_and_selection", "status": "PASSED", "state": refreshed})

    click(window, "#labelModelGallery .model-card")
    selected = state(window)
    assert_true(selected["selectedPath"], "Kart tıklaması selectedModel üretmedi", selected)
    assert_true(selected["selectedCardCount"] == 1, "Seçili kart vurgusu yok", selected)
    assert_true(selected["manualTemplate"] == selected["selectedPath"], "Kart seçimi Studio model state değerini senkronlamadı", selected)
    screenshots["selected_detail"] = save_screenshot(window, "label_models_selected_detail.png")
    checks.append({"name": "card_select_updates_detail", "status": "PASSED", "state": selected})

    selected_path = selected["selectedPath"]
    click(window, "#labelModelGallery .model-card.selected .model-card-actions .btn.primary")
    studio = state(window)
    assert_true(studio["activePage"] == "label", "Etiket Hazırla Studio'ya gitmedi", studio)
    assert_true(studio["manualTemplate"] == selected_path, "Etiket Hazırla yanlış modeli taşıdı", studio)
    checks.append({"name": "card_prepare_opens_studio_with_selected_model", "status": "PASSED", "model": selected_path})

    run_js(window, "(() => { showSection('labelModels'); renderLabelModels(); return { ok: true }; })()")
    wait(600)
    second = run_js(window, """
    (() => {
      const cards = [...document.querySelectorAll('#labelModelGallery .model-card')];
      const target = cards[1] || cards[0];
      target?.click();
      return { ok: Boolean(target), count: cards.length, selectedPath: selectedLabelModel?.path || '' };
    })()
    """)
    wait(500)
    second_path = state(window)["selectedPath"]
    click(window, "#labelModelGallery .model-card.selected .model-card-actions .btn:not(.primary)")
    studio_second = state(window)
    assert_true(studio_second["activePage"] == "label", "Studio’da Düzenle Studio'ya gitmedi", studio_second)
    assert_true(studio_second["manualTemplate"] == second_path, "Studio’da Düzenle yanlış modeli taşıdı", studio_second)
    checks.append({"name": "card_edit_opens_studio_with_clicked_model", "status": "PASSED", "model": second_path, "selection": second})

    run_js(window, "(() => { showSection('labelModels'); renderLabelModels(); return { ok: true }; })()")
    wait(600)
    click(window, ".detail-panel .button-grid .btn:nth-child(3)")
    preview = state(window)
    assert_true(preview["previewModalOpen"], "Önizle modal açmadı", preview)
    screenshots["preview_modal"] = save_screenshot(window, "label_models_preview_modal.png")
    click(window, "#modelPreviewModal .btn.ghost")
    checks.append({"name": "preview_modal_opens", "status": "PASSED"})

    click(window, "button[onclick='openNewLabelModelWizard()']")
    new_modal = state(window)
    assert_true(new_modal["newModelModalOpen"], "Yeni Model Ekle sade modal açmadı", new_modal)
    assert_true(new_modal["editTemplateCalls"] == 0, "Yeni Model Ekle teknik editörü açtı", new_modal)
    assert_true(new_modal["newModelWizardStepCount"] == 5, "Yeni Model Ekle sihirbazı 5 adım göstermedi", new_modal)
    assert_true(new_modal["newModelWizardFieldPreview"], "Yeni Model Ekle varsayılan yazı alanlarını anlatmadı", new_modal)
    screenshots["new_model_modal"] = save_screenshot(window, "label_models_new_model_modal.png")
    click(window, "#newLabelModelModal .btn.ghost")
    checks.append({"name": "new_model_opens_safe_modal", "status": "PASSED"})

    click(window, "button[onclick='openCloneLabelModelWizard()']")
    clone_modal = state(window)
    assert_true(clone_modal["cloneModelModalOpen"], "Varyant Oluştur sade modal açmadı", clone_modal)
    assert_true(clone_modal["editTemplateCalls"] == 0, "Varyant Oluştur teknik editörü açtı", clone_modal)
    assert_true(clone_modal["sourceModelCalls"] == 0, "Varyant Oluştur kaynak model oluşturma akışını çağırdı", clone_modal)
    screenshots["clone_model_modal"] = save_screenshot(window, "label_models_clone_model_modal.png")
    click(window, "#cloneLabelModelModal .btn.ghost")
    checks.append({"name": "clone_model_opens_safe_modal", "status": "PASSED"})

    click(window, "button[onclick='uploadDesignVisualForSelectedModel()']")
    binding = state(window)
    assert_true(binding["bindingModalOpen"], "Tasarım Görseli Yükle bağlama modalı açmadı", binding)
    assert_true(binding["sourceModelCalls"] == 0, "Tasarım Görseli Yükle create_label_model_from_source çağırdı", binding)
    assert_true(binding["editTemplateCalls"] == 0, "Tasarım Görseli Yükle teknik editörü açtı", binding)
    screenshots["preview_binding_modal"] = save_screenshot(window, "label_models_preview_binding_modal.png")
    click(window, "#previewBindingModal .btn.ghost")
    checks.append({"name": "upload_design_visual_opens_safe_binding", "status": "PASSED"})

    click(window, ".detail-panel .button-grid .btn:nth-child(6)")
    health = state(window)
    assert_true(health["healthResultVisible"], "Modeli Kontrol Et sonucu görünmedi", health)
    assert_true(health["repairResultVisible"], "Modeli Kontrol Et onarım sonuç panelini göstermedi", health)
    screenshots["health_check"] = save_screenshot(window, "label_models_health_check.png")
    checks.append({"name": "model_health_check_visible", "status": "PASSED"})

    run_js(window, "(() => { document.getElementById('modelSearch').value = '__no_model__'; renderLabelModels(); return { ok: true }; })()")
    wait(500)
    empty = state(window)
    assert_true(empty["visibleCards"] == 0, "Arama filtresi sonuçları filtrelemedi", empty)
    screenshots["empty_filter"] = save_screenshot(window, "label_models_empty_filter.png")
    run_js(window, "(() => { clearModelFilters(); return { ok: true }; })()")
    wait(500)
    checks.append({"name": "filters_show_empty_state", "status": "PASSED"})

    run_js(window, "(() => { setModelHealthFilter('Görsel eksik'); return { visibleCards: document.querySelectorAll('#labelModelGallery .model-card').length }; })()")
    wait(500)
    missing_preview = state(window)
    assert_true(missing_preview["selectedPath"] == missing_preview["manualTemplate"], "Eksik görsel filtresi Studio model state değerini senkron tutmadı", missing_preview)
    screenshots["missing_preview_filter"] = save_screenshot(window, "label_models_missing_preview_filter.png")
    run_js(window, "(() => { clearModelFilters(); return { ok: true }; })()")
    wait(500)
    checks.append({"name": "missing_preview_filter_is_safe", "status": "PASSED", "state": missing_preview})

    tech_closed = state(window)
    assert_true(not tech_closed["technicalMode"] and not tech_closed["technicalVisible"], "Teknik detaylar normal modda görünür", tech_closed)
    run_js(window, "(() => { document.getElementById('labelTechnicalMode').click(); return { ok: true }; })()")
    wait(500)
    tech_open = state(window)
    assert_true(tech_open["technicalMode"] and tech_open["technicalVisible"], "Teknik Mod detayları açmadı", tech_open)
    screenshots["technical_mode_open"] = save_screenshot(window, "label_models_technical_mode_open.png")
    checks.append({"name": "technical_mode_isolated", "status": "PASSED"})

    final_state = state(window)
    assert_true(not final_state["consoleErrors"], "Console error oluştu", final_state)
    assert_true(final_state["editTemplateCalls"] == 0, "Normal akış teknik editörü çağırdı", final_state)
    assert_true(final_state["sourceModelCalls"] == 0, "Normal akış kaynak model oluşturma çağırdı", final_state)

    return {"status": "PASSED", "checks": checks, "screenshots": screenshots, "final_state": final_state}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 950)
    window.show()
    wait(6000)
    try:
        outcome = run_gate(window)
    except Exception as exc:  # noqa: BLE001
        outcome = {"status": "ERROR", "message": str(exc)}
    RESULT_PATH.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    window.close()
    app.processEvents()
    return 0 if outcome.get("status") == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
