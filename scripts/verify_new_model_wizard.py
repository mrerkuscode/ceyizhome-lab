from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from label_models_real_click_gate import PROJECT_ROOT, WebMainWindow, assert_true, click, run_js, wait


OUTPUT_DIR = PROJECT_ROOT / "output" / date.today().isoformat() / "new_model_wizard_flow"
RESULT_PATH = OUTPUT_DIR / "NEW_MODEL_WIZARD_FLOW_RESULT.json"
TEST_VISUAL = PROJECT_ROOT / "assets" / "label_backgrounds" / "normalized" / "01_a_gold_preview_50x30.png"


def save_screenshot(window: WebMainWindow, filename: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    window.view.grab().save(str(path))
    return str(path)


def wizard_state(window: WebMainWindow) -> dict[str, object]:
    return run_js(
        window,
        """
        (() => ({
          activePage: document.querySelector('.page.active')?.id || '',
          modalOpen: !document.getElementById('newLabelModelModal')?.hidden,
          stepCount: document.querySelectorAll('#newLabelModelModal .wizard-progress span').length,
          hasFieldPreview: Boolean(document.querySelector('#newLabelModelModal .wizard-field-preview')),
          footerVisible: (() => {
            const footer = document.querySelector('#newLabelModelModal .toolbar');
            if (!footer) return false;
            const rect = footer.getBoundingClientRect();
            return rect.bottom <= window.innerHeight && rect.top >= 0 && rect.height > 20;
          })(),
          visualText: document.getElementById('newModelVisualStatus')?.innerText || '',
          resultText: document.getElementById('newLabelModelResult')?.innerText || '',
          resultHasStudioOpen: Boolean(document.querySelector('#newLabelModelResult .new-model-result-actions .btn.primary')),
          pendingPath: pendingLabelModelSelectPath || '',
          lastCreatedPath: lastCreatedLabelModelPath || '',
          selectedPath: selectedLabelModel?.path || '',
          selectedName: selectedLabelModel?.model_name || selectedLabelModel?.title || '',
          manualTemplate: document.getElementById('manualTemplate')?.value || '',
          modelCount: currentLabelModels.length,
          editTemplateCalls: window.__wizardEditTemplateCalls || 0,
          sourceModelCalls: window.__wizardSourceModelCalls || 0,
          consoleErrors: window.__wizardErrors || []
        }))()
        """,
    )


def normalize_model_path(value: str) -> str:
    normalized = str(value or "").replace("\\", "/")
    marker = "/templates/designs/"
    index = normalized.lower().rfind(marker)
    if index >= 0:
        return normalized[index + 1 :]
    return normalized.lstrip("./")


def cleanup_created_model(created_path: str, preview_path: str) -> None:
    for raw in [created_path, preview_path]:
        if not raw:
            continue
        path = (PROJECT_ROOT / raw).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            continue
        if path.exists() and path.is_file():
            path.unlink()


def run_gate(window: WebMainWindow) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, object]] = []
    screenshots: dict[str, str] = {}
    created_path = ""
    created_preview = ""

    visual_url = TEST_VISUAL.as_uri()
    model_name = f"Wizard QA Model {date.today().isoformat()}"

    run_js(
        window,
        """
        (() => {
          window.__wizardErrors = [];
          window.onerror = (message, source, line, column, error) => {
            window.__wizardErrors.push(String(message || error || 'unknown'));
          };
          window.__wizardEditTemplateCalls = 0;
          window.__wizardSourceModelCalls = 0;
          if (bridge && typeof bridge.editTemplate === 'function') {
            const originalEditTemplate = bridge.editTemplate.bind(bridge);
            bridge.editTemplate = (...args) => {
              window.__wizardEditTemplateCalls += 1;
              return originalEditTemplate(...args);
            };
          }
          if (bridge && typeof bridge.create_label_model_from_source === 'function') {
            bridge.create_label_model_from_source = () => { window.__wizardSourceModelCalls += 1; };
          }
          showSection('labelModels');
          clearModelFilters();
          renderLabelModels();
          return { ok: true };
        })()
        """,
        timeout_ms=60000,
    )
    wait(1200)

    before = wizard_state(window)
    screenshots["models_before"] = save_screenshot(window, "new_model_models_before.png")
    checks.append({"name": "label_models_page_ready", "status": "PASSED", "state": before})

    click(window, "button[onclick='openNewLabelModelWizard()']")
    opened = wizard_state(window)
    assert_true(opened["modalOpen"], "Yeni Model Ekle modalı açılmadı", opened)
    assert_true(opened["stepCount"] == 5, "Wizard 5 adım göstermedi", opened)
    assert_true(opened["hasFieldPreview"], "Varsayılan İsim/Tarih/Not alan önizlemesi yok", opened)
    assert_true(opened["footerVisible"], "Wizard footer görünür değil veya kesiliyor", opened)
    assert_true(opened["editTemplateCalls"] == 0, "Wizard teknik editör açtı", opened)
    screenshots["step_1"] = save_screenshot(window, "new_model_step_1.png")
    checks.append({"name": "wizard_opens_with_visible_footer", "status": "PASSED", "state": opened})

    visual = run_js(
        window,
        f"""
        (() => {{
          document.getElementById('newModelName').value = {json.dumps(model_name)};
          document.getElementById('newModelVariant').value = 'QA';
          document.getElementById('newModelUseDefaultSize').checked = false;
          syncNewModelSizeInputs();
          document.getElementById('newModelWidthMm').value = '50';
          document.getElementById('newModelHeightMm').value = '30';
          newLabelModelVisual = {{
            status: 'OK',
            path: {json.dumps(str(TEST_VISUAL))},
            file_name: {json.dumps(TEST_VISUAL.name)},
            preview_url: {json.dumps(visual_url)}
          }};
          document.getElementById('newModelVisualStatus').innerHTML =
            '<div class="success-note"><b>Tasarım görseli seçildi.</b><br>' +
            {json.dumps(TEST_VISUAL.name)} +
            '</div><div class="wizard-preview"><img src="' + {json.dumps(visual_url)} + '" alt="Seçilen tasarım görseli" /></div>' +
            '<div class="preview-diagnostic">Oran kontrolü: 50 x 30 mm etiket için görsel hazır.</div>';
          return {{
            name: document.getElementById('newModelName').value,
            variant: document.getElementById('newModelVariant').value,
            widthDisabled: document.getElementById('newModelWidthMm').disabled,
            visualText: document.getElementById('newModelVisualStatus').innerText
          }};
        }})()
        """,
    )
    assert_true(visual["name"] == model_name, "Model adı input'a yazılmadı", visual)
    assert_true(visual["variant"] == "QA", "Varyant input'a yazılmadı", visual)
    assert_true(not visual["widthDisabled"], "Özel ölçü inputları aktif olmadı", visual)
    assert_true("Tasarım görseli seçildi" in visual["visualText"], "Görsel seçimi UI'da görünmedi", visual)
    screenshots["visual_step"] = save_screenshot(window, "new_model_visual_step.png")
    checks.append({"name": "visual_and_size_step_ready", "status": "PASSED", "state": visual})

    click(window, "#newLabelModelModal .toolbar .btn.primary", timeout_ms=10000)
    wait(2200)
    saved = wizard_state(window)
    assert_true(saved["resultHasStudioOpen"], "Kaydet sonrası Studio'da Aç aksiyonu görünmedi", saved)
    assert_true(saved["pendingPath"] or saved["lastCreatedPath"], "Kaydet sonrası model path oluşmadı", saved)
    assert_true("kaydedildi" in str(saved["resultText"]).lower() or "oluşturuldu" in str(saved["resultText"]).lower(), "Kaydet başarı mesajı yok", saved)
    assert_true(saved["editTemplateCalls"] == 0 and saved["sourceModelCalls"] == 0, "Wizard güvenli olmayan teknik akış çağırdı", saved)
    created_path = str(saved["pendingPath"] or saved["lastCreatedPath"])
    screenshots["saved_summary"] = save_screenshot(window, "new_model_saved_summary.png")
    checks.append({"name": "wizard_saves_model", "status": "PASSED", "state": saved})

    created_data = json.loads((PROJECT_ROOT / created_path).read_text(encoding="utf-8"))
    created_preview = str(created_data.get("preview_image") or "")
    fields = created_data.get("fields") if isinstance(created_data.get("fields"), list) else []
    columns = {str(field.get("excel_column") or "") for field in fields if isinstance(field, dict)}
    assert_true({"label_text", "date_text", "note_text"}.issubset(columns), "Varsayılan yazı alanları oluşmadı", created_data)
    assert_true(float(created_data.get("label_width_mm") or 0) == 50.0, "Model genişliği yanlış kaydedildi", created_data)
    assert_true(float(created_data.get("label_height_mm") or 0) == 30.0, "Model yüksekliği yanlış kaydedildi", created_data)
    checks.append({"name": "created_template_has_safe_basic_fields", "status": "PASSED", "path": created_path})

    click(window, "#newLabelModelResult .new-model-result-actions .btn.primary", timeout_ms=10000)
    wait(1200)
    studio = wizard_state(window)
    assert_true(studio["activePage"] == "label", "Studio'da Aç etiketi Studio sayfasına götürmedi", studio)
    assert_true(normalize_model_path(str(studio["manualTemplate"])) == normalize_model_path(created_path), "Studio yanlış modeli açtı", studio)
    screenshots["studio_new_model"] = save_screenshot(window, "new_model_opened_in_studio.png")
    checks.append({"name": "created_model_opens_in_studio", "status": "PASSED", "state": studio})

    final_state = wizard_state(window)
    assert_true(not final_state["consoleErrors"], "Wizard akışında console error oluştu", final_state)

    return {
        "status": "PASSED",
        "created_path": created_path,
        "created_preview": created_preview,
        "cleaned_up_created_model": False,
        "checks": checks,
        "screenshots": screenshots,
    }


def main() -> int:
    if not TEST_VISUAL.exists():
        print(f"Missing test visual: {TEST_VISUAL}")
        return 1
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()
    result_box: dict[str, object] = {}

    def execute() -> None:
        try:
            result_box.update(run_gate(window))
            cleanup_created_model(str(result_box.get("created_path") or ""), str(result_box.get("created_preview") or ""))
            result_box["cleaned_up_created_model"] = True
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
    print(f"NEW_MODEL_WIZARD_FLOW: PASSED -> {RESULT_PATH}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
